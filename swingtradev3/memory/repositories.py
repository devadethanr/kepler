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
        row.state = "open"
        row.quantity = position.quantity
        row.entry_price = position.entry_price
        row.stop_price = position.stop_price
        row.target_price = position.target_price
        row.opened_at = position.opened_at
        row.payload = position.model_dump(mode="json")

    def get_pending_approvals_payload(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow).order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.ticker.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def get_execution_requested_approvals(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(ApprovalRow)
            .where(ApprovalRow.execution_requested.is_(True))
            .order_by(ApprovalRow.created_at_effective.asc(), ApprovalRow.ticker.asc())
        ).all()
        return [dict(row.payload) for row in rows]

    def replace_pending_approvals(
        self,
        payload: Iterable[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        existing = {
            str(row.ticker).upper(): row
            for row in self.session.scalars(select(ApprovalRow)).all()
        }
        normalized_payload: list[dict[str, Any]] = []
        seen_tickers: set[str] = set()

        for item in payload:
            approval = PendingApproval.model_validate(item)
            normalized = approval.model_dump(mode="json")
            if "execution_requested" in item:
                normalized["execution_requested"] = bool(item.get("execution_requested"))
            if "execution_request_id" in item:
                normalized["execution_request_id"] = item.get("execution_request_id")
            ticker_key = approval.ticker.upper()
            row = existing.get(ticker_key)
            if row is None:
                row = ApprovalRow(approval_id=f"approval:{ticker_key}", ticker=approval.ticker)
                existing[ticker_key] = row
                self.session.add(row)

            execution_requested = bool(normalized.get("execution_requested", False))
            approved = normalized.get("approved")
            row.ticker = approval.ticker
            row.status = "approved" if approved is True else "pending"
            row.approved = approved
            row.execution_requested = execution_requested
            row.execution_request_id = (
                str(normalized["execution_request_id"])
                if normalized.get("execution_request_id") is not None
                else None
            )
            row.created_at_effective = approval.created_at
            row.expires_at = approval.expires_at
            row.payload = normalized

            normalized_payload.append(normalized)
            seen_tickers.add(ticker_key)

        for ticker, row in existing.items():
            if ticker not in seen_tickers:
                self.session.delete(row)

        self.append_execution_event(
            event_type="approvals_replaced",
            entity_type="approvals",
            entity_id="pending",
            source=source,
            payload={"count": len(normalized_payload)},
        )
        return normalized_payload

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

    def get_order_intent(self, order_intent_id: str) -> dict[str, Any] | None:
        row = self.session.get(OrderIntentRow, order_intent_id)
        if row is None:
            return None
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
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
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def list_order_intents(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(OrderIntentRow).order_by(OrderIntentRow.updated_at.desc())
        ).all()
        return [
            {
                "order_intent_id": row.order_intent_id,
                "ticker": row.ticker,
                "status": row.status,
                "broker_tag": row.broker_tag,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def upsert_order_intent(
        self,
        *,
        order_intent_id: str,
        ticker: str,
        status: str,
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
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="order_intent_upserted",
            entity_type="order_intent",
            entity_id=order_intent_id,
            source=source,
            payload={"status": status, "ticker": ticker, "broker_tag": broker_tag},
        )
        return {
            "order_intent_id": row.order_intent_id,
            "ticker": row.ticker,
            "status": row.status,
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
        row.status = status
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="broker_order_upserted",
            entity_type="broker_order",
            entity_id=broker_order_id,
            source=source,
            payload={"status": status, "ticker": ticker, "broker_tag": broker_tag},
        )
        return {
            "broker_order_id": row.broker_order_id,
            "exchange_order_id": row.exchange_order_id,
            "ticker": row.ticker,
            "status": row.status,
            "broker_tag": row.broker_tag,
            "payload": dict(row.payload),
        }

    def upsert_broker_fill(
        self,
        *,
        fill_id: str,
        broker_order_id: str,
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
        row.ticker = ticker
        row.quantity = quantity
        row.fill_price = fill_price
        row.payload = dict(payload)

        self.append_execution_event(
            event_type="broker_fill_upserted",
            entity_type="broker_fill",
            entity_id=fill_id,
            source=source,
            payload={"broker_order_id": broker_order_id, "quantity": quantity, "ticker": ticker},
        )
        return {
            "fill_id": row.fill_id,
            "broker_order_id": row.broker_order_id,
            "ticker": row.ticker,
            "quantity": row.quantity,
            "fill_price": row.fill_price,
            "payload": dict(row.payload),
        }

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
