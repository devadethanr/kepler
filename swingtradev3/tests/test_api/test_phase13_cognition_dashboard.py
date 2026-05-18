from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import cfg
from memory.db import session_scope
from memory.repository import MemoryRepository


IST = ZoneInfo("Asia/Kolkata")
client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield


def test_phase13_cognition_dashboard_endpoints_show_run_reports_and_plan():
    suffix = datetime.now(IST).strftime("%H%M%S%f")
    run_id = f"phase13-api-run:{suffix}"
    report_id = f"{run_id}:SBIN:final"
    plan_id = f"session-plan:phase13-api:{suffix}"

    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_cognition_run(
            run_id=run_id,
            phase="phase_13",
            status="completed",
            started_at=datetime.now(IST),
            completed_at=datetime.now(IST),
            payload={"run_id": run_id},
            source="test_phase13_api",
        )
        repo.upsert_cognition_report(
            report_id=report_id,
            run_id=run_id,
            ticker="SBIN",
            agent_name="final_intent_judge",
            schema_version="v1",
            status="proposed",
            payload={"decision": "BUY_ONLY_ABOVE_TRIGGER"},
            source="test_phase13_api",
        )
        repo.upsert_session_execution_plan(
            plan_id=plan_id,
            trading_date="2026-05-17",
            status="ready",
            payload={"plan_id": plan_id, "status": "ready"},
            source="test_phase13_api",
        )

    runs = client.get("/dashboard/cognition/runs?limit=20")
    assert runs.status_code == 200
    assert any(item["run_id"] == run_id for item in runs.json()["runs"])

    run = client.get(f"/dashboard/cognition/runs/{run_id}")
    assert run.status_code == 200
    assert run.json()["run"]["run_id"] == run_id
    assert run.json()["reports"][0]["report_id"] == report_id

    reports = client.get("/dashboard/cognition/reports/SBIN")
    assert reports.status_code == 200
    assert any(item["report_id"] == report_id for item in reports.json()["reports"])

    plan = client.get("/dashboard/session-plan?trading_date=2026-05-17")
    assert plan.status_code == 200
    assert plan.json()["plan"]["plan_id"] == plan_id

