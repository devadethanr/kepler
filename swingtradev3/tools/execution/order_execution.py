from __future__ import annotations

import uuid

from auth.kite.client import calculate_live_order_margins, fetch_margins, has_kite_session, place_live_order
from config import cfg, runtime_flags
from integrations.kite.mcp_client import KiteMCPClient
from models import AccountState
from paper.fill_engine import FillEngine
from tools.execution.gtt_manager import GTTManager
from tools.execution.risk_check import RiskCheckTool


def _is_submission_timeout(exc: Exception) -> bool:
    marker = f"{type(exc).__module__}.{type(exc).__name__}:{exc}".lower()
    return "timeout" in marker or "timed out" in marker


class OrderExecutionTool:
    def __init__(
        self,
        fill_engine: FillEngine | None = None,
        risk_tool: RiskCheckTool | None = None,
        gtt_manager: GTTManager | None = None,
        mcp_client: KiteMCPClient | None = None,
    ) -> None:
        self.fill_engine = fill_engine or FillEngine()
        self.risk_tool = risk_tool or RiskCheckTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.mcp_client = mcp_client or KiteMCPClient()

    def _build_broker_tag(self, ticker: str) -> str:
        base = ticker.upper().replace("-", "")[:8]
        suffix = uuid.uuid4().hex[:8].upper()
        return f"STV3{base}{suffix}"[:20]

    def _run_live_margin_check(
        self,
        *,
        ticker: str,
        side: str,
        quantity: int,
        price: float,
    ) -> tuple[bool, str | None, dict[str, object]]:
        order_spec = {
            "exchange": cfg.trading.exchange,
            "tradingsymbol": ticker,
            "transaction_type": side.upper(),
            "variety": "regular",
            "product": "CNC",
            "order_type": "LIMIT",
            "quantity": quantity,
            "price": price,
        }
        try:
            margin_rows = calculate_live_order_margins([order_spec])
            margin_row = margin_rows[0] if margin_rows else {}
            required_total = float(margin_row.get("total") or 0.0)
            margins = fetch_margins()
            equity = margins.get("equity", {}) if isinstance(margins, dict) else {}
            available = equity.get("available", {}) if isinstance(equity, dict) else {}
            available_cash = float(available.get("cash") or 0.0)
        except Exception:
            return False, "live_margin_check_failed", {}

        if required_total > 0 and available_cash > 0 and required_total > available_cash:
            return False, "insufficient_broker_margin", {
                "required_total": required_total,
                "available_cash": available_cash,
            }
        return True, None, {
            "required_total": required_total,
            "available_cash": available_cash,
        }

    def _resolve_quantity(
        self,
        state: AccountState,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
        quantity: int | None = None,
    ) -> tuple[dict[str, object], int]:
        risk = self.risk_tool.check_risk(state, score, price, stop_price, target_price)
        if not risk["approved"]:
            return {"status": "rejected", "reason": risk["reason"], "quantity": 0}, 0

        approved_quantity = int(risk["quantity"])
        if quantity is None:
            return risk, approved_quantity
        if quantity <= 0:
            return {"status": "rejected", "reason": "invalid_quantity", "quantity": 0}, 0
        return risk, min(int(quantity), approved_quantity)

    def place_order(
        self,
        state: AccountState,
        ticker: str,
        side: str,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
        quantity: int | None = None,
    ) -> dict[str, object]:
        risk, resolved_quantity = self._resolve_quantity(
            state, score, price, stop_price, target_price, quantity=quantity
        )
        if risk.get("status") == "rejected":
            return risk

        live_block_reason = runtime_flags.live_entry_block_reason(cfg.trading.mode)

        if cfg.trading.mode.value == "live":
            if live_block_reason is not None:
                return {
                    "status": "blocked",
                    "reason": live_block_reason,
                    "quantity": 0,
                    "mode": "live",
                }
            if not has_kite_session():
                return {
                    "status": "blocked",
                    "reason": "KITE_SESSION_REQUIRED",
                    "quantity": 0,
                    "mode": "live",
                }
            margin_ok, margin_reason, margin_payload = self._run_live_margin_check(
                ticker=ticker,
                side=side,
                quantity=resolved_quantity,
                price=price,
            )
            if not margin_ok:
                return {
                    "status": "blocked",
                    "reason": margin_reason,
                    "quantity": resolved_quantity,
                    "mode": "live",
                    "margin": margin_payload,
                }

            broker_tag = self._build_broker_tag(ticker)

            try:
                order_id = place_live_order(
                    exchange=cfg.trading.exchange,
                    ticker=ticker,
                    side=side,
                    quantity=resolved_quantity,
                    price=price,
                    tag=broker_tag,
                )
            except Exception as exc:
                if _is_submission_timeout(exc):
                    return {
                        "order_id": None,
                        "status": "submission_uncertain",
                        "reason": "live_order_submission_timeout",
                        "average_price": None,
                        "quantity": resolved_quantity,
                        "mode": "live",
                        "product": "CNC",
                        "broker_tag": broker_tag,
                        "margin": margin_payload,
                        "protection_status": "pending_broker_reconciliation",
                    }
                return {
                    "status": "failed",
                    "reason": f"live_order_submission_failed:{exc}",
                    "quantity": resolved_quantity,
                    "mode": "live",
                    "broker_tag": broker_tag,
                    "margin": margin_payload,
                }
            return {
                "order_id": order_id,
                "status": "submitted",
                "average_price": None,
                "quantity": resolved_quantity,
                "mode": "live",
                "product": "CNC",
                "broker_tag": broker_tag,
                "margin": margin_payload,
                "protection_status": "pending_fill_confirmation",
            }

        order_id = f"order-{uuid.uuid4().hex[:10]}"
        fill = self.fill_engine.fill(ticker, side, resolved_quantity, price, order_id)
        position_id = f"pos-{uuid.uuid4().hex[:10]}"
        gtt = self.gtt_manager.place_gtt(
            position_id,
            ticker,
            stop_price,
            target_price,
            quantity=resolved_quantity,
        )
        return {
            "order_id": fill.order_id,
            "status": fill.status,
            "average_price": fill.average_price,
            "quantity": fill.quantity,
            "product": "CNC",
            "position_id": position_id,
            "oco_gtt_id": gtt.oco_gtt_id,
        }

    async def place_order_async(
        self,
        state: AccountState,
        ticker: str,
        side: str,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
        quantity: int | None = None,
    ) -> dict[str, object]:
        risk, resolved_quantity = self._resolve_quantity(
            state, score, price, stop_price, target_price, quantity=quantity
        )
        if risk.get("status") == "rejected":
            return risk

        order_id = f"order-{uuid.uuid4().hex[:10]}"
        if cfg.trading.mode.value != "live":
            return self.place_order(
                state,
                ticker,
                side,
                score,
                price,
                stop_price,
                target_price,
                quantity=resolved_quantity,
            )

        live_block_reason = runtime_flags.live_entry_block_reason(cfg.trading.mode)
        if live_block_reason is not None:
            return {
                "status": "blocked",
                "reason": live_block_reason,
                "quantity": 0,
                "mode": "live",
            }
        if not has_kite_session():
            return {
                "status": "blocked",
                "reason": "KITE_SESSION_REQUIRED",
                "quantity": 0,
                "mode": "live",
            }
        margin_ok, margin_reason, margin_payload = self._run_live_margin_check(
            ticker=ticker,
            side=side,
            quantity=resolved_quantity,
            price=price,
        )
        if not margin_ok:
            return {
                "status": "blocked",
                "reason": margin_reason,
                "quantity": resolved_quantity,
                "mode": "live",
                "margin": margin_payload,
            }

        broker_tag = self._build_broker_tag(ticker)

        if has_kite_session():
            try:
                order_id = place_live_order(
                    exchange=cfg.trading.exchange,
                    ticker=ticker,
                    side=side,
                    quantity=resolved_quantity,
                    price=price,
                    tag=broker_tag,
                )
            except Exception as exc:
                if _is_submission_timeout(exc):
                    return {
                        "order_id": None,
                        "status": "submission_uncertain",
                        "reason": "live_order_submission_timeout",
                        "average_price": None,
                        "quantity": resolved_quantity,
                        "mode": "live",
                        "product": "CNC",
                        "broker_tag": broker_tag,
                        "margin": margin_payload,
                        "position_id": None,
                        "oco_gtt_id": None,
                        "protection_status": "pending_broker_reconciliation",
                    }
                return {
                    "status": "failed",
                    "reason": f"live_order_submission_failed:{exc}",
                    "quantity": resolved_quantity,
                    "mode": "live",
                    "broker_tag": broker_tag,
                    "margin": margin_payload,
                }
        return {
            "order_id": order_id,
            "status": "submitted",
            "average_price": None,
            "quantity": resolved_quantity,
            "mode": "live",
            "product": "CNC",
            "broker_tag": broker_tag,
            "margin": margin_payload,
            "position_id": None,
            "oco_gtt_id": None,
            "protection_status": "pending_fill_confirmation",
        }

    async def place_exit_order_async(
        self,
        *,
        ticker: str,
        quantity: int,
        reference_price: float,
        product: str = "CNC",
    ) -> dict[str, object]:
        """Phase 7 (P2): place a SELL MARKET order to close an existing position.

        Bypasses risk sizing (the position already exists; we are closing, not
        opening). Routes to paper fill engine or live Kite according to
        ``cfg.trading.mode``.
        """
        if quantity <= 0:
            return {"status": "rejected", "reason": "invalid_quantity", "quantity": 0}

        order_id = f"exit-{uuid.uuid4().hex[:10]}"

        if cfg.trading.mode.value != "live":
            fill = self.fill_engine.fill(ticker, "sell", quantity, reference_price, order_id)
            return {
                "order_id": fill.order_id,
                "status": fill.status,
                "average_price": fill.average_price,
                "quantity": fill.quantity,
                "mode": cfg.trading.mode.value,
                "product": product,
            }

        if not has_kite_session():
            return {
                "status": "blocked",
                "reason": "KITE_SESSION_REQUIRED",
                "quantity": quantity,
                "mode": "live",
            }

        broker_tag = self._build_broker_tag(ticker)
        try:
            live_order_id = place_live_order(
                exchange=cfg.trading.exchange,
                ticker=ticker,
                side="sell",
                quantity=quantity,
                price=0.0,
                order_type="MARKET",
                product=product,
                tag=broker_tag,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "reason": f"exit_order_submission_failed:{exc}",
                "quantity": quantity,
                "mode": "live",
            }
        return {
            "order_id": live_order_id,
            "status": "submitted",
            "average_price": None,
            "quantity": quantity,
            "mode": "live",
            "product": product,
            "broker_tag": broker_tag,
        }
