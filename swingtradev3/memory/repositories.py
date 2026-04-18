from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AccountState, PendingApproval, PositionState, TradeRecord

from .models import (
    AccountStateRow,
    ApprovalRow,
    AuthSessionRow,
    BrokerFillRow,
    BrokerOrderRow,
    EntryIntentRow,
    ExecutionEventRow,
    FailureIncidentRow,
    OrderIntentRow,
    OperatorControlRow,
    PositionRow,
    ProtectiveTriggerRow,
    ReconciliationRunRow,
    TradeRow,
)


PRIMARY_ACCOUNT_KEY = "primary"
KITE_SESSION_KEY = "kite"
VISIBLE_APPROVAL_STATUSES = {"pending", "approved", "queued", "rejected", "expired"}
ACTIVE_APPROVAL_ORDER_STATUSES = {"awaiting_approval", "approved", "queued"}


class StoredKiteSessionPayload(BaseModel):
    api_key: str
    access_token: str
    public_token: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    user_shortname: str | None = None
    email: str | None = None
    broker: str | None = None
    user_type: str | None = None
    login_time: str | None = None
    created_at: str | None = None
    raw_session: dict[str, Any] = Field(default_factory=dict)


def _approval_status(
    *,
    approved: bool | None,
    execution_requested: bool,
    order_intent_status: str | None = None,
    explicit_status: str | None = None,
) -> str:
    if explicit_status:
        normalized = explicit_status.strip().lower()
        if normalized:
            return normalized
    if order_intent_status:
        normalized = order_intent_status.strip().lower()
        if normalized and normalized not in ACTIVE_APPROVAL_ORDER_STATUSES:
            return normalized
    if approved is False:
        return "rejected"
    if approved is True and execution_requested:
        return "queued"
    if approved is True:
        return "approved"
    return "pending"


def _entry_intent_status(
    *,
    approved: bool | None,
    execution_requested: bool,
    order_intent_status: str | None = None,
) -> str:
    if order_intent_status:
        normalized = order_intent_status.strip().lower()
        if normalized and normalized not in {"awaiting_approval"}:
            return normalized
    if approved is False:
        return "cancelled"
    if approved is True and execution_requested:
        return "queued"
    if approved is True:
        return "approved"
    return "awaiting_approval"


