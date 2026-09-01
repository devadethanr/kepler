"""OperatorControl sub-repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class OperatorRepository:
    """Operator control flags and locks."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_operator_control(self, control_key: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.OperatorControlRow, control_key)
        if row is None:
            return None
        return {
            "control_key": row.control_key,
            "value": dict(row.value),
            "payload": dict(row.payload),
        }

    def list_operator_controls(self, *, prefix: str | None = None) -> list[dict[str, Any]]:
        query = select(models_module.OperatorControlRow).order_by(
            models_module.OperatorControlRow.control_key.asc()
        )
        if prefix:
            query = query.where(models_module.OperatorControlRow.control_key.like(f"{prefix}%"))
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
        source: str = "system",
    ) -> dict[str, Any]:
        row = self.session.get(models_module.OperatorControlRow, control_key)
        if row is None:
            row = models_module.OperatorControlRow(control_key=control_key)
            self.session.add(row)

        row.value = dict(value)
        row.payload = dict(payload or row.payload or {})

        EventRepository(self.session).append_execution_event(
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
