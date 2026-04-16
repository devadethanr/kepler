from __future__ import annotations

import uuid

from auth.kite.client import has_kite_session, place_live_order
from config import cfg, runtime_flags
from integrations.kite.mcp_client import KiteMCPClient
from models import AccountState
from paper.fill_engine import FillEngine
from tools.execution.gtt_manager import GTTManager
from tools.execution.risk_check import RiskCheckTool


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

            order_id = place_live_order(
                exchange=cfg.trading.exchange,
                ticker=ticker,
                side=side,
                quantity=resolved_quantity,
                price=price,
            )
            return {
                "order_id": order_id,
                "status": "submitted",
                "average_price": None,
                "quantity": resolved_quantity,
                "mode": "live",
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
            "position_id": position_id,
            "stop_gtt_id": gtt.position_id,
            "target_gtt_id": gtt.position_id,
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

        if has_kite_session():
            try:
                order_id = place_live_order(
                    exchange=cfg.trading.exchange,
                    ticker=ticker,
                    side=side,
                    quantity=resolved_quantity,
                    price=price,
                )
            except Exception:
                return {
                    "status": "failed",
                    "reason": "live_order_submission_failed",
                    "quantity": resolved_quantity,
                    "mode": "live",
                }
        return {
            "order_id": order_id,
            "status": "submitted",
            "average_price": None,
            "quantity": resolved_quantity,
            "mode": "live",
            "position_id": None,
            "stop_gtt_id": None,
            "target_gtt_id": None,
            "protection_status": "pending_fill_confirmation",
        }
