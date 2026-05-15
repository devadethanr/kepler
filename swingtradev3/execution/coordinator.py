from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from config import cfg
from data.market_regime import MarketRegimeDetector
from memory.db import session_scope
from memory.repository import MemoryRepository
from models import AccountState, PositionState
from paths import CONTEXT_DIR
from policy.effective_policy import new_entries_block_reason
from regime_adapter import RegimeAdaptiveConfig
from storage import read_json, write_json
from tools.execution.alerts import AlertsTool
from tools.execution.gtt_manager import GTTManager
from tools.execution.order_execution import OrderExecutionTool
from tools.execution.risk_check import RiskCheckTool

from .auth_preflight import is_session_fresh
from .failure_tracker import FailureCounter
from .operator_controls import (
    append_flatten_result,
    clear_block_new_entries,
    clear_flatten_request,
    is_block_new_entries_active,
    is_exit_only_mode,
    is_trading_enabled,
    read_block_new_entries,
    read_flatten_request,
    set_block_new_entries,
)
from .protection_manager import ProtectionManager
from .session_guards import entry_stream_required_for_new_entries


QUEUED_ORDER_INTENT_STATUSES = {"queued"}
ACTIVE_ORDER_INTENT_STATUSES = {
    "submitting",
    "submitted",
    "entry_open",
    "entry_partially_filled",
    "entry_filled",
    "protection_pending",
}
OPEN_BROKER_ORDER_STATUSES = {
    "open",
    "open_pending",
    "modify_pending",
    "modify_validation_pending",
    "trigger_pending",
    "cancel_pending",
    "put_order_req_received",
    "after_market_order_req_received",
    "validation_pending",
}
APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"
ENTRY_BLOCK_ALERT_COOLDOWN_SECONDS = 15 * 60
SESSION_SCOPED_ENTRY_BLOCK_REASONS = {
    "broker_disconnected",
    "stale_quotes",
    "stream_unavailable",
}
IST = ZoneInfo("Asia/Kolkata")


def _now() -> datetime:
    return datetime.now(IST)


