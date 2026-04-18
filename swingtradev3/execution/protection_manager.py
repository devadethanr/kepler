from __future__ import annotations

from datetime import datetime
from typing import Any

from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import AccountState, GTTOrder, PositionState
from tools.execution.alerts import AlertsTool
from tools.execution.gtt_manager import GTTManager


ACTIVE_ORDER_INTENT_STATUSES = {
    "entry_filled",
    "protection_pending",
    "protected",
}
RECOVERABLE_TRIGGER_STATUSES = {"cancelled", "deleted", "disabled", "expired"}
OPEN_EXIT_ORDER_STATUSES = {
    "open",
    "open_pending",
    "modify_pending",
    "modify_validation_pending",
    "trigger_pending",
    "cancel_pending",
    "put_order_req_received",
    "after_market_order_req_received",
    "validation_pending",
    "update",
}
FAILED_EXIT_ORDER_STATUSES = {"failed", "rejected", "cancelled"}
RECOVERY_FAILURE_THRESHOLD = 3


def _now() -> datetime:
    return datetime.now()


def _merge_payload(base: dict[str, Any], patch: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(base)
    if patch:
        merged.update(patch)
    return merged


class ProtectionManager:
    def __init__(
        self,
        *,
        gtt_manager: GTTManager | None = None,
        alerts_tool: AlertsTool | None = None,
    ) -> None:
        self.gtt_manager = gtt_manager or GTTManager()
        self.alerts_tool = alerts_tool or AlertsTool()

    async def arm_for_order_intent(self, order_intent_id: str) -> str:
        with session_scope() as session:
            repo = MemoryRepository(session)
            intent = repo.get_order_intent(order_intent_id)
            state = AccountState.model_validate(repo.get_account_state_payload())
        if intent is None:
            return "ignored"

        ticker = str(intent["ticker"]).upper()
        payload = dict(intent["payload"])
        position = next((item for item in state.positions if item.ticker.upper() == ticker), None)
        if position is None:
            return "ignored"

        if payload.get("oco_gtt_id"):
            self._replace_position(
                ticker=ticker,
                updater=lambda item: item.model_copy(
                    update={"oco_gtt_id": str(payload["oco_gtt_id"]), "lifecycle_state": "open"}
                ),
                source="protection_manager",
            )
            self._store_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status="protected",
                payload=payload,
                intent=intent,
            )
            return "protected"

        try:
            gtt = await self.gtt_manager.place_gtt_async(
                position_id=position.ticker.upper(),
                ticker=position.ticker,
                stop_price=position.stop_price,
                target_price=position.target_price,
                quantity=position.quantity,
            )
        except Exception as exc:
            self._open_incident(
                ticker=ticker,
                incident_id=f"protection:{ticker}",
                severity="warning",
                payload={"detail": str(exc), "at": _now().isoformat(), "kind": "arm_failed"},
            )
            await self.alerts_tool.send_alert(
                f"🔴 Failed to arm protection for {ticker}: {exc}",
                level="warning",
            )
            return "failed"

        oco_gtt_id = str(gtt.oco_gtt_id)
        now_iso = _now().isoformat()
        self._replace_position(
            ticker=ticker,
            updater=lambda item: item.model_copy(
                update={
                    "oco_gtt_id": oco_gtt_id,
                    "lifecycle_state": "open",
                }
            ),
            source="protection_manager",
        )
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id=oco_gtt_id,
                position_id=ticker,
                ticker=ticker,
                status="active",
                payload={
                    "ticker": ticker,
                    "order_intent_id": order_intent_id,
                    "stop_price": position.stop_price,
                    "target_price": position.target_price,
                    "quantity": position.quantity,
                    "armed_at": now_iso,
                    "broker_status": "active",
                    "recovery_attempts": 0,
                },
                source="protection_manager",
            )
            repo.upsert_failure_incident(
                incident_id=f"protection:{ticker}",
                status="resolved",
                severity="warning",
                payload={"ticker": ticker, "resolved_at": now_iso},
                source="protection_manager",
            )

        self._store_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status="protected",
            payload=_merge_payload(
                payload,
                {"oco_gtt_id": oco_gtt_id, "protection_armed_at": now_iso},
            ),
            intent=intent,
        )
        await self.alerts_tool.send_alert(f"🛡️ Armed protection for {ticker}: gtt={oco_gtt_id}")
        return "protected"

    async def run_watchdog(self) -> dict[str, int]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())

        if not state.positions:
            return {"positions": 0, "recovered": 0, "triggered": 0, "closed": 0}

        summary = {"positions": len(state.positions), "recovered": 0, "triggered": 0, "closed": 0}
        for position in state.positions:
            result = await self._reconcile_position(position)
            if result in summary:
                summary[result] += 1
        return summary

    async def _reconcile_position(self, position: PositionState) -> str:
        ticker = position.ticker.upper()
        with session_scope() as session:
            repo = MemoryRepository(session)
            trigger = (
                repo.get_protective_trigger(str(position.oco_gtt_id))
                if position.oco_gtt_id
                else repo.get_protective_trigger_for_ticker(ticker)
            )
            intent = self._current_order_intent(repo, ticker)

        if not position.oco_gtt_id:
            recovered = await self._recover_protection(position, trigger, intent, reason="missing_oco_gtt_id")
            return "recovered" if recovered else "positions"

        gtt = await self.gtt_manager.get_gtt_async(str(position.oco_gtt_id))
        if gtt is None:
            recovered = await self._recover_protection(position, trigger, intent, reason="missing_trigger")
            return "recovered" if recovered else "positions"

        row_status = self._trigger_row_status(gtt)
        payload = self._trigger_payload(
            position=position,
            gtt=gtt,
            trigger=trigger,
            intent=intent,
        )
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id=gtt.oco_gtt_id,
                position_id=ticker,
                ticker=ticker,
                status=row_status,
                payload=payload,
                source="gtt_watchdog",
            )

        if row_status == "active":
            self._replace_position(
                ticker=ticker,
                updater=lambda item: item.model_copy(
                    update={"oco_gtt_id": gtt.oco_gtt_id, "lifecycle_state": "open"}
                ),
                source="gtt_watchdog",
            )
            if intent is not None and str(intent["status"]) in ACTIVE_ORDER_INTENT_STATUSES:
                self._store_order_intent(
                    order_intent_id=str(intent["order_intent_id"]),
                    ticker=ticker,
                    status="protected",
                    payload=_merge_payload(
                        dict(intent["payload"]),
                        {"oco_gtt_id": gtt.oco_gtt_id, "last_protection_check_at": _now().isoformat()},
                    ),
                    intent=intent,
                )
            return "positions"

        if row_status in RECOVERABLE_TRIGGER_STATUSES:
            recovered = await self._recover_protection(position, trigger, intent, reason=row_status)
            return "recovered" if recovered else "positions"

        if row_status in {"rejected", "triggered", "exit_order_open", "exit_filled"}:
            return await self._handle_triggered_exit(position, gtt, intent, trigger_status=row_status)

        return "positions"

    async def _handle_triggered_exit(
        self,
        position: PositionState,
        gtt: GTTOrder,
        intent: dict[str, Any] | None,
        *,
        trigger_status: str,
    ) -> str:
        ticker = position.ticker.upper()
        exit_order_id = gtt.exit_order_id
        exit_order_status = gtt.exit_order_status

        if exit_order_id:
            with session_scope() as session:
                repo = MemoryRepository(session)
                broker_order = repo.get_broker_order(exit_order_id)
            if broker_order is not None:
                exit_order_status = str(
                    broker_order["status"] or broker_order["payload"].get("status") or exit_order_status or ""
                ).strip().lower()

        if gtt.exit_rejection_reason or exit_order_status in FAILED_EXIT_ORDER_STATUSES:
            await self._mark_operator_intervention(
                position,
                detail=gtt.exit_rejection_reason or f"exit_order_status={exit_order_status}",
            )
            return "triggered"

        if exit_order_status == "complete" and exit_order_id:
            closed = await self._close_position_from_exit(position, gtt, intent, exit_order_id=exit_order_id)
            return "closed" if closed else "triggered"

        next_lifecycle = "closing" if trigger_status in {"triggered", "exit_order_open"} else position.lifecycle_state
        self._replace_position(
            ticker=ticker,
            updater=lambda item: item.model_copy(update={"lifecycle_state": next_lifecycle}),
            source="gtt_watchdog",
        )
        return "triggered"

    async def _close_position_from_exit(
        self,
        position: PositionState,
        gtt: GTTOrder,
        intent: dict[str, Any] | None,
        *,
        exit_order_id: str,
    ) -> bool:
        ticker = position.ticker.upper()
        with session_scope() as session:
            repo = MemoryRepository(session)
            fills = repo.list_broker_fills(exit_order_id)
            state = AccountState.model_validate(repo.get_account_state_payload())

        filled_quantity = sum(int(item["quantity"]) for item in fills)
        if filled_quantity <= 0:
            return False

        gross = sum(int(item["quantity"]) * float(item["fill_price"]) for item in fills)
        exit_price = gross / filled_quantity
        closed_at = _now()
        exit_reason = "gtt_stop" if gtt.triggered_leg == "stop" else "gtt_target"
        pnl_abs = (exit_price - position.entry_price) * filled_quantity
        pnl_pct = ((exit_price / position.entry_price) - 1) * 100 if position.entry_price else 0.0

        remaining_positions = [
            item.model_copy()
            for item in state.positions
            if item.ticker.upper() != ticker
        ]
        next_state = state.model_copy(update={"positions": remaining_positions})

        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.replace_account_state(next_state.model_dump(mode="json"), source="protection_manager")
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
                exit_reason=exit_reason,
                payload={
                    "setup_type": (intent or {}).get("payload", {}).get("setup_type"),
                    "thesis_reasoning": (intent or {}).get("payload", {}).get("confidence_reasoning"),
                    "research_date": position.research_date,
                    "skill_version": position.skill_version,
                    "sector": position.sector,
                    "entry_order_id": position.entry_order_id,
                    "exit_order_id": exit_order_id,
                    "gtt_id": position.oco_gtt_id,
                    "triggered_leg": gtt.triggered_leg,
                },
                source="protection_manager",
            )
            if position.oco_gtt_id:
                repo.upsert_protective_trigger(
                    protective_trigger_id=str(position.oco_gtt_id),
                    position_id=ticker,
                    ticker=ticker,
                    status="exit_filled",
                    payload={
                        "ticker": ticker,
                        "broker_status": "triggered",
                        "triggered_leg": gtt.triggered_leg,
                        "exit_order_id": exit_order_id,
                        "exit_order_status": "complete",
                        "exit_filled_at": closed_at.isoformat(),
                        "exit_fill_price": exit_price,
                    },
                    source="protection_manager",
                )
            repo.upsert_failure_incident(
                incident_id=f"protection:{ticker}",
                status="resolved",
                severity="warning",
                payload={"ticker": ticker, "resolved_at": closed_at.isoformat()},
                source="protection_manager",
            )

        if intent is not None:
            self._store_order_intent(
                order_intent_id=str(intent["order_intent_id"]),
                ticker=ticker,
                status="protected",
                payload=_merge_payload(
                    dict(intent["payload"]),
                    {
                        "exit_order_id": exit_order_id,
                        "exit_order_status": "complete",
                        "closed_at": closed_at.isoformat(),
                        "closed_reason": exit_reason,
                    },
                ),
                intent=intent,
            )

        try:
            from api.tasks.event_bus import BusEvent, EventType, event_bus

            payload = {
                "ticker": ticker,
                "entry_price": position.entry_price,
                "pnl_pct": round(pnl_pct, 2),
            }
            if exit_reason == "gtt_stop":
                payload["stop_price"] = exit_price
                event_type = EventType.STOP_HIT
            else:
                payload["target_price"] = exit_price
                event_type = EventType.TARGET_HIT
            await event_bus.publish(BusEvent(type=event_type, payload=payload, source="protection_manager"))
        except Exception:
            pass

        await self.alerts_tool.send_alert(
            f"✅ Closed {ticker} via {exit_reason}: qty={filled_quantity} exit={exit_price:.2f}"
        )
        return True

    async def _recover_protection(
        self,
        position: PositionState,
        trigger: dict[str, Any] | None,
        intent: dict[str, Any] | None,
        *,
        reason: str,
    ) -> bool:
        ticker = position.ticker.upper()
        previous_payload = dict(trigger["payload"]) if trigger is not None else {}
        attempts = int(previous_payload.get("recovery_attempts") or 0) + 1
        if attempts > RECOVERY_FAILURE_THRESHOLD:
            await self._mark_operator_intervention(
                position,
                detail=f"protection recovery exceeded threshold after {attempts - 1} failures",
            )
            return False

        try:
            gtt = await self.gtt_manager.place_gtt_async(
                position_id=ticker,
                ticker=ticker,
                stop_price=position.stop_price,
                target_price=position.target_price,
                quantity=position.quantity,
            )
        except Exception as exc:
            with session_scope() as session:
                repo = MemoryRepository(session)
                repo.upsert_protective_trigger(
                    protective_trigger_id=str(position.oco_gtt_id or (trigger or {}).get("protective_trigger_id") or ticker),
                    position_id=ticker,
                    ticker=ticker,
                    status="recreate_required",
                    payload={
                        **previous_payload,
                        "ticker": ticker,
                        "stop_price": position.stop_price,
                        "target_price": position.target_price,
                        "quantity": position.quantity,
                        "recovery_attempts": attempts,
                        "recovery_reason": reason,
                        "last_recovery_error": str(exc),
                        "last_recovery_error_at": _now().isoformat(),
                    },
                    source="gtt_watchdog",
                )
            self._open_incident(
                ticker=ticker,
                incident_id=f"protection:{ticker}",
                severity="critical" if attempts >= RECOVERY_FAILURE_THRESHOLD else "warning",
                payload={
                    "detail": str(exc),
                    "at": _now().isoformat(),
                    "reason": reason,
                    "recovery_attempts": attempts,
                },
            )
            if attempts >= RECOVERY_FAILURE_THRESHOLD:
                await self._mark_operator_intervention(position, detail=str(exc))
            return False

        oco_gtt_id = str(gtt.oco_gtt_id)
        now_iso = _now().isoformat()
        self._replace_position(
            ticker=ticker,
            updater=lambda item: item.model_copy(
                update={"oco_gtt_id": oco_gtt_id, "lifecycle_state": "open"}
            ),
            source="gtt_watchdog",
        )
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id=oco_gtt_id,
                position_id=ticker,
                ticker=ticker,
                status="active",
                payload={
                    "ticker": ticker,
                    "stop_price": position.stop_price,
                    "target_price": position.target_price,
                    "quantity": position.quantity,
                    "armed_at": now_iso,
                    "recovered_at": now_iso,
                    "recovery_attempts": attempts,
                    "recovery_reason": reason,
                    "broker_status": "active",
                    "order_intent_id": str(intent["order_intent_id"]) if intent is not None else None,
                },
                source="gtt_watchdog",
            )
            repo.upsert_failure_incident(
                incident_id=f"protection:{ticker}",
                status="resolved",
                severity="warning",
                payload={"ticker": ticker, "resolved_at": now_iso},
                source="gtt_watchdog",
            )

        if intent is not None:
            self._store_order_intent(
                order_intent_id=str(intent["order_intent_id"]),
                ticker=ticker,
                status="protected",
                payload=_merge_payload(
                    dict(intent["payload"]),
                    {
                        "oco_gtt_id": oco_gtt_id,
                        "protection_recovered_at": now_iso,
                        "protection_recovery_reason": reason,
                    },
                ),
                intent=intent,
            )

        await self.alerts_tool.send_alert(
            f"🛡️ Recreated protection for {ticker}: gtt={oco_gtt_id} reason={reason}"
        )
        return True

    async def _mark_operator_intervention(self, position: PositionState, *, detail: str) -> None:
        ticker = position.ticker.upper()
        now_iso = _now().isoformat()
        self._replace_position(
            ticker=ticker,
            updater=lambda item: item.model_copy(update={"lifecycle_state": "operator_intervention"}),
            source="protection_manager",
        )
        with session_scope() as session:
            repo = MemoryRepository(session)
            if position.oco_gtt_id:
                trigger = repo.get_protective_trigger(str(position.oco_gtt_id))
                payload = dict(trigger["payload"]) if trigger is not None else {"ticker": ticker}
                payload["operator_intervention_at"] = now_iso
                payload["operator_detail"] = detail
                repo.upsert_protective_trigger(
                    protective_trigger_id=str(position.oco_gtt_id),
                    position_id=ticker,
                    ticker=ticker,
                    status="recreate_required",
                    payload=payload,
                    source="protection_manager",
                )
            repo.upsert_failure_incident(
                incident_id=f"protection:{ticker}",
                status="open",
                severity="critical",
                payload={"ticker": ticker, "detail": detail, "at": now_iso},
                source="protection_manager",
            )
        await self.alerts_tool.send_alert(
            f"⚠️ Operator intervention required for {ticker}: {detail}",
            level="warning",
        )

    def _replace_position(
        self,
        *,
        ticker: str,
        updater,
        source: str,
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            state = AccountState.model_validate(repo.get_account_state_payload())
            positions: list[PositionState] = []
            for item in state.positions:
                if item.ticker.upper() == ticker:
                    positions.append(updater(item))
                else:
                    positions.append(item.model_copy())
            next_state = state.model_copy(update={"positions": positions})
            repo.replace_account_state(next_state.model_dump(mode="json"), source=source)

    def _current_order_intent(
        self,
        repo: MemoryRepository,
        ticker: str,
    ) -> dict[str, Any] | None:
        intents = repo.list_order_intents_for_ticker(ticker)
        return next(
            (
                item
                for item in intents
                if str(item["status"]).strip().lower() not in {"failed", "cancelled", "expired"}
            ),
            None,
        )

    def _store_order_intent(
        self,
        *,
        order_intent_id: str,
        ticker: str,
        status: str,
        payload: dict[str, Any],
        intent: dict[str, Any],
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_order_intent(
                order_intent_id=order_intent_id,
                ticker=ticker,
                status=status,
                approval_id=intent.get("approval_id"),
                entry_intent_id=intent.get("entry_intent_id"),
                broker_order_id=intent.get("broker_order_id"),
                broker_tag=intent.get("broker_tag"),
                payload=payload,
                source="protection_manager",
            )

    def _open_incident(
        self,
        *,
        ticker: str,
        incident_id: str,
        severity: str,
        payload: dict[str, Any],
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_failure_incident(
                incident_id=incident_id,
                status="open",
                severity=severity,
                payload={"ticker": ticker, **payload},
                source="protection_manager",
            )

    def _trigger_row_status(self, gtt: GTTOrder) -> str:
        if gtt.status == "triggered":
            if gtt.exit_order_status == "complete":
                return "exit_filled"
            if gtt.exit_order_status and gtt.exit_order_status not in FAILED_EXIT_ORDER_STATUSES:
                return "exit_order_open"
            if gtt.exit_rejection_reason or gtt.exit_order_status in FAILED_EXIT_ORDER_STATUSES:
                return "rejected"
            return "triggered"
        return gtt.status

    def _trigger_payload(
        self,
        *,
        position: PositionState,
        gtt: GTTOrder,
        trigger: dict[str, Any] | None,
        intent: dict[str, Any] | None,
    ) -> dict[str, Any]:
        previous_payload = dict(trigger["payload"]) if trigger is not None else {}
        return {
            **previous_payload,
            "ticker": position.ticker.upper(),
            "order_intent_id": str(intent["order_intent_id"]) if intent is not None else None,
            "stop_price": gtt.stop_price,
            "target_price": gtt.target_price,
            "quantity": position.quantity,
            "broker_status": gtt.status,
            "triggered_leg": gtt.triggered_leg,
            "exit_order_id": gtt.exit_order_id,
            "exit_exchange_order_id": gtt.exit_exchange_order_id,
            "exit_order_status": gtt.exit_order_status,
            "exit_rejection_reason": gtt.exit_rejection_reason,
            "last_seen_at": _now().isoformat(),
        }
