from __future__ import annotations

from datetime import datetime
from typing import Any

from data.market_regime import MarketRegimeDetector
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import AccountState, PositionState
from paths import CONTEXT_DIR
from regime_adapter import RegimeAdaptiveConfig
from storage import read_json, write_json
from tools.execution.alerts import AlertsTool
from tools.execution.gtt_manager import GTTManager
from tools.execution.order_execution import OrderExecutionTool
from tools.execution.risk_check import RiskCheckTool

from .protection_manager import ProtectionManager


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


def _now() -> datetime:
    return datetime.now()


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

    def pending_execution_requests(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            return repo.list_order_intents_by_status(QUEUED_ORDER_INTENT_STATUSES)

    def active_execution_requests(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            repo = MemoryRepository(session)
            return repo.list_order_intents_by_status(ACTIVE_ORDER_INTENT_STATUSES)

    async def submit_queued_order_intents(self) -> int:
        submitted = 0
        for intent in self.pending_execution_requests():
            result = await self.submit_order_intent(str(intent["order_intent_id"]))
            if result != "ignored":
                submitted += 1
        return submitted

    async def reconcile_active_order_intents(self) -> int:
        advanced = 0
        for intent in self.active_execution_requests():
            result = await self.reconcile_order_intent(str(intent["order_intent_id"]))
            if result != "noop":
                advanced += 1
        return advanced

    async def submit_order_intent(self, order_intent_id: str) -> str:
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
        if expires_at_raw and datetime.fromisoformat(str(expires_at_raw)) <= _now():
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
        risk = self.risk_tool.check_risk(state, score, entry_price, stop_price, target_price)
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

        if status == "filled":
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
        return "failed"

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
        if status not in {"submitted", "entry_open", "entry_partially_filled", "entry_filled"}:
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
