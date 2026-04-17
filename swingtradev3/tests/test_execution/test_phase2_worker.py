from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import approvals as approvals_route
from config import cfg
from execution.operator_controls import read_worker_status, write_worker_status
from execution.state_machine import WorkerExecutionStateMachine
from memory.db import session_scope
from memory.repositories import MemoryRepository


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield


def _approval_payload() -> list[dict[str, object]]:
    now = datetime.now()
    return [
        {
            "ticker": "RELIANCE",
            "score": 8.2,
            "setup_type": "breakout",
            "entry_zone": {"low": 1000.0, "high": 1010.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 7,
            "confidence_reasoning": "Strong setup",
            "risk_flags": [],
            "approved": None,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=4)).isoformat(),
        }
    ]


async def _empty_event_stream(*_args, **_kwargs):
    if False:
        yield None


def test_approval_route_queues_worker_execution(monkeypatch):
    payload = _approval_payload()
    mock_write = MagicMock()
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "read_json", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(approvals_route, "write_json", mock_write)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post("/approvals/RELIANCE/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert body["message"] == "Approved. Queued for worker execution."
    assert payload[0]["approved"] is True
    assert payload[0]["execution_requested"] is True
    assert payload[0]["execution_request_id"]
    mock_write.assert_called_once()
    mock_broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_state_machine_runs_order_agent_for_queued_approvals(monkeypatch):
    queued = _approval_payload()
    queued[0]["approved"] = True
    queued[0]["execution_requested"] = True
    queued[0]["execution_request_id"] = "req-phase2"

    state_machine = WorkerExecutionStateMachine()
    monkeypatch.setattr(state_machine, "pending_execution_requests", lambda: queued)

    with patch("execution.state_machine.Runner") as mock_runner:
        runner_instance = mock_runner.return_value
        runner_instance.run_async = MagicMock(side_effect=_empty_event_stream)

        executed = await state_machine.execute_requested_approvals()

    assert executed == 1
    mock_runner.assert_called_once()
    runner_instance.run_async.assert_called_once()


def test_dashboard_scheduler_reads_worker_status():
    original_status = read_worker_status()
    status = {
        "is_running": True,
        "current_phase": "market_hours",
        "total_jobs": 17,
        "next_run": "2026-04-17 10:05:00",
        "next_task": "In 4 min",
        "failed_events": 2,
    }

    try:
        write_worker_status(status)
        response = client.get("/dashboard/scheduler")
        assert response.status_code == 200
        body = response.json()
        assert body["is_running"] is True
        assert body["current_phase"] == "market_hours"
        assert body["failed_events"] == 2
    finally:
        if original_status:
            write_worker_status(original_status)


def test_failed_event_retry_is_queued_for_worker():
    event_id = "event-phase2-retry"

    response = client.post(f"/portfolio/failed-events/{event_id}/retry")

    assert response.status_code == 200
    assert response.json()["message"] == "Retry queued for worker"
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(f"retry_failed_event:{event_id}")
    assert control is not None
    assert control["value"]["event_id"] == event_id
