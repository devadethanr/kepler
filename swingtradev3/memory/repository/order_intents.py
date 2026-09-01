"""OrderIntent sub-repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class OrderIntentRepository:
    """Order intent lifecycle tracking."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_order_intent(self, order_intent_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.OrderIntentRow, order_intent_id)
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
            select(models_module.OrderIntentRow)
            .where(models_module.OrderIntentRow.ticker == ticker)
            .order_by(
                models_module.OrderIntentRow.updated_at.desc(),
                models_module.OrderIntentRow.created_at.desc(),
            )
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
            select(models_module.OrderIntentRow)
            .where(models_module.OrderIntentRow.ticker == ticker)
            .order_by(
                models_module.OrderIntentRow.updated_at.desc(),
                models_module.OrderIntentRow.created_at.desc(),
            )
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
            select(models_module.OrderIntentRow).order_by(
                models_module.OrderIntentRow.updated_at.desc()
            )
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

    def list_order_intents_by_status(self, statuses: set[str]) -> list[dict[str, Any]]:
        normalized = [str(status).strip() for status in statuses if str(status).strip()]
        if not normalized:
            return []
        rows = self.session.scalars(
            select(models_module.OrderIntentRow)
            .where(models_module.OrderIntentRow.status.in_(normalized))
            .order_by(
                models_module.OrderIntentRow.updated_at.asc(),
                models_module.OrderIntentRow.created_at.asc(),
            )
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
            select(models_module.OrderIntentRow)
            .where(models_module.OrderIntentRow.broker_tag == normalized)
            .order_by(
                models_module.OrderIntentRow.updated_at.desc(),
                models_module.OrderIntentRow.created_at.desc(),
            )
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
        row = self.session.get(models_module.OrderIntentRow, order_intent_id)
        if row is None:
            row = models_module.OrderIntentRow(order_intent_id=order_intent_id)
            self.session.add(row)

        row.ticker = ticker
        row.status = status
        row.approval_id = approval_id
        row.entry_intent_id = entry_intent_id
        row.broker_order_id = broker_order_id
        row.broker_tag = broker_tag
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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