def _as_ist(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def _merge_payload(base: dict[str, Any], patch: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(base)
    if patch:
        merged.update(patch)
    return merged


class ExecutionCoordinator:
    def __init__(
        self,
        *,
        risk_tool: RiskCheckTool | None = None,
        order_tool: OrderExecutionTool | None = None,
        alerts_tool: AlertsTool | None = None,
        gtt_manager: GTTManager | None = None,
    ) -> None:
        self.risk_tool = risk_tool or RiskCheckTool()
        self.order_tool = order_tool or OrderExecutionTool()
        self.alerts_tool = alerts_tool or AlertsTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.protection_manager = ProtectionManager(
            gtt_manager=self.gtt_manager,
            alerts_tool=self.alerts_tool,
        )
        self._order_failures = FailureCounter(
            threshold=int(cfg.execution.safety.order_failure_threshold)
        )
        self._last_block_alert_at_by_reason: dict[str, datetime] = {}
        self._hydrate_order_failure_counter()

    def _hydrate_order_failure_counter(self) -> None:
        block = read_block_new_entries() or {}
        active_reasons = {
            str(item).strip()
            for item in block.get("active_reasons", [])
            if str(item).strip()
        }
        if "order_submission_failures" not in active_reasons:
            return

        count = self._order_failures.threshold
        with session_scope() as session:
            repo = MemoryRepository(session)
            incident = next(
                (
                    item
                    for item in repo.list_failure_incidents(status="open")
                    if str(item.get("incident_id") or "") == "order_submission_failures"
                ),
                None,
            )
        if incident is not None:
            payload = dict(incident.get("payload") or {})
            count = int(payload.get("consecutive_failures") or self._order_failures.threshold)

        self._order_failures.count = max(count, self._order_failures.threshold)
        self._order_failures._already_tripped = True

    def safety_counters(self) -> dict[str, Any]:
        return {
            "order_submission_failures": {
                "count": self._order_failures.count,
                "threshold": self._order_failures.threshold,
                "tripped": self._order_failures.is_tripped(),
            }
        }

    def pending_execution_requests(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            return repo.list_order_intents_by_status(QUEUED_ORDER_INTENT_STATUSES)

    def active_execution_requests(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            return repo.list_order_intents_by_status(ACTIVE_ORDER_INTENT_STATUSES)

    async def submit_queued_order_intents(self) -> int:
        if not is_trading_enabled():
            return 0
        if new_entries_block_reason() is not None or is_exit_only_mode():
            return 0
        if is_block_new_entries_active():
            block = read_block_new_entries() or {}
            reason = self._block_reason(block)
            if self._should_send_block_alert(reason):
                await self.alerts_tool.send_alert(
                    f"⛔ New entries blocked by reconciler: reason={reason}",
                    level="warning",
                )
            return 0
        submitted = 0
        for intent in self.pending_execution_requests():
            result = await self.submit_order_intent(str(intent["order_intent_id"]))
            if result != "ignored":
                submitted += 1
        return submitted

    @staticmethod
    def _block_reason(block: dict[str, Any]) -> str:
        reason = str(block.get("latest_reason") or block.get("reason") or "unknown").strip()
        return reason or "unknown"

    def _should_send_block_alert(self, reason: str) -> bool:
        if (
            reason in SESSION_SCOPED_ENTRY_BLOCK_REASONS
            and not entry_stream_required_for_new_entries()
        ):
            return False

        now = _now()
        last_alert_at = self._last_block_alert_at_by_reason.get(reason)
        if (
            last_alert_at is not None
            and (now - last_alert_at).total_seconds() < ENTRY_BLOCK_ALERT_COOLDOWN_SECONDS
        ):
            return False
        self._last_block_alert_at_by_reason[reason] = now
        return True

    async def reconcile_active_order_intents(self) -> int:
        advanced = 0
        for intent in self.active_execution_requests():
            result = await self.reconcile_order_intent(str(intent["order_intent_id"]))
            if result != "noop":
                advanced += 1
        return advanced

    async def submit_order_intent(self, order_intent_id: str) -> str:
        if not is_trading_enabled() or new_entries_block_reason() is not None or is_exit_only_mode():
            return "ignored"
        if is_block_new_entries_active():
            return "ignored"
        # Phase 7 (P4): per-order auth preflight. Only meaningful when we are
        # about to hit the live broker — paper / backtest have no session.
        if cfg.trading.mode.value == "live":
            fresh, reason, age_hours = is_session_fresh()
            if not fresh:
                detail: dict[str, Any] = {"stale_reason": reason or "unknown"}
                if age_hours is not None:
                    detail["session_age_hours"] = age_hours
                set_block_new_entries(
                    reason="stale_auth",
                    source="coordinator_preflight",
                    detail=detail,
                )
                return "ignored"
        with session_scope() as session:
            repo = MemoryRepository(session)
            intent = repo.get_order_intent(order_intent_id)
            account_payload = repo.get_account_state_payload()
        if intent is None:
            return "ignored"
        if intent["status"] not in QUEUED_ORDER_INTENT_STATUSES:
            return "ignored"

        payload = dict(intent["payload"])
        ticker = str(intent["ticker"]).upper()
        expires_at_raw = payload.get("expires_at")
        if expires_at_raw and _as_ist(datetime.fromisoformat(str(expires_at_raw))) <= _now():
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="expired",
                payload=_merge_payload(payload, {"expired_at": _now().isoformat()}),
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            self._clear_approval_execution_request(order_intent_id)
            return "expired"

        self._store_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status="submitting",
            payload=_merge_payload(payload, {"submission_started_at": _now().isoformat()}),
            broker_tag=intent["broker_tag"],
            source="execution_coordinator",
        )

        state = AccountState.model_validate(account_payload)
        score = float(payload.get("score") or 0.0)
        entry_zone = payload.get("entry_zone") or {}
        entry_price = float(entry_zone.get("high") or 0.0)
        stop_price = float(payload.get("stop_price") or 0.0)
        target_price = float(payload.get("target_price") or 0.0)

        regime = str(MarketRegimeDetector().detect_regime().get("regime", "neutral"))
        regime_config = RegimeAdaptiveConfig(regime)
        risk = self.risk_tool.check_risk(
            state,
            score,
            entry_price,
            stop_price,
            target_price,
            sector=payload.get("sector") if isinstance(payload.get("sector"), str) else None,
        )
        if not risk["approved"]:
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="failed",
                payload=_merge_payload(
                    payload,
                    {"failure_reason": risk["reason"], "failed_at": _now().isoformat()},
                ),
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            self._clear_approval_execution_request(order_intent_id)
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} execution failed risk checks: {risk['reason']}"
            )
            return "failed"

        adjusted_quantity = regime_config.position_size(base_quantity=int(risk["quantity"]))
        if adjusted_quantity <= 0:
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="failed",
                payload=_merge_payload(
                    payload,
                    {"failure_reason": f"regime_blocked:{regime}", "failed_at": _now().isoformat()},
                ),
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            self._clear_approval_execution_request(order_intent_id)
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} execution blocked because regime={regime} pauses entries."
            )
            return "failed"

        result = await self.order_tool.place_order_async(
            state=state,
            ticker=ticker,
            side="buy",
            score=score,
            price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            quantity=adjusted_quantity,
        )
        status = str(result.get("status") or "unknown")
        merged_payload = _merge_payload(
            payload,
            {
                **result,
                "broker_order_id": result.get("order_id"),
                "requested_quantity": int(result.get("quantity") or adjusted_quantity),
                "regime": regime,
                "submitted_at": _now().isoformat(),
            },
        )
        broker_tag = (
            str(result.get("broker_tag"))
            if result.get("broker_tag") not in (None, "")
            else intent["broker_tag"]
        )

        if status == "submitted":
            self._record_submission_success()
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="submitted",
                payload=merged_payload,
                broker_tag=broker_tag,
                source="execution_coordinator",
            )
            self._remove_pending_approval(order_intent_id)
            await self.alerts_tool.send_alert(
                f"🟢 Submitted live entry for {ticker}: order_id={result.get('order_id')}"
            )
            return "submitted"

        if status == "submission_uncertain":
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="submitting",
                payload=_merge_payload(
                    merged_payload,
                    {
                        "submission_uncertain_at": _now().isoformat(),
                        "reconciliation_required": True,
                    },
                ),
                broker_tag=broker_tag,
                source="execution_coordinator",
            )
            self._remove_pending_approval(order_intent_id)
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} entry submission timed out; waiting for broker reconciliation "
                f"tag={broker_tag}",
                level="warning",
            )
            return "submitting"

        if status == "filled":
            self._record_submission_success()
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="entry_filled",
                payload=merged_payload,
                broker_tag=broker_tag,
                source="execution_coordinator",
            )
            self._remove_pending_approval(order_intent_id)
            await self._materialize_filled_position(
                order_intent_id=order_intent_id,
                intent_payload=merged_payload,
                broker_order_id=str(result.get("order_id") or ""),
                filled_quantity=int(result.get("quantity") or adjusted_quantity),
                average_price=float(result.get("average_price") or entry_price),
            )
            await self._arm_protection(order_intent_id)
            return "filled"

        self._store_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status="failed",
            payload=_merge_payload(
                merged_payload,
                {"failure_reason": result.get("reason", status), "failed_at": _now().isoformat()},
            ),
            broker_tag=broker_tag,
            source="execution_coordinator",
        )
        self._clear_approval_execution_request(order_intent_id)
        await self.alerts_tool.send_alert(
            f"⚠️ {ticker} order submission failed: {result.get('reason', status)}"
        )
        self._record_submission_failure(
            ticker=ticker,
            reason=str(result.get("reason", status) or status),
        )
        return "failed"

    def _record_submission_success(self) -> None:
        if self._order_failures.record_success():
            clear_block_new_entries(
                source="coordinator",
                reason="order_submission_failures",
            )
            with session_scope() as session:
                repo = MemoryRepository(session)
                repo.upsert_failure_incident(
                    incident_id="order_submission_failures",
                    status="resolved",
                    severity="critical",
                    payload={"resolved_at": _now().isoformat()},
                    source="coordinator",
                )

    def _record_submission_failure(self, *, ticker: str, reason: str) -> None:
        if self._order_failures.record_failure():
            set_block_new_entries(
                reason="order_submission_failures",
                source="coordinator",
                detail={
                    "consecutive_failures": self._order_failures.count,
                    "threshold": self._order_failures.threshold,
                    "last_ticker": ticker,
                    "last_reason": reason,
                },
            )
            with session_scope() as session:
                repo = MemoryRepository(session)
                repo.upsert_failure_incident(
                    incident_id="order_submission_failures",
                    status="open",
                    severity="critical",
                    payload={
                        "at": _now().isoformat(),
                        "consecutive_failures": self._order_failures.count,
                        "threshold": self._order_failures.threshold,
                        "last_ticker": ticker,
                        "last_reason": reason,
                    },
                    source="coordinator",
                )

    # ------------------------------------------------------------------
    # Phase 7 (P2/P9/P10): flatten / manual close / reconcile-ack
    # ------------------------------------------------------------------

    async def process_flatten_request(self) -> int:
        """Poll the flatten_requested control and execute any pending request.

        Invoked on each coordinator tick (same cadence as approval submission).
        Returns the number of positions whose close-side order was submitted.
        """
        if not is_trading_enabled():
            # Trading disabled entirely — even operator flatten is gated.
            return 0
        request = read_flatten_request()
        if not request or not request.get("pending"):
            return 0

        if cfg.trading.mode.value == "live":
            # Broker-session freshness only matters when a live SELL will go out.
            fresh, stale_reason, age_hours = is_session_fresh()
            if not fresh:
                detail: dict[str, Any] = {"stale_reason": stale_reason or "unknown"}
                if age_hours is not None:
                    detail["session_age_hours"] = age_hours
                set_block_new_entries(
                    reason="stale_auth",
                    source="coordinator_flatten",
                    detail=detail,
                )
                return 0

        requested_tickers = request.get("tickers") or None
        reason = str(request.get("reason") or "operator_flatten")
        multi_day_acked = set(request.get("multi_day_holdings_acked") or [])
        flatten_id = str(request.get("flatten_id") or "")

        positions = self._open_positions()
        if requested_tickers:
            tickers_filter = {str(t).strip().upper() for t in requested_tickers}
            positions = [p for p in positions if p.ticker.upper() in tickers_filter]

        submitted = 0
        for position in positions:
            result = await self._flatten_single_position(
                position=position,
                reason=reason,
                multi_day_acked=multi_day_acked,
                flatten_id=flatten_id,
            )
            append_flatten_result(
                ticker=position.ticker.upper(),
                outcome=result,
                source="coordinator_flatten",
            )
            if result.get("status") in {"submitted", "filled"}:
                submitted += 1

        # Mark request complete regardless — outcomes are preserved in
        # ``results``. Operator can inspect via GET /ops/safety.
        clear_flatten_request(source="coordinator_flatten", reason="processed")
        return submitted

    def _open_positions(self) -> list[PositionState]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            payload = repo.get_account_state_payload()
        state = AccountState.model_validate(payload or {})
        return [p for p in state.positions if p.quantity > 0]

    async def _flatten_single_position(
        self,
        *,
        position: PositionState,
        reason: str,
        multi_day_acked: set[str],
        flatten_id: str,
    ) -> dict[str, Any]:
        ticker = position.ticker.upper()
        lifecycle_state = str(position.lifecycle_state or "open").strip().lower()

        if lifecycle_state == "reconcile_required":
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} flatten blocked: lifecycle_state=reconcile_required. "
                "Use reconcile ack first.",
                level="warning",
            )
            return {
                "status": "blocked",
                "reason": "reconcile_required",
                "ticker": ticker,
                "lifecycle_state": lifecycle_state,
            }

        if lifecycle_state == "closing":
            return {
                "status": "blocked",
                "reason": "already_closing",
                "ticker": ticker,
                "lifecycle_state": lifecycle_state,
            }

        if lifecycle_state not in {"open", "operator_intervention"}:
            return {
                "status": "blocked",
                "reason": "lifecycle_state_not_flattenable",
                "ticker": ticker,
                "lifecycle_state": lifecycle_state,
            }

        if lifecycle_state == "operator_intervention":
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} flatten proceeding from operator_intervention state.",
                level="warning",
            )

        # P9: DDPI/POA guard for multi-day CNC holdings.
        if not self._ddpi_allows_exit(position=position, multi_day_acked=multi_day_acked):
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} flatten blocked — multi-day CNC holding without DDPI. "
                f"Resubmit with multi_day_holdings_acked=['{ticker}'] to proceed.",
                level="critical",
            )
            return {"status": "blocked", "reason": "ddpi_required", "ticker": ticker}

        # Cancel the OCO GTT (if any) so broker does not fire both sides.
        if position.oco_gtt_id:
            try:
                await self.gtt_manager.cancel_gtt_async(str(position.oco_gtt_id))
            except Exception as exc:
                # Non-fatal — log and continue. The SELL MARKET will still clear
                # the position; the reconciler will mop up a stranded GTT.
                await self.alerts_tool.send_alert(
                    f"⚠️ {ticker} GTT cancel during flatten failed: {exc}",
                    level="warning",
                )

        reference_price = float(position.current_price or position.entry_price or 0.0)
        order_result = await self.order_tool.place_exit_order_async(
            ticker=ticker,
            quantity=int(position.quantity),
            reference_price=reference_price,
            product=str(position.product or "CNC"),
        )
        status = str(order_result.get("status") or "unknown")

        if status == "filled":
            # Paper / backtest path — fill is synchronous. Finalize trade record.
            await self._finalize_flatten_fill(
                position=position,
                order_result=order_result,
                reason=reason,
            )
            self._resolve_protection_incident_and_unblock_if_clear(
                ticker=ticker,
                source="coordinator_flatten",
                reason=reason,
            )
        elif status == "submitted":
            self._mark_position_closing(
                ticker=ticker,
                exit_order_id=str(order_result.get("order_id") or ""),
                reason=reason,
                flatten_id=flatten_id,
            )
            self._resolve_protection_incident_and_unblock_if_clear(
                ticker=ticker,
                source="coordinator_flatten",
                reason=reason,
            )
            await self.alerts_tool.send_alert(
                f"🧹 {ticker} flatten submitted: order_id={order_result.get('order_id')} "
                f"reason={reason}",
                level="info",
            )
        else:
            await self.alerts_tool.send_alert(
                f"⚠️ {ticker} flatten failed: status={status} "
                f"reason={order_result.get('reason', status)}",
                level="critical",
            )

        return {
            "status": status,
            "ticker": ticker,
            "order_id": order_result.get("order_id"),
            "mode": order_result.get("mode"),
            "reason_if_failed": order_result.get("reason"),
        }

    def _ddpi_allows_exit(self, *, position: PositionState, multi_day_acked: set[str]) -> bool:
        """Phase 7 (P9): without DDPI we cannot silently sell multi-day holdings."""
        # Deferred import so unit tests can stub ops.phase0_check cheaply.
        try:
            from ops.phase0_check import check_ddpi_poa
        except Exception:
            return True

        try:
            result = check_ddpi_poa()
        except Exception:
            return True

        if getattr(result, "status", "PASS") == "PASS":
            return True

        ticker = position.ticker.upper()
        opened_at = getattr(position, "opened_at", None)
        if opened_at is None:
            return True
        try:
            opened_at_utc = (
                opened_at.astimezone(timezone.utc)
                if opened_at.tzinfo is not None
                else opened_at.astimezone().astimezone(timezone.utc)
            )
            opened_days_ago = (datetime.now(timezone.utc) - opened_at_utc).days
        except Exception:
            opened_days_ago = 0
        if opened_days_ago < 1:
            return True
        return ticker in multi_day_acked

    def _mark_position_closing(
        self,
        *,
        ticker: str,
        exit_order_id: str,
        reason: str,
        flatten_id: str,
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.update_position_state(
                position_id=ticker,
                new_state="closing",
                source="coordinator_flatten",
                detail=f"flatten:{reason}:order={exit_order_id}:req={flatten_id}",
            )

    async def _finalize_flatten_fill(
        self,
        *,
        position: PositionState,
        order_result: dict[str, Any],
        reason: str,
    ) -> None:
        """Paper/backtest path: broker has no postback, so finalize inline."""
        ticker = position.ticker.upper()
        exit_price = float(order_result.get("average_price") or position.current_price or position.entry_price)
        filled_quantity = int(order_result.get("quantity") or position.quantity)
        closed_at = _now()
        pnl_abs = (exit_price - position.entry_price) * filled_quantity
        pnl_pct = ((exit_price / position.entry_price) - 1) * 100 if position.entry_price else 0.0

        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())
            remaining = [p.model_copy() for p in state.positions if p.ticker.upper() != ticker]
            next_state = state.model_copy(update={"positions": remaining})
            repo.replace_account_state(next_state.model_dump(mode="json"), source="coordinator_flatten")
            repo.upsert_trade(
                trade_id=f"trade:{ticker}:{closed_at.strftime('%Y%m%d%H%M%S')}",
                ticker=ticker,
                quantity=filled_quantity,
                entry_price=position.entry_price,
                exit_price=exit_price,
                opened_at=position.opened_at,
                closed_at=closed_at,
                pnl_abs=pnl_abs,
                pnl_pct=pnl_pct,
                exit_reason=f"operator_flatten:{reason}",
                payload={
                    "ticker": ticker,
                    "sector": position.sector,
                    "skill_version": position.skill_version,
                    "research_date": position.research_date,
                    "product": position.product,
                    "entry_order_id": position.entry_order_id,
                    "exit_order_id": str(order_result.get("order_id") or ""),
                    "flatten_reason": reason,
                },
                source="coordinator_flatten",
            )

    def _resolve_protection_incident_and_unblock_if_clear(
        self,
        *,
        ticker: str,
        source: str,
        reason: str,
    ) -> None:
        now_iso = _now().isoformat()
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_failure_incident(
                incident_id=f"protection:{ticker}",
                status="resolved",
                severity="critical",
                payload={
                    "ticker": ticker,
                    "resolved_at": now_iso,
                    "resolution_reason": reason,
                },
                source=source,
            )
            open_protection_incidents = [
                item
                for item in repo.list_failure_incidents(status="open")
                if str(item.get("incident_id") or "").startswith("protection:")
            ]

        if not open_protection_incidents:
            clear_block_new_entries(source=source, reason="gtt_recovery_failures")

    async def resolve_reconcile_required(
        self,
        *,
        position_id: str,
        resolution: str,
        source: str,
    ) -> dict[str, Any]:
        """Phase 7 (P10): operator exit for positions pinned in reconcile_required.

        - ``resolution="broker_close"``: book the position as closed at last-known
          price (broker asserted it was gone), delete the position row, write a trade.
        - ``resolution="retain"``: flip lifecycle back to open — operator believes
          the next reconcile will reconfirm.
        """
        normalized = position_id.upper()
        if resolution not in {"broker_close", "retain"}:
            return {"status": "rejected", "reason": "invalid_resolution"}

        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())
            target = next((p for p in state.positions if p.ticker.upper() == normalized), None)
            if target is None:
                return {"status": "rejected", "reason": "position_not_found"}
            if str(target.lifecycle_state or "").strip().lower() != "reconcile_required":
                return {"status": "rejected", "reason": "position_not_reconcile_required"}

            if resolution == "retain":
                repo.update_position_state(
                    position_id=normalized,
                    new_state="open",
                    source=source,
                    detail="operator_retain",
                )
                return {"status": "retained", "position_id": normalized}

            # broker_close
            exit_price = float(target.current_price or target.entry_price or 0.0)
            filled_quantity = int(target.quantity)
            closed_at = _now()
            pnl_abs = (exit_price - target.entry_price) * filled_quantity
            pnl_pct = ((exit_price / target.entry_price) - 1) * 100 if target.entry_price else 0.0

            remaining = [p.model_copy() for p in state.positions if p.ticker.upper() != normalized]
            next_state = state.model_copy(update={"positions": remaining})
            repo.replace_account_state(next_state.model_dump(mode="json"), source=source)
            repo.upsert_trade(
                trade_id=f"trade:{normalized}:{closed_at.strftime('%Y%m%d%H%M%S')}",
                ticker=normalized,
                quantity=filled_quantity,
                entry_price=target.entry_price,
                exit_price=exit_price,
                opened_at=target.opened_at,
                closed_at=closed_at,
                pnl_abs=pnl_abs,
                pnl_pct=pnl_pct,
                exit_reason="operator_ack:broker_close",
                payload={
                    "ticker": normalized,
                    "sector": target.sector,
                    "skill_version": target.skill_version,
                    "product": target.product,
                    "resolution": "broker_close",
                },
                source=source,
            )
        self._resolve_protection_incident_and_unblock_if_clear(
            ticker=normalized,
            source=source,
            reason="broker_close",
        )
        return {
            "status": "broker_closed",
            "position_id": normalized,
            "exit_price": exit_price,
            "quantity": filled_quantity,
        }

    async def reconcile_order_intent(self, order_intent_id: str) -> str:
        with session_scope() as session:
            repo = MemoryRepository(session)
            intent = repo.get_order_intent(order_intent_id)
        if intent is None:
            return "noop"

        status = str(intent["status"])
        if status == "protection_pending":
            await self._arm_protection(order_intent_id)
            return "advanced"
        if status not in {
            "submitting",
            "submitted",
            "entry_open",
            "entry_partially_filled",
            "entry_filled",
        }:
            return "noop"

        payload = dict(intent["payload"])
        broker_order = self._find_broker_order(intent)
        if broker_order is None:
            return "noop"

        broker_payload = dict(broker_order["payload"])
        broker_order_id = str(broker_order["broker_order_id"])
        requested_quantity = int(
            payload.get("requested_quantity")
            or broker_payload.get("quantity")
            or payload.get("quantity")
            or 0
        )
        fill_summary = self._fill_summary(broker_order_id)
        filled_quantity = max(fill_summary["filled_quantity"], int(broker_payload.get("filled_quantity") or 0))
        average_price = fill_summary["average_price"]
        if average_price is None:
            average_price = float(broker_payload.get("average_price") or 0.0) or None
        next_status = self._derive_intent_status(
            broker_status=str(broker_order["status"]),
            requested_quantity=requested_quantity,
            filled_quantity=filled_quantity,
        )
        next_payload = _merge_payload(
            payload,
            {
                "broker_order_id": broker_order_id,
                "exchange_order_id": broker_order.get("exchange_order_id"),
                "broker_order_status": broker_order["status"],
                "filled_quantity": filled_quantity,
                "pending_quantity": int(broker_payload.get("pending_quantity") or 0),
                "average_price": average_price,
                "last_broker_update_at": broker_payload.get("exchange_update_timestamp")
                or broker_payload.get("order_timestamp"),
            },
        )
        if next_status in {"cancelled", "failed"}:
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=intent["ticker"],
                status=next_status,
                payload=next_payload,
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            return "advanced"

        if next_status in {"entry_open", "entry_partially_filled"}:
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=intent["ticker"],
                status=next_status,
                payload=next_payload,
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            return "advanced"

        if next_status == "entry_filled":
            if average_price is None:
                return "noop"
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=intent["ticker"],
                status="entry_filled",
                payload=next_payload,
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            await self._materialize_filled_position(
                order_intent_id=order_intent_id,
                intent_payload=next_payload,
                broker_order_id=broker_order_id,
                filled_quantity=max(filled_quantity, requested_quantity),
                average_price=average_price,
            )
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=intent["ticker"],
                status="protection_pending",
                payload=_merge_payload(
                    next_payload,
                    {"position_materialized_at": _now().isoformat()},
                ),
                broker_tag=intent["broker_tag"],
                source="execution_coordinator",
            )
            await self._arm_protection(order_intent_id)
            return "advanced"
        return "noop"

    async def _materialize_filled_position(
        self,
        *,
        order_intent_id: str,
        intent_payload: dict[str, Any],
        broker_order_id: str,
        filled_quantity: int,
        average_price: float,
    ) -> None:
        ticker = str(intent_payload["ticker"]).upper()
        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())
            positions = [position.model_copy() for position in state.positions if position.ticker.upper() != ticker]
            position = PositionState(
                ticker=ticker,
                quantity=filled_quantity,
                entry_price=average_price,
                current_price=average_price,
                stop_price=float(intent_payload["stop_price"]),
                target_price=float(intent_payload["target_price"]),
                opened_at=_now(),
                entry_order_id=broker_order_id or None,
                product=str(intent_payload.get("product") or "CNC"),
                thesis_score=float(intent_payload.get("score") or 0.0),
                research_date=intent_payload.get("research_date"),
                skill_version=intent_payload.get("skill_version"),
                sector=intent_payload.get("sector"),
            )
            positions.append(position)
            next_state = state.model_copy(update={"positions": positions})
            repo.replace_account_state(
                next_state.model_dump(mode="json"),
                source="execution_coordinator",
            )
            repo.append_execution_event(
                event_type="order_intent_position_materialized",
                entity_type="order_intent",
                entity_id=order_intent_id,
                source="execution_coordinator",
                payload={
                    "ticker": ticker,
                    "broker_order_id": broker_order_id,
                    "quantity": filled_quantity,
                    "average_price": average_price,
                },
            )

    async def _arm_protection(self, order_intent_id: str) -> None:
        await self.protection_manager.arm_for_order_intent(order_intent_id)

    def _find_broker_order(self, intent: dict[str, Any]) -> dict[str, Any] | None:
        payload = dict(intent["payload"])
        broker_order_id = str(payload.get("broker_order_id") or "").strip()
        broker_tag = str(intent.get("broker_tag") or payload.get("broker_tag") or "").strip()
        with session_scope() as session:
            repo = MemoryRepository(session)
            if broker_order_id:
                order = repo.get_broker_order(broker_order_id)
                if order is not None:
                    return order
            if broker_tag:
                orders = repo.list_broker_orders_by_tag(broker_tag)
                if orders:
                    return orders[0]
        return None

    def _fill_summary(self, broker_order_id: str) -> dict[str, Any]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            fills = repo.list_broker_fills(broker_order_id)
        if not fills:
            return {"filled_quantity": 0, "average_price": None}
        filled_quantity = sum(int(item["quantity"]) for item in fills)
        gross = sum(int(item["quantity"]) * float(item["fill_price"]) for item in fills)
        average_price = gross / filled_quantity if filled_quantity > 0 else None
        return {"filled_quantity": filled_quantity, "average_price": average_price}

    def _store_order_intent(
        self,
        *,
        order_intent_id: str,
        ticker: str,
        status: str,
        payload: dict[str, Any],
        broker_tag: str | None,
        source: str,
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status=status,
                approval_id=(
                    str(payload.get("approval_id"))
                    if payload.get("approval_id") not in (None, "")
                    else None
                ),
                entry_intent_id=(
                    str(payload.get("entry_intent_id"))
                    if payload.get("entry_intent_id") not in (None, "")
                    else None
                ),
                broker_order_id=(
                    str(payload.get("broker_order_id"))
                    if payload.get("broker_order_id") not in (None, "")
                    else None
                ),
                broker_tag=broker_tag,
                payload=payload,
                source=source,
            )

    def _clear_approval_execution_request(self, order_intent_id: str) -> None:
        payload = read_json(APPROVALS_PATH, [])
        changed = False
        for item in payload:
            if str(item.get("order_intent_id") or "").strip() != order_intent_id:
                continue
            if item.get("execution_requested") is not False:
                item["execution_requested"] = False
                changed = True
            if item.get("execution_request_id") is not None:
                item["execution_request_id"] = None
                changed = True
        if changed:
            write_json(APPROVALS_PATH, payload)

    def _remove_pending_approval(self, order_intent_id: str) -> None:
        payload = read_json(APPROVALS_PATH, [])
        next_payload = [
            item for item in payload if str(item.get("order_intent_id") or "").strip() != order_intent_id
        ]
        if len(next_payload) != len(payload):
            write_json(APPROVALS_PATH, next_payload)

    def _derive_intent_status(
        self,
        *,
        broker_status: str,
        requested_quantity: int,
        filled_quantity: int,
    ) -> str:
        normalized = broker_status.strip().lower()
        if normalized == "complete":
            return "entry_filled"
        if normalized == "rejected":
            return "failed"
        if normalized == "cancelled":
            return "cancelled"
        if filled_quantity > 0 and requested_quantity > 0 and filled_quantity < requested_quantity:
            return "entry_partially_filled"
        if normalized in OPEN_BROKER_ORDER_STATUSES or normalized == "open":
            return "entry_open"
        return "submitted"