class MemoryRepository:
    def __init__(self, session: Session):
        self.session = session

    def append_execution_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        source: str,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            ExecutionEventRow(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                source=source,
                payload=payload,
            )
        )

    def execution_event_exists(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        source: str | None = None,
    ) -> bool:
        query = select(ExecutionEventRow.event_id).where(
            ExecutionEventRow.event_type == event_type,
            ExecutionEventRow.entity_type == entity_type,
            ExecutionEventRow.entity_id == entity_id,
        )
        if source is not None:
            query = query.where(ExecutionEventRow.source == source)
        self.session.flush()
        return self.session.scalar(query.limit(1)) is not None

    def account_state_exists(self) -> bool:
        return self.session.get(AccountStateRow, PRIMARY_ACCOUNT_KEY) is not None

    def approvals_exist(self) -> bool:
        return self.session.scalar(select(ApprovalRow.approval_id).limit(1)) is not None

    def trades_exist(self) -> bool:
        return self.session.scalar(select(TradeRow.trade_id).limit(1)) is not None

    def auth_session_exists(self) -> bool:
        return self.session.get(AuthSessionRow, KITE_SESSION_KEY) is not None

    def get_account_state_payload(self) -> dict[str, Any]:
        row = self.session.get(AccountStateRow, PRIMARY_ACCOUNT_KEY)
        if row is None:
            return AccountState().model_dump(mode="json")
        return dict(row.payload)

    def replace_account_state(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        state = AccountState.model_validate(payload or {})
        normalized = state.model_dump(mode="json")

        row = self.session.get(AccountStateRow, PRIMARY_ACCOUNT_KEY)
        if row is None:
            row = AccountStateRow(account_key=PRIMARY_ACCOUNT_KEY)
            self.session.add(row)

        row.cash_inr = state.cash_inr
        row.realized_pnl = state.realized_pnl
        row.unrealized_pnl = state.unrealized_pnl
        row.drawdown_pct = state.drawdown_pct
        row.weekly_loss_pct = state.weekly_loss_pct
        row.consecutive_losses = state.consecutive_losses
        row.payload = normalized

        existing_positions = {
            str(position.ticker).upper(): position
            for position in self.session.scalars(select(PositionRow)).all()
        }
        seen_tickers: set[str] = set()

        for position in state.positions:
            self._upsert_position(position, existing_positions)
            seen_tickers.add(position.ticker.upper())

        for ticker, row_position in existing_positions.items():
            if ticker not in seen_tickers:
                self.session.delete(row_position)

        self.append_execution_event(
            event_type="account_state_replaced",
            entity_type="account_state",
            entity_id=PRIMARY_ACCOUNT_KEY,
            source=source,
            payload={
                "positions": len(state.positions),
                "cash_inr": state.cash_inr,
            },
        )
        return normalized

    def _upsert_position(
        self,
        position: PositionState,
        existing_positions: dict[str, PositionRow],
    ) -> None:
        ticker_key = position.ticker.upper()
        row = existing_positions.get(ticker_key)
        if row is None:
            row = PositionRow(position_id=ticker_key, ticker=position.ticker)
            existing_positions[ticker_key] = row
            self.session.add(row)

        row.ticker = position.ticker
        row.state = position.lifecycle_state
        row.quantity = position.quantity
        row.entry_price = position.entry_price
        row.stop_price = position.stop_price
        row.target_price = position.target_price
        row.opened_at = position.opened_at
        row.payload = position.model_dump(mode="json")

    def get_pending_approvals_payload(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(ApprovalRow.status.in_(sorted(VISIBLE_APPROVAL_STATUSES)))
            .order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.approval_id.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def get_execution_requested_approvals(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(
                ApprovalRow.execution_requested.is_(True),
                ApprovalRow.status.in_(("approved", "queued")),
            )
            .order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.approval_id.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        row = self.session.get(ApprovalRow, approval_id)
        if row is None:
            return None
        return dict(row.payload)

    def replace_pending_approvals(
        self,
        payload: Iterable[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        existing = {
            str(row.approval_id): row
            for row in self.session.scalars(select(ApprovalRow)).all()
        }
        normalized_payload: list[dict[str, Any]] = []
        seen_approval_ids: set[str] = set()

        for item in payload:
            incoming = dict(item)
            approval = PendingApproval.model_validate(item)
            normalized = approval.model_dump(mode="json")
            approval_id = str(normalized["approval_id"])
            entry_intent_id = str(normalized["entry_intent_id"])
            order_intent_id = str(normalized["order_intent_id"])
            row = existing.get(approval_id)
            if row is None:
                row = ApprovalRow(approval_id=approval_id, ticker=approval.ticker)
                existing[approval_id] = row
                self.session.add(row)

            approved_provided = "approved" in incoming
            execution_requested_provided = "execution_requested" in incoming
            request_id_provided = "execution_request_id" in incoming
            broker_tag_provided = "broker_tag" in incoming
            existing_payload = dict(row.payload or {})

            approved = (
                normalized.get("approved") if approved_provided else row.approved
            )
            execution_requested = (
                bool(normalized.get("execution_requested", False))
                if execution_requested_provided
                else bool(row.execution_requested)
            )
            execution_request_id = (
                str(normalized["execution_request_id"])
                if request_id_provided and normalized.get("execution_request_id") is not None
                else None
                if request_id_provided
                else row.execution_request_id
            )
            broker_tag = (
                str(normalized.get("broker_tag"))
                if broker_tag_provided and normalized.get("broker_tag") not in (None, "")
                else None
                if broker_tag_provided
                else str(existing_payload.get("broker_tag"))
                if existing_payload.get("broker_tag") not in (None, "")
                else None
            )

            normalized["approved"] = approved
            normalized["execution_requested"] = execution_requested
            normalized["execution_request_id"] = execution_request_id
            normalized["approval_id"] = approval_id
            normalized["entry_intent_id"] = entry_intent_id
            normalized["order_intent_id"] = order_intent_id
            if broker_tag is not None:
                normalized["broker_tag"] = broker_tag

            order_intent_status = "awaiting_approval"
            if approved is True and execution_requested:
                order_intent_status = "queued"
            elif approved is True:
                order_intent_status = "approved"
            elif approved is False:
                order_intent_status = "cancelled"

            row.ticker = approval.ticker
            row.entry_intent_id = entry_intent_id
            row.order_intent_id = order_intent_id
            row.status = _approval_status(
                approved=approved,
                execution_requested=execution_requested,
                order_intent_status=order_intent_status,
                explicit_status=normalized.get("status"),
            )
            row.approved = approved
            row.execution_requested = execution_requested
            row.execution_request_id = execution_request_id
            row.created_at_effective = approval.created_at
            row.expires_at = approval.expires_at
            normalized["status"] = row.status
            row.payload = normalized

            self.upsert_entry_intent(
                entry_intent_id=entry_intent_id,
                ticker=approval.ticker,
                status=_entry_intent_status(
                    approved=approved,
                    execution_requested=execution_requested,
                    order_intent_status=order_intent_status,
                ),
                approval_id=approval_id,
                order_intent_id=order_intent_id,
                payload=normalized,
                source=source,
            )
            self.upsert_order_intent(
                order_intent_id=order_intent_id,
                ticker=approval.ticker,
                status=order_intent_status,
                approval_id=approval_id,
                entry_intent_id=entry_intent_id,
                broker_order_id=(
                    str(normalized.get("broker_order_id"))
                    if normalized.get("broker_order_id") not in (None, "")
                    else None
                ),
                broker_tag=broker_tag,
                payload=normalized,
                source=source,
            )

            normalized_payload.append(normalized)
            seen_approval_ids.add(approval_id)

        for approval_id, row in existing.items():
            if approval_id in seen_approval_ids:
                continue
            order_intent = (
                self.get_order_intent(str(row.order_intent_id))
                if row.order_intent_id
                else None
            )
            next_status = _approval_status(
                approved=row.approved,
                execution_requested=False,
                order_intent_status=(
                    str(order_intent["status"])
                    if order_intent is not None
                    else None
                ),
            )
            row.status = next_status
            row.execution_requested = False
            row.execution_request_id = None
            next_payload = dict(row.payload)
            next_payload["status"] = next_status
            next_payload["execution_requested"] = False
            next_payload["execution_request_id"] = None
            row.payload = next_payload

        self.append_execution_event(
            event_type="approvals_replaced",
            entity_type="approvals",
            entity_id="pending",
            source=source,
            payload={"count": len(normalized_payload)},
        )
        return self.get_pending_approvals_payload()

    def get_trades_payload(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(TradeRow).order_by(TradeRow.closed_at_effective.desc(), TradeRow.trade_id.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def replace_trades(
        self,
        payload: Iterable[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        existing_trade_ids = set(self.session.scalars(select(TradeRow.trade_id)).all())
        seen_trade_ids: set[str] = set()
        normalized_payload: list[dict[str, Any]] = []
        for item in payload:
            trade = TradeRecord.model_validate(item)
            normalized = trade.model_dump(mode="json")
            row = self.session.get(TradeRow, trade.trade_id)
            if row is None:
                row = TradeRow(trade_id=trade.trade_id)
                self.session.add(row)
            row.ticker = trade.ticker
            row.quantity = trade.quantity
            row.entry_price = trade.entry_price
            row.exit_price = trade.exit_price
            row.opened_at_effective = trade.opened_at
            row.closed_at_effective = trade.closed_at
            row.pnl_abs = trade.pnl_abs
            row.pnl_pct = trade.pnl_pct
            row.exit_reason = trade.exit_reason
            row.payload = normalized
            normalized_payload.append(normalized)
            seen_trade_ids.add(trade.trade_id)

        for trade_id in existing_trade_ids - seen_trade_ids:
            row = self.session.get(TradeRow, trade_id)
            if row is not None:
                self.session.delete(row)

        self.append_execution_event(
            event_type="trades_replaced",
            entity_type="trades",
            entity_id="closed",
            source=source,
            payload={"count": len(normalized_payload)},
        )
        return normalized_payload

    def get_auth_session_payload(self) -> dict[str, Any]:
        row = self.session.get(AuthSessionRow, KITE_SESSION_KEY)
        return {} if row is None else dict(row.payload)

    def replace_auth_session(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        session_payload = StoredKiteSessionPayload.model_validate(payload)
        normalized = session_payload.model_dump(mode="json")

        row = self.session.get(AuthSessionRow, KITE_SESSION_KEY)
        if row is None:
            row = AuthSessionRow(session_key=KITE_SESSION_KEY, provider="kite")
            self.session.add(row)

        row.provider = "kite"
        row.user_id = session_payload.user_id
        row.access_token = session_payload.access_token
        row.public_token = session_payload.public_token
        row.payload = normalized

        self.append_execution_event(
            event_type="auth_session_replaced",
            entity_type="auth_session",
            entity_id=KITE_SESSION_KEY,
            source=source,
            payload={"provider": "kite", "user_id": session_payload.user_id},
        )
        return normalized

    def get_operator_control(self, control_key: str) -> dict[str, Any] | None:
        row = self.session.get(OperatorControlRow, control_key)
        if row is None:
            return None
        return {
            "control_key": row.control_key,
            "value": dict(row.value),
            "payload": dict(row.payload),
        }

    def get_entry_intent(self, entry_intent_id: str) -> dict[str, Any] | None:
        row = self.session.get(EntryIntentRow, entry_intent_id)
        if row is None:
            return None
        return {
            "entry_intent_id": row.intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "order_intent_id": row.order_intent_id,
            "payload": dict(row.payload),
        }

    def list_entry_intents(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(EntryIntentRow).order_by(EntryIntentRow.updated_at.desc())
        ).all()
        return [
            {
                "entry_intent_id": row.intent_id,
                "ticker": row.ticker,
                "status": row.status,
                "approval_id": row.approval_id,
                "order_intent_id": row.order_intent_id,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def upsert_entry_intent(
        self,
        *,
        entry_intent_id: str,
        ticker: str,
        status: str,
        approval_id: str | None,
        order_intent_id: str | None,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(EntryIntentRow, entry_intent_id)
        if row is None:
            row = EntryIntentRow(intent_id=entry_intent_id)
            self.session.add(row)

        row.ticker = ticker
        row.status = status
        row.approval_id = approval_id
        row.order_intent_id = order_intent_id
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="entry_intent_upserted",
            entity_type="entry_intent",
            entity_id=entry_intent_id,
            source=source,
            payload={
                "status": status,
                "ticker": ticker,
                "approval_id": approval_id,
                "order_intent_id": order_intent_id,
            },
        )
        return {
            "entry_intent_id": row.intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "order_intent_id": row.order_intent_id,
            "payload": dict(row.payload),
        }

    def get_order_intent(self, order_intent_id: str) -> dict[str, Any] | None:
        row = self.session.get(OrderIntentRow, order_intent_id)
        if row is None:
            return None
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "entry_intent_id": row.entry_intent_id,
            "broker_order_id": row.broker_order_id,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def get_order_intent_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        row = self.session.scalar(
            select(OrderIntentRow)
            .where(OrderIntentRow.ticker == ticker)
            .order_by(OrderIntentRow.updated_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "entry_intent_id": row.entry_intent_id,
            "broker_order_id": row.broker_order_id,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def list_order_intents_for_ticker(self, ticker: str) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(OrderIntentRow)
            .where(OrderIntentRow.ticker == ticker)
            .order_by(OrderIntentRow.updated_at.desc(), OrderIntentRow.created_at.desc())
        ).all()
        return [
            {
                "order_intent_id": row.order_intent_id,
                "ticker": row.ticker,
                "status": row.status,
                "approval_id": row.approval_id,
                "entry_intent_id": row.entry_intent_id,
                "broker_order_id": row.broker_order_id,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def list_order_intents(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(OrderIntentRow).order_by(OrderIntentRow.updated_at.desc())
        ).all()
        return [
            {
                "order_intent_id": row.order_intent_id,
                "ticker": row.ticker,
                "status": row.status,
                "approval_id": row.approval_id,
                "entry_intent_id": row.entry_intent_id,
                "broker_order_id": row.broker_order_id,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def list_order_intents_by_status(self, statuses: Iterable[str]) -> list[dict[str, Any]]:
        normalized = [str(status).strip() for status in statuses if str(status).strip()]
        if not normalized:
            return []
        rows = self.session.scalars(
            select(OrderIntentRow)
            .where(OrderIntentRow.status.in_(normalized))
            .order_by(OrderIntentRow.updated_at.asc(), OrderIntentRow.created_at.asc())
        ).all()
        return [
            {
                "order_intent_id": row.order_intent_id,
                "ticker": row.ticker,
                "status": row.status,
                "approval_id": row.approval_id,
                "entry_intent_id": row.entry_intent_id,
                "broker_order_id": row.broker_order_id,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def get_order_intent_by_broker_tag(self, broker_tag: str) -> dict[str, Any] | None:
        normalized = broker_tag.strip()
        if not normalized:
            return None
        row = self.session.scalar(
            select(OrderIntentRow)
            .where(OrderIntentRow.broker_tag == normalized)
            .order_by(OrderIntentRow.updated_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "entry_intent_id": row.entry_intent_id,
            "broker_order_id": row.broker_order_id,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def upsert_order_intent(
        self,
        *,
        order_intent_id: str,
        ticker: str,
        status: str,
        approval_id: str | None,
        entry_intent_id: str | None,
        broker_order_id: str | None,
        broker_tag: str | None,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(OrderIntentRow, order_intent_id)
        if row is None:
            row = OrderIntentRow(order_intent_id=order_intent_id)
            self.session.add(row)

        row.ticker = ticker
        row.status = status
        row.approval_id = approval_id
        row.entry_intent_id = entry_intent_id
        row.broker_order_id = broker_order_id
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="order_intent_upserted",
            entity_type="order_intent",
            entity_id=order_intent_id,
            source=source,
            payload={
                "status": status,
                "ticker": ticker,
                "approval_id": approval_id,
                "entry_intent_id": entry_intent_id,
                "broker_order_id": broker_order_id,
                "broker_tag": broker_tag,
            },
        )
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
            "approval_id": row.approval_id,
            "entry_intent_id": row.entry_intent_id,
            "broker_order_id": row.broker_order_id,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def get_broker_order(self, broker_order_id: str) -> dict[str, Any] | None:
        row = self.session.get(BrokerOrderRow, broker_order_id)
        if row is None:
            return None
        return {
            "broker_order_id": row.broker_order_id,
            "exchange_order_id": row.exchange_order_id,
            "ticker": row.ticker,
            "order_intent_id": row.order_intent_id,
            "status": row.status,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def list_broker_orders(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(select(BrokerOrderRow).order_by(BrokerOrderRow.updated_at.desc())).all()
        return [
            {
                "broker_order_id": row.broker_order_id,
                "exchange_order_id": row.exchange_order_id,
                "ticker": row.ticker,
                "order_intent_id": row.order_intent_id,
                "status": row.status,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def list_broker_orders_by_tag(self, broker_tag: str) -> list[dict[str, Any]]:
        normalized = broker_tag.strip()
        if not normalized:
            return []
        rows = self.session.scalars(
            select(BrokerOrderRow)
            .where(BrokerOrderRow.broker_tag == normalized)
            .order_by(BrokerOrderRow.updated_at.desc(), BrokerOrderRow.created_at.desc())
        ).all()
        return [
            {
                "broker_order_id": row.broker_order_id,
                "exchange_order_id": row.exchange_order_id,
                "ticker": row.ticker,
                "order_intent_id": row.order_intent_id,
                "status": row.status,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def upsert_broker_order(
        self,
        *,
        broker_order_id: str,
        exchange_order_id: str | None,
        ticker: str,
        order_intent_id: str | None,
        status: str,
        broker_tag: str | None,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(BrokerOrderRow, broker_order_id)
        if row is None:
            row = BrokerOrderRow(broker_order_id=broker_order_id)
            self.session.add(row)

        row.exchange_order_id = exchange_order_id
        row.ticker = ticker
        row.order_intent_id = order_intent_id
        row.status = status
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="broker_order_upserted",
            entity_type="broker_order",
            entity_id=broker_order_id,
            source=source,
            payload={
                "status": status,
                "ticker": ticker,
                "order_intent_id": order_intent_id,
                "broker_tag": broker_tag,
            },
        )
        return {
            "broker_order_id": row.broker_order_id,
            "exchange_order_id": row.exchange_order_id,
            "ticker": row.ticker,
            "order_intent_id": row.order_intent_id,
            "status": row.status,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def upsert_broker_fill(
        self,
        *,
        fill_id: str,
        broker_order_id: str,
        order_intent_id: str | None,
        ticker: str,
        quantity: int,
        fill_price: float,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(BrokerFillRow, fill_id)
        if row is None:
            row = BrokerFillRow(fill_id=fill_id)
            self.session.add(row)

        row.broker_order_id = broker_order_id
        row.order_intent_id = order_intent_id
        row.ticker = ticker
        row.quantity = quantity
        row.fill_price = fill_price
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="broker_fill_upserted",
            entity_type="broker_fill",
            entity_id=fill_id,
            source=source,
            payload={
                "broker_order_id": broker_order_id,
                "order_intent_id": order_intent_id,
                "quantity": quantity,
                "ticker": ticker,
            },
        )
        return {
            "fill_id": row.fill_id,
            "broker_order_id": row.broker_order_id,
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "quantity": row.quantity,
            "fill_price": row.fill_price,
            "payload": dict(row.payload),
        }

    def list_broker_fills(self, broker_order_id: str | None = None) -> list[dict[str, Any]]:
        query = select(BrokerFillRow).order_by(BrokerFillRow.created_at.asc(), BrokerFillRow.fill_id.asc())
        if broker_order_id is not None:
            query = query.where(BrokerFillRow.broker_order_id == broker_order_id)
        rows = self.session.scalars(query).all()
        return [
            {
                "fill_id": row.fill_id,
                "broker_order_id": row.broker_order_id,
                "order_intent_id": row.order_intent_id,
                "ticker": row.ticker,
                "quantity": row.quantity,
                "fill_price": row.fill_price,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def list_protective_triggers(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ProtectiveTriggerRow).order_by(ProtectiveTriggerRow.updated_at.desc())
        ).all()
        return [
            {
                "protective_trigger_id": row.protective_trigger_id,
                "position_id": row.position_id,
                "ticker": row.ticker,
                "status": row.status,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def get_protective_trigger(self, protective_trigger_id: str) -> dict[str, Any] | None:
        row = self.session.get(ProtectiveTriggerRow, protective_trigger_id)
        if row is None:
            return None
        return {
            "protective_trigger_id": row.protective_trigger_id,
            "position_id": row.position_id,
            "ticker": row.ticker,
            "status": row.status,
            "payload": dict(row.payload),
        }

    def get_protective_trigger_for_ticker(self, ticker: str) -> dict[str, Any] | None:
        normalized = ticker.strip().upper()
        if not normalized:
            return None
        row = self.session.scalar(
            select(ProtectiveTriggerRow)
            .where(ProtectiveTriggerRow.ticker == normalized)
            .order_by(ProtectiveTriggerRow.updated_at.desc(), ProtectiveTriggerRow.created_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        return {
            "protective_trigger_id": row.protective_trigger_id,
            "position_id": row.position_id,
            "ticker": row.ticker,
            "status": row.status,
            "payload": dict(row.payload),
        }

    def upsert_protective_trigger(
        self,
        *,
        protective_trigger_id: str,
        position_id: str,
        ticker: str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(ProtectiveTriggerRow, protective_trigger_id)
        if row is None:
            row = ProtectiveTriggerRow(protective_trigger_id=protective_trigger_id)
            self.session.add(row)

        row.position_id = position_id
        row.ticker = ticker
        row.status = status
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="protective_trigger_upserted",
            entity_type="protective_trigger",
            entity_id=protective_trigger_id,
            source=source,
            payload={"ticker": ticker, "status": status},
        )
        return {
            "protective_trigger_id": row.protective_trigger_id,
            "position_id": row.position_id,
            "ticker": row.ticker,
            "status": row.status,
            "payload": dict(row.payload),
        }

    def upsert_trade(
        self,
        *,
        trade_id: str,
        ticker: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        opened_at: Any,
        closed_at: Any,
        pnl_abs: float,
        pnl_pct: float,
        exit_reason: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        trade = TradeRecord.model_validate(
            {
                "trade_id": trade_id,
                "ticker": ticker,
                "quantity": quantity,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "opened_at": opened_at,
                "closed_at": closed_at,
                "exit_reason": exit_reason,
                "pnl_abs": pnl_abs,
                "pnl_pct": pnl_pct,
                **dict(payload),
            }
        )
        normalized = trade.model_dump(mode="json")
        row = self.session.get(TradeRow, trade_id)
        if row is None:
            row = TradeRow(trade_id=trade_id)
            self.session.add(row)
        row.ticker = trade.ticker
        row.quantity = trade.quantity
        row.entry_price = trade.entry_price
        row.exit_price = trade.exit_price
        row.opened_at_effective = trade.opened_at
        row.closed_at_effective = trade.closed_at
        row.pnl_abs = trade.pnl_abs
        row.pnl_pct = trade.pnl_pct
        row.exit_reason = trade.exit_reason
        row.payload = normalized
        self.append_execution_event(
            event_type="trade_upserted",
            entity_type="trade",
            entity_id=trade_id,
            source=source,
            payload={
                "ticker": trade.ticker,
                "exit_reason": trade.exit_reason,
                "pnl_pct": trade.pnl_pct,
            },
        )
        return normalized

    def upsert_reconciliation_run(
        self,
        *,
        reconciliation_run_id: str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(ReconciliationRunRow, reconciliation_run_id)
        if row is None:
            row = ReconciliationRunRow(reconciliation_run_id=reconciliation_run_id)
            self.session.add(row)

        row.status = status
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="reconciliation_run_upserted",
            entity_type="reconciliation_run",
            entity_id=reconciliation_run_id,
            source=source,
            payload={"status": status},
        )
        return {
            "reconciliation_run_id": row.reconciliation_run_id,
            "status": row.status,
            "payload": dict(row.payload),
        }

    def upsert_failure_incident(
        self,
        *,
        incident_id: str,
        status: str,
        severity: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(FailureIncidentRow, incident_id)
        if row is None:
            row = FailureIncidentRow(incident_id=incident_id)
            self.session.add(row)

        row.status = status
        row.severity = severity
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="failure_incident_upserted",
            entity_type="failure_incident",
            entity_id=incident_id,
            source=source,
            payload={"status": status, "severity": severity},
        )
        return {
            "incident_id": row.incident_id,
            "status": row.status,
            "severity": row.severity,
            "payload": dict(row.payload),
        }

    def list_operator_controls(self, *, prefix: str | None = None) -> list[dict[str, Any]]:
        query = select(OperatorControlRow).order_by(OperatorControlRow.control_key.asc())
        if prefix:
            query = query.where(OperatorControlRow.control_key.like(f"{prefix}%"))
        rows = self.session.scalars(query).all()
        return [
            {
                "control_key": row.control_key,
                "value": dict(row.value),
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def upsert_operator_control(
        self,
        *,
        control_key: str,
        value: dict[str, Any],
        payload: dict[str, Any] | None = None,
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(OperatorControlRow, control_key)
        if row is None:
            row = OperatorControlRow(control_key=control_key)
            self.session.add(row)

        row.value = dict(value)
        row.payload = dict(payload or row.payload or {})

        self.append_execution_event(
            event_type="operator_control_updated",
            entity_type="operator_control",
            entity_id=control_key,
            source=source,
            payload={"value": row.value, "payload": row.payload},
        )
        return {
            "control_key": row.control_key,
            "value": dict(row.value),
            "payload": dict(row.payload),
        }
