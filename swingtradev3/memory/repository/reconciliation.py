"""ReconciliationRun sub-repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class ReconciliationRepository:
    """Reconciliation run tracking."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_reconciliation_run(
        self,
        *,
        reconciliation_run_id: str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(models_module.ReconciliationRunRow, reconciliation_run_id)
        if row is None:
            row = models_module.ReconciliationRunRow(reconciliation_run_id=reconciliation_run_id)
            self.session.add(row)

        row.status = status
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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

    def list_reconciliation_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        bounded = max(1, min(limit, 200))
        rows = self.session.scalars(
            select(models_module.ReconciliationRunRow)
            .order_by(
                models_module.ReconciliationRunRow.updated_at.desc(),
                models_module.ReconciliationRunRow.created_at.desc(),
            )
            .limit(bounded)
        ).all()
        return [
            {
                "reconciliation_run_id": row.reconciliation_run_id,
                "status": row.status,
                "payload": dict(row.payload or {}),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]