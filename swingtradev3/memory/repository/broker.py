"""BrokerOrder, BrokerFill, and ProtectiveTrigger sub-repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


IST = ZoneInfo("Asia/Kolkata")


class BrokerRepository:
    """Broker orders, fills, and protective triggers."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── broker orders ────────────────────────────────────────────────

    def get_broker_order(self, broker_order_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.BrokerOrderRow, broker_order_id)
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
        rows = self.session.scalars(
            select(models_module.BrokerOrderRow).order_by(models_module.BrokerOrderRow.updated_at.desc())
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

    def list_broker_orders_by_tag(self, broker_tag: str) -> list[dict[str, Any]]:
        normalized = broker_tag.strip()
        if not normalized:
            return []
        rows = self.session.scalars(
            select(models_module.BrokerOrderRow)
            .where(models_module.BrokerOrderRow.broker_tag == normalized)
            .order_by(models_module.BrokerOrderRow.updated_at.desc(), models_module.BrokerOrderRow.created_at.desc())
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
        row = self.session.get(models_module.BrokerOrderRow, broker_order_id)
        if row is None:
            row = models_module.BrokerOrderRow(broker_order_id=broker_order_id)
            self.session.add(row)

        row.exchange_order_id = exchange_order_id
        row.ticker = ticker
        row.order_intent_id = order_intent_id
        row.status = status
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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

    # ── broker fills ─────────────────────────────────────────────────

    def list_broker_fills(self, broker_order_id: str | None = None) -> list[dict[str, Any]]:
        query = select(models_module.BrokerFillRow).order_by(
            models_module.BrokerFillRow.created_at.asc(), models_module.BrokerFillRow.fill_id.asc()
        )
        if broker_order_id is not None:
            query = query.where(models_module.BrokerFillRow.broker_order_id == broker_order_id)
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
        row = self.session.get(models_module.BrokerFillRow, fill_id)
        if row is None:
            row = models_module.BrokerFillRow(fill_id=fill_id)
            self.session.add(row)

        row.broker_order_id = broker_order_id
        row.order_intent_id = order_intent_id
        row.ticker = ticker
        row.quantity = quantity
        row.fill_price = fill_price
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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

    # ── protective triggers ──────────────────────────────────────────

    def list_protective_triggers(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(models_module.ProtectiveTriggerRow).order_by(
                models_module.ProtectiveTriggerRow.updated_at.desc()
            )
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
        row = self.session.get(models_module.ProtectiveTriggerRow, protective_trigger_id)
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
            select(models_module.ProtectiveTriggerRow)
            .where(models_module.ProtectiveTriggerRow.ticker == normalized)
            .order_by(
                models_module.ProtectiveTriggerRow.updated_at.desc(),
                models_module.ProtectiveTriggerRow.created_at.desc(),
            )
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
        row = self.session.get(models_module.ProtectiveTriggerRow, protective_trigger_id)
        if row is None:
            row = models_module.ProtectiveTriggerRow(protective_trigger_id=protective_trigger_id)
            self.session.add(row)

        row.position_id = position_id
        row.ticker = ticker
        row.status = status
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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