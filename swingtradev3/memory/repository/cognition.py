"""Cognition audit and session-plan sub-repository."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


IST = ZoneInfo("Asia/Kolkata")


def _as_ist(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def _parse_trading_date(value: date | str | None) -> date:
    if value is None:
        return datetime.now(IST).date()
    if isinstance(value, datetime):
        return value.astimezone(IST).date() if value.tzinfo else value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class CognitionRepository:
    """Phase 13 durable audit store for slow-brain desk runs and plans."""

    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _run_payload(row: models_module.CognitionRunRow) -> dict[str, Any]:
        return {
            "run_id": row.run_id,
            "phase": row.phase,
            "status": row.status,
            "started_at": row.started_at.isoformat(),
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _report_payload(row: models_module.CognitionReportRow) -> dict[str, Any]:
        return {
            "report_id": row.report_id,
            "run_id": row.run_id,
            "ticker": row.ticker,
            "agent_name": row.agent_name,
            "schema_version": row.schema_version,
            "status": row.status,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _plan_payload(row: models_module.SessionExecutionPlanRow) -> dict[str, Any]:
        return {
            "plan_id": row.plan_id,
            "trading_date": row.trading_date.isoformat(),
            "status": row.status,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

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
        row = self.session.get(models_module.CognitionRunRow, run_id)
        if row is None:
            row = models_module.CognitionRunRow(
                run_id=run_id,
                started_at=_as_ist(started_at) or datetime.now(IST),
            )
            self.session.add(row)

        row.phase = phase
        row.status = status
        if started_at is not None:
            row.started_at = _as_ist(started_at) or started_at
        row.completed_at = _as_ist(completed_at)
        row.payload = dict(payload or {})

        EventRepository(self.session).append_execution_event(
            event_type="cognition_run_started" if status == "started" else "cognition_run_updated",
            entity_type="cognition_run",
            entity_id=run_id,
            source=source,
            payload={"phase": phase, "status": status},
        )
        return self._run_payload(row)

    def get_cognition_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.CognitionRunRow, run_id)
        if row is None:
            return None
        return self._run_payload(row)

    def list_cognition_runs(
        self,
        *,
        limit: int = 50,
        phase: str | None = None,
    ) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 200))
        statement = select(models_module.CognitionRunRow)
        if phase:
            statement = statement.where(models_module.CognitionRunRow.phase == phase)
        rows = self.session.scalars(
            statement.order_by(
                models_module.CognitionRunRow.started_at.desc(),
                models_module.CognitionRunRow.run_id.asc(),
            )
            .limit(bounded)
        ).all()
        return [self._run_payload(row) for row in rows]

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
        row = self.session.get(models_module.CognitionReportRow, report_id)
        if row is None:
            row = models_module.CognitionReportRow(report_id=report_id, run_id=run_id)
            self.session.add(row)

        row.run_id = run_id
        row.ticker = ticker.strip().upper() if ticker else None
        row.agent_name = agent_name
        row.schema_version = schema_version
        row.status = status
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
            event_type="cognition_agent_completed",
            entity_type="cognition_report",
            entity_id=report_id,
            source=source,
            payload={
                "run_id": run_id,
                "ticker": row.ticker,
                "agent_name": agent_name,
                "status": status,
            },
        )
        return self._report_payload(row)

    def list_cognition_reports(
        self,
        *,
        run_id: str | None = None,
        ticker: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 500))
        statement = select(models_module.CognitionReportRow)
        if run_id:
            statement = statement.where(models_module.CognitionReportRow.run_id == run_id)
        if ticker:
            statement = statement.where(
                models_module.CognitionReportRow.ticker == ticker.strip().upper()
            )
        rows = self.session.scalars(
            statement.order_by(
                models_module.CognitionReportRow.created_at.asc(),
                models_module.CognitionReportRow.report_id.asc(),
            ).limit(bounded)
        ).all()
        return [self._report_payload(row) for row in rows]

    def upsert_session_execution_plan(
        self,
        *,
        plan_id: str,
        trading_date: date | str,
        status: str,
        payload: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        row = self.session.get(models_module.SessionExecutionPlanRow, plan_id)
        if row is None:
            row = models_module.SessionExecutionPlanRow(plan_id=plan_id)
            self.session.add(row)

        row.trading_date = _parse_trading_date(trading_date)
        row.status = status
        row.payload = dict(payload)

        EventRepository(self.session).append_execution_event(
            event_type="session_plan_updated",
            entity_type="session_execution_plan",
            entity_id=plan_id,
            source=source,
            payload={"trading_date": row.trading_date.isoformat(), "status": status},
        )
        return self._plan_payload(row)

    def latest_session_execution_plan(
        self,
        *,
        trading_date: date | str | None = None,
    ) -> dict[str, Any] | None:
        statement = select(models_module.SessionExecutionPlanRow)
        if trading_date is not None:
            statement = statement.where(
                models_module.SessionExecutionPlanRow.trading_date
                == _parse_trading_date(trading_date)
            )
        row = self.session.scalars(
            statement.order_by(
                models_module.SessionExecutionPlanRow.trading_date.desc(),
                models_module.SessionExecutionPlanRow.updated_at.desc(),
            ).limit(1)
        ).first()
        if row is None:
            return None
        return self._plan_payload(row)

    def list_session_execution_plans(self, *, limit: int = 20) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 100))
        rows = self.session.scalars(
            select(models_module.SessionExecutionPlanRow)
            .order_by(
                models_module.SessionExecutionPlanRow.trading_date.desc(),
                models_module.SessionExecutionPlanRow.updated_at.desc(),
            )
            .limit(bounded)
        ).all()
        return [self._plan_payload(row) for row in rows]
