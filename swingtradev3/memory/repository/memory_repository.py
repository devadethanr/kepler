"""MemoryRepository — Facade aggregating all domain sub-repositories.

This is the sole public API.  All existing call sites that import
``from memory.repository import MemoryRepository`` continue to work
because ``../repositories.py`` re-exports from this module.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from .. import models as models_module

from . import (
    AccountRepository,
    ApprovalRepository,
    BrokerRepository,
    CognitionRepository,
    EntryIntentRepository,
    EventRepository,
    FailureRepository,
    NewsRepository,
    OperatorRepository,
    OrderIntentRepository,
    PolicyRepository,
    PositionRepository,
    ReconciliationRepository,
    TradeRepository,
)


class MemoryRepository:
    """Unified facade over all domain sub-repositories.

    Every method delegates to the appropriate sub-repo, keeping this
    class thin and each domain module independently testable.
    """

    # ── construction ────────────────────────────────────────────────

    def __init__(self, session: Session) -> None:
        self._session = session
        self._account: AccountRepository | None = None
        self._approval: ApprovalRepository | None = None
        self._broker: BrokerRepository | None = None
        self._cognition: CognitionRepository | None = None
        self._entry_intent: EntryIntentRepository | None = None
        self._event: EventRepository | None = None
        self._failure: FailureRepository | None = None
        self._news: NewsRepository | None = None
        self._operator: OperatorRepository | None = None
        self._order_intent: OrderIntentRepository | None = None
        self._policy: PolicyRepository | None = None
        self._position: PositionRepository | None = None
        self._reconciliation: ReconciliationRepository | None = None
        self._trade: TradeRepository | None = None

    @property
    def account(self) -> AccountRepository:
        if self._account is None:
            self._account = AccountRepository(self._session)
        return self._account

    @property
    def approvals(self) -> ApprovalRepository:
        if self._approval is None:
            self._approval = ApprovalRepository(self._session)
        return self._approval

    @property
    def broker(self) -> BrokerRepository:
        if self._broker is None:
            self._broker = BrokerRepository(self._session)
        return self._broker

    @property
    def cognition(self) -> CognitionRepository:
        if self._cognition is None:
            self._cognition = CognitionRepository(self._session)
        return self._cognition

    @property
    def entry_intents(self) -> EntryIntentRepository:
        if self._entry_intent is None:
            self._entry_intent = EntryIntentRepository(self._session)
        return self._entry_intent

    @property
    def events(self) -> EventRepository:
        if self._event is None:
            self._event = EventRepository(self._session)
        return self._event

    @property
    def failures(self) -> FailureRepository:
        if self._failure is None:
            self._failure = FailureRepository(self._session)
        return self._failure

    @property
    def news(self) -> NewsRepository:
        if self._news is None:
            self._news = NewsRepository(self._session)
        return self._news

    @property
    def operator(self) -> OperatorRepository:
        if self._operator is None:
            self._operator = OperatorRepository(self._session)
        return self._operator

    @property
    def order_intents(self) -> OrderIntentRepository:
        if self._order_intent is None:
            self._order_intent = OrderIntentRepository(self._session)
        return self._order_intent

    @property
    def policy(self) -> PolicyRepository:
        if self._policy is None:
            self._policy = PolicyRepository(self._session)
        return self._policy

    @property
    def positions(self) -> PositionRepository:
        if self._position is None:
            self._position = PositionRepository(self._session)
        return self._position

    @property
    def reconciliation(self) -> ReconciliationRepository:
        if self._reconciliation is None:
            self._reconciliation = ReconciliationRepository(self._session)
        return self._reconciliation

    @property
    def trades(self) -> TradeRepository:
        if self._trade is None:
            self._trade = TradeRepository(self._session)
        return self._trade

    # ── delegate methods (backwards-compatible API) ─────────────────

    def _sync_account_state_position_payload(
        self,
        *,
        position_id: str,
        updater,
    ) -> None:
        self.account._sync_account_state_position_payload(
            position_id=position_id, updater=updater
        )

    # ── events ──────────────────────────────────────────────────────

    def append_execution_event(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        source: str,
        payload: dict[str, Any],
    ) -> None:
        self.events.append_execution_event(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
            payload=payload,
        )

    def execution_event_exists(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str,
        source: str | None = None,
    ) -> bool:
        return self.events.execution_event_exists(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            source=source,
        )

    def list_execution_events(
        self,
        *,
        limit: int = 100,
        after_id: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.events.list_execution_events(
            limit=limit, after_id=after_id, event_type=event_type
        )

    def get_latest_execution_event_id(self) -> int | None:
        return self.events.get_latest_execution_event_id()

    # ── cognition audit ────────────────────────────────────────────

    def upsert_cognition_run(
        self,
        *,
        run_id: str,
        phase: str,
        status: str,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        payload: dict[str, Any] | None = None,
        source: str,
    ) -> dict[str, Any]:
        return self.cognition.upsert_cognition_run(
            run_id=run_id,
            phase=phase,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            payload=payload,
            source=source,
        )

    def get_cognition_run(self, run_id: str) -> dict[str, Any] | None:
        return self.cognition.get_cognition_run(run_id)

    def list_cognition_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return self.cognition.list_cognition_runs(limit=limit)

    def upsert_cognition_report(
        self,
        *,
        report_id: str,
        run_id: str,
        ticker: str | None,
        agent_name: str,
        schema_version: str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.cognition.upsert_cognition_report(
            report_id=report_id,
            run_id=run_id,
            ticker=ticker,
            agent_name=agent_name,
            schema_version=schema_version,
            status=status,
            payload=payload,
            source=source,
        )

    def list_cognition_reports(
        self,
        *,
        run_id: str | None = None,
        ticker: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        return self.cognition.list_cognition_reports(
            run_id=run_id,
            ticker=ticker,
            limit=limit,
        )

    def upsert_session_execution_plan(
        self,
        *,
        plan_id: str,
        trading_date: date | str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.cognition.upsert_session_execution_plan(
            plan_id=plan_id,
            trading_date=trading_date,
            status=status,
            payload=payload,
            source=source,
        )

    def latest_session_execution_plan(
        self,
        *,
        trading_date: date | str | None = None,
    ) -> dict[str, Any] | None:
        return self.cognition.latest_session_execution_plan(trading_date=trading_date)

    def list_session_execution_plans(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.cognition.list_session_execution_plans(limit=limit)

    # ── news ────────────────────────────────────────────────────────

    def upsert_news_items(self, items: list[dict[str, Any]], *, source: str) -> None:
        self.news.upsert_news_items(items, source=source)

    def upsert_news_provider_health(self, health: dict[str, dict[str, Any]]) -> None:
        self.news.upsert_news_provider_health(health)

    def list_news_items(
        self,
        *,
        limit: int = 100,
        ticker: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.news.list_news_items(limit=limit, ticker=ticker)

    def list_news_provider_health(self) -> dict[str, dict[str, Any]]:
        return self.news.list_news_provider_health()

    # ── account state ───────────────────────────────────────────────

    def account_state_exists(self) -> bool:
        return self.account.account_state_exists()

    def get_account_state_payload(self) -> dict[str, Any]:
        return self.account.get_account_state_payload()

    def replace_account_state(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        return self.account.replace_account_state(payload, source=source)

    # ── approvals ───────────────────────────────────────────────────

    def approvals_exist(self) -> bool:
        return self.approvals.approvals_exist()

    def get_pending_approvals_payload(self) -> list[dict[str, Any]]:
        return self.approvals.get_pending_approvals_payload()

    def get_execution_requested_approvals(self) -> list[dict[str, Any]]:
        return self.approvals.get_execution_requested_approvals()

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        return self.approvals.get_approval(approval_id)

    def update_approval_payload(
        self,
        approval_id: str,
        payload: dict[str, Any],
        *,
        source: str,
    ) -> dict[str, Any] | None:
        return self.approvals.update_approval_payload(approval_id, payload, source=source)

    def replace_pending_approvals(
        self,
        payload: list[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        return self.approvals.replace_pending_approvals(payload, source=source)

    # ── entries ─────────────────────────────────────────────────────

    def get_entry_intent(self, entry_intent_id: str) -> dict[str, Any] | None:
        return self.entry_intents.get_entry_intent(entry_intent_id)

    def list_entry_intents(self) -> list[dict[str, Any]]:
        return self.entry_intents.list_entry_intents()

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
        return self.entry_intents.upsert_entry_intent(
            entry_intent_id=entry_intent_id,
            ticker=ticker,
            status=status,
            approval_id=approval_id,
            order_intent_id=order_intent_id,
            payload=payload,
            source=source,
        )

    # ── order intents ───────────────────────────────────────────────

    def get_order_intent(self, order_intent_id: str) -> dict[str, Any] | None:
        return self.order_intents.get_order_intent(order_intent_id)

    def get_order_intent_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        return self.order_intents.get_order_intent_by_ticker(ticker)

    def list_order_intents_for_ticker(self, ticker: str) -> list[dict[str, Any]]:
        return self.order_intents.list_order_intents_for_ticker(ticker)

    def list_order_intents(self) -> list[dict[str, Any]]:
        return self.order_intents.list_order_intents()

    def list_order_intents_by_status(self, statuses: set[str]) -> list[dict[str, Any]]:
        return self.order_intents.list_order_intents_by_status(statuses)

    def get_order_intent_by_broker_tag(self, broker_tag: str) -> dict[str, Any] | None:
        return self.order_intents.get_order_intent_by_broker_tag(broker_tag)

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
        return self.order_intents.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            approval_id=approval_id,
            entry_intent_id=entry_intent_id,
            broker_order_id=broker_order_id,
            broker_tag=broker_tag,
            payload=payload,
            source=source,
        )

    # ── broker ──────────────────────────────────────────────────────

    def get_broker_order(self, broker_order_id: str) -> dict[str, Any] | None:
        return self.broker.get_broker_order(broker_order_id)

    def list_broker_orders(self) -> list[dict[str, Any]]:
        return self.broker.list_broker_orders()

    def list_broker_orders_by_tag(self, broker_tag: str) -> list[dict[str, Any]]:
        return self.broker.list_broker_orders_by_tag(broker_tag)

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
        return self.broker.upsert_broker_order(
            broker_order_id=broker_order_id,
            exchange_order_id=exchange_order_id,
            ticker=ticker,
            order_intent_id=order_intent_id,
            status=status,
            broker_tag=broker_tag,
            payload=payload,
            source=source,
        )

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
        return self.broker.upsert_broker_fill(
            fill_id=fill_id,
            broker_order_id=broker_order_id,
            order_intent_id=order_intent_id,
            ticker=ticker,
            quantity=quantity,
            fill_price=fill_price,
            payload=payload,
            source=source,
        )

    def list_broker_fills(self, broker_order_id: str | None = None) -> list[dict[str, Any]]:
        return self.broker.list_broker_fills(broker_order_id)

    def list_protective_triggers(self) -> list[dict[str, Any]]:
        return self.broker.list_protective_triggers()

    def get_protective_trigger(self, protective_trigger_id: str) -> dict[str, Any] | None:
        return self.broker.get_protective_trigger(protective_trigger_id)

    def get_protective_trigger_for_ticker(self, ticker: str) -> dict[str, Any] | None:
        return self.broker.get_protective_trigger_for_ticker(ticker)

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
        return self.broker.upsert_protective_trigger(
            protective_trigger_id=protective_trigger_id,
            position_id=position_id,
            ticker=ticker,
            status=status,
            payload=payload,
            source=source,
        )

    # ── positions ───────────────────────────────────────────────────

    def list_positions(self, *, states: set[str] | None = None) -> list[dict[str, Any]]:
        return self.positions.list_positions(states=states)

    def get_position(self, position_id: str) -> dict[str, Any] | None:
        return self.positions.get_position(position_id)

    def update_position_state(
        self,
        *,
        position_id: str,
        new_state: str,
        source: str,
        detail: str | None = None,
    ) -> dict[str, Any] | None:
        return self.positions.update_position_state(
            position_id=position_id, new_state=new_state, source=source, detail=detail
        )

    def update_position_price(
        self,
        *,
        position_id: str,
        current_price: float,
        source: str,
    ) -> dict[str, Any] | None:
        return self.positions.update_position_price(
            position_id=position_id, current_price=current_price, source=source
        )

    # ── trades ──────────────────────────────────────────────────────

    def trades_exist(self) -> bool:
        return self.trades.trades_exist()

    def upsert_trade(
        self,
        *,
        trade_id: str,
        ticker: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        opened_at: datetime,
        closed_at: datetime,
        pnl_abs: float,
        pnl_pct: float,
        exit_reason: str,
        payload: dict[str, Any] | None = None,
        source: str = "system",
    ) -> dict[str, Any]:
        return self.trades.upsert_trade(
            trade_id=trade_id,
            ticker=ticker,
            quantity=quantity,
            entry_price=entry_price,
            exit_price=exit_price,
            opened_at=opened_at,
            closed_at=closed_at,
            pnl_abs=pnl_abs,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            payload=payload,
            source=source,
        )

    def get_trades_payload(self) -> list[dict[str, Any]]:
        return self.trades.get_trades_payload()

    def replace_trades(
        self,
        payload: list[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        return self.trades.replace_trades(payload, source=source)

    # ── reconciliation ──────────────────────────────────────────────

    def upsert_reconciliation_run(
        self,
        *,
        reconciliation_run_id: str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.reconciliation.upsert_reconciliation_run(
            reconciliation_run_id=reconciliation_run_id,
            status=status,
            payload=payload,
            source=source,
        )

    def list_reconciliation_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        return self.reconciliation.list_reconciliation_runs(limit=limit)

    # ── failure incidents ───────────────────────────────────────────

    def get_failure_incident(self, incident_id: str) -> dict[str, Any] | None:
        return self.failures.get_failure_incident(incident_id)

    def list_failure_incidents(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.failures.list_failure_incidents(status=status, severity=severity)

    def upsert_failure_incident(
        self,
        *,
        incident_id: str,
        status: str,
        severity: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.failures.upsert_failure_incident(
            incident_id=incident_id,
            status=status,
            severity=severity,
            payload=payload,
            source=source,
        )

    # ── policy overlays ─────────────────────────────────────────────

    def get_policy_overlay(self, overlay_id: str) -> dict[str, Any] | None:
        return self.policy.get_policy_overlay(overlay_id)

    def list_policy_overlays(
        self,
        *,
        status: str | None = None,
        key: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        return self.policy.list_policy_overlays(status=status, key=key, limit=limit)

    def upsert_policy_overlay(
        self,
        *,
        overlay_id: str,
        key: str,
        value: dict[str, Any],
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.policy.upsert_policy_overlay(
            overlay_id=overlay_id,
            key=key,
            value=value,
            status=status,
            payload=payload,
            source=source,
        )

    def transition_policy_overlay_status(
        self,
        overlay_id: str,
        *,
        status: str,
        payload_updates: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        return self.policy.transition_policy_overlay_status(
            overlay_id=overlay_id,
            status=status,
            payload_updates=payload_updates,
            source=source,
        )

    # ── operator controls ───────────────────────────────────────────

    def get_operator_control(self, control_key: str) -> dict[str, Any] | None:
        return self.operator.get_operator_control(control_key)

    def list_operator_controls(self, *, prefix: str | None = None) -> list[dict[str, Any]]:
        return self.operator.list_operator_controls(prefix=prefix)

    def upsert_operator_control(
        self,
        *,
        control_key: str,
        value: dict[str, Any],
        payload: dict[str, Any] | None = None,
        source: str = "system",
    ) -> dict[str, Any]:
        return self.operator.upsert_operator_control(
            control_key=control_key, value=value, payload=payload, source=source
        )

    # ── auth session ────────────────────────────────────────────────

    def auth_session_exists(self) -> bool:
        return self._session.get(models_module.AuthSessionRow, "kite") is not None

    def get_auth_session_payload(self) -> dict[str, Any]:
        row = self._session.get(models_module.AuthSessionRow, "kite")
        return {} if row is None else dict(row.payload)

    def replace_auth_session(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        from ..models import StoredKiteSessionPayload

        session_payload = StoredKiteSessionPayload.model_validate(payload)
        normalized = session_payload.model_dump(mode="json")

        row = self._session.get(models_module.AuthSessionRow, "kite")
        if row is None:
            row = models_module.AuthSessionRow(session_key="kite", provider="kite")
            self._session.add(row)

        row.provider = "kite"
        row.user_id = session_payload.user_id
        row.access_token = session_payload.access_token
        row.public_token = session_payload.public_token
        row.payload = normalized

        self.append_execution_event(
            event_type="auth_session_replaced",
            entity_type="auth_session",
            entity_id="kite",
            source=source,
            payload={"provider": "kite", "user_id": session_payload.user_id},
        )
        return normalized
