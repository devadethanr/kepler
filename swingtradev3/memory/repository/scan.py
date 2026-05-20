"""Scan run repository for Postgres-backed scan tracking."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module


class ScanRepository:
    """Repository for scan run tracking."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_scan_run(
        self,
        *,
        run_id: str,
        status: str,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        error: str | None = None,
        result_summary: dict[str, Any] | None = None,
    ) -> None:
        """Insert or update a scan run record."""
        existing = self.session.get(models_module.ScanRunRow, run_id)
        if existing:
            existing.status = status
            if started_at is not None:
                existing.started_at = started_at
            if completed_at is not None:
                existing.completed_at = completed_at
            if error is not None:
                existing.error = error
            if result_summary is not None:
                existing.result_summary = result_summary
        else:
            self.session.add(
                models_module.ScanRunRow(
                    run_id=run_id,
                    status=status,
                    started_at=started_at,
                    completed_at=completed_at,
                    error=error,
                    result_summary=result_summary,
                )
            )

    def get_scan_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a scan run by ID."""
        row = self.session.get(models_module.ScanRunRow, run_id)
        if not row:
            return None
        return {
            "run_id": row.run_id,
            "status": row.status,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "error": row.error,
            "result_summary": row.result_summary,
        }

    def get_latest_scan_run(self) -> dict[str, Any] | None:
        """Get the most recent scan run."""
        stmt = (
            select(models_module.ScanRunRow)
            .order_by(models_module.ScanRunRow.started_at.desc())
            .limit(1)
        )
        row = self.session.scalar(stmt)
        if not row:
            return None
        return {
            "run_id": row.run_id,
            "status": row.status,
            "started_at": row.started_at,
            "completed_at": row.completed_at,
            "error": row.error,
            "result_summary": row.result_summary,
        }