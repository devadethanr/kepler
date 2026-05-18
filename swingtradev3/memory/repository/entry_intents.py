"""EntryIntent sub-repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class EntryIntentRepository:
    """Entry intent lifecycle."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_entry_intent(self, entry_intent_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.EntryIntentRow, entry_intent_id)
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
            select(models_module.EntryIntentRow).order_by(
                models_module.EntryIntentRow.created_at.desc(),
                models_module.EntryIntentRow.intent_id.asc(),
            )
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
        row = self.session.get(models_module.EntryIntentRow, entry_intent_id)
        if row is None:
            row = models_module.EntryIntentRow(intent_id=entry_intent_id)
            self.session.add(row)

        row.ticker = ticker
        row.status = status
        row.approval_id = approval_id
        row.order_intent_id = order_intent_id
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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
