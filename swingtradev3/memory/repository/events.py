"""ExecutionEvent (append-only audit log) sub-repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module


class EventRepository:
    """Append-only execution event log."""

    def __init__(self, session: Session) -> None:
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
            models_module.ExecutionEventRow(
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
        import datetime as _dt

        query = select(models_module.ExecutionEventRow.event_id).where(
            models_module.ExecutionEventRow.event_type == event_type,
            models_module.ExecutionEventRow.entity_type == entity_type,
            models_module.ExecutionEventRow.entity_id == entity_id,
        )
        if source is not None:
            query = query.where(models_module.ExecutionEventRow.source == source)
        self.session.flush()
        return self.session.scalar(query.limit(1)) is not None

    def list_execution_events(
        self,
        *,
        limit: int = 100,
        after_id: int | None = None,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 500))
        query = select(models_module.ExecutionEventRow)
        if after_id is not None:
            query = query.where(models_module.ExecutionEventRow.event_id > after_id)
        if event_type:
            query = query.where(models_module.ExecutionEventRow.event_type == event_type)
        if after_id is None:
            rows = list(
                reversed(
                    self.session.scalars(
                        query.order_by(
                            models_module.ExecutionEventRow.event_id.desc()
                        ).limit(bounded_limit)
                    ).all()
                )
            )
        else:
            rows = self.session.scalars(
                query.order_by(
                    models_module.ExecutionEventRow.event_id.asc()
                ).limit(bounded_limit)
            ).all()
        return [
            {
                "event_id": row.event_id,
                "event_type": row.event_type,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "source": row.source,
                "payload": dict(row.payload or {}),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    def get_latest_execution_event_id(self) -> int | None:
        return self.session.scalar(
            select(models_module.ExecutionEventRow.event_id).order_by(
                models_module.ExecutionEventRow.event_id.desc()
            ).limit(1)
        )