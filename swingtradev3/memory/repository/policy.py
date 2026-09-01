"""PolicyOverlay sub-repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class PolicyRepository:
    """Policy overlay lifecycle."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_policy_overlay(self, overlay_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.PolicyOverlayRow, overlay_id)
        if row is None:
            return None
        return self._payload(row)

    def list_policy_overlays(
        self,
        *,
        status: str | None = None,
        key: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        bounded = max(1, min(limit, 500))
        query = select(models_module.PolicyOverlayRow).order_by(
            models_module.PolicyOverlayRow.updated_at.asc(),
            models_module.PolicyOverlayRow.created_at.asc(),
        )
        if status:
            query = query.where(models_module.PolicyOverlayRow.status == status)
        if key:
            query = query.where(models_module.PolicyOverlayRow.key == key)
        rows = self.session.scalars(query.limit(bounded)).all()
        return [self._payload(row) for row in rows]

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
        row = self.session.get(models_module.PolicyOverlayRow, overlay_id)
        if row is None:
            row = models_module.PolicyOverlayRow(overlay_id=overlay_id)
            self.session.add(row)

        row.key = key
        row.value = dict(value)
        row.status = status
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
            event_type="policy_overlay_upserted",
            entity_type="policy_overlay",
            entity_id=overlay_id,
            source=source,
            payload={"key": key, "status": status},
        )
        return self._payload(row)

    def transition_policy_overlay_status(
        self,
        overlay_id: str,
        *,
        status: str,
        payload_updates: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(models_module.PolicyOverlayRow, overlay_id)
        if row is None:
            raise KeyError(overlay_id)
        previous = row.status
        row.status = status
        row.payload = dict(payload_updates)
        EventRepository(self.session).append_execution_event(
            event_type="policy_overlay_status_changed",
            entity_type="policy_overlay",
            entity_id=overlay_id,
            source=source,
            payload={"key": row.key, "previous_status": previous, "status": status},
        )
        return self._payload(row)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _payload(row: models_module.PolicyOverlayRow) -> dict[str, Any]:
        return {
            "overlay_id": row.overlay_id,
            "key": row.key,
            "value": dict(row.value or {}),
            "status": row.status,
            "payload": dict(row.payload or {}),
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
