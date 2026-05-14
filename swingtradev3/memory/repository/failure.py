"""FailureIncident sub-repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class FailureRepository:
    """Failure incident tracking."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_failure_incident(self, incident_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.FailureIncidentRow, incident_id)
        if row is None:
            return None
        return {
            "incident_id": row.incident_id,
            "status": row.status,
            "severity": row.severity,
            "payload": dict(row.payload),
        }

    def list_failure_incidents(
        self,
        *,
        status: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        self.session.flush()
        query = select(models_module.FailureIncidentRow).order_by(
            models_module.FailureIncidentRow.updated_at.desc()
        )
        if status is not None:
            query = query.where(models_module.FailureIncidentRow.status == status)
        if severity is not None:
            query = query.where(models_module.FailureIncidentRow.severity == severity)
        rows = self.session.scalars(query).all()
        return [
            {
                "incident_id": row.incident_id,
                "status": row.status,
                "severity": row.severity,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def upsert_failure_incident(
        self,
        *,
        incident_id: str,
        status: str,
        severity: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(models_module.FailureIncidentRow, incident_id)
        if row is None:
            row = models_module.FailureIncidentRow(incident_id=incident_id)
            self.session.add(row)

        row.status = status
        row.severity = severity
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
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