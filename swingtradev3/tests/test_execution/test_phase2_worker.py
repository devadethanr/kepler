from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import approvals as approvals_route
from config import cfg
from execution.bootstrap import WorkerRuntime
from execution.operator_controls import read_worker_status, write_worker_status
from execution.state_machine import WorkerExecutionStateMachine
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import PendingApproval, TradingMode


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


def test_approval_route_queues_worker_execution(monkeypatch):
    payload = _approval_payload()
    mock_write = MagicMock()
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "read_json", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(approvals_route, "write_json", mock_write)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post(f"/approvals/{PendingApproval.model_validate(payload[0]).approval_id}/yes")

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
async def test_worker_state_machine_runs_coordinator_for_queued_order_intents(monkeypatch):
    queued = [{"order_intent_id": "order-intent:RELIANCE:req-phase4"}]

    state_machine = WorkerExecutionStateMachine()
    monkeypatch.setattr(state_machine.coordinator, "pending_execution_requests", lambda: queued)
    submit_mock = AsyncMock(return_value=1)
    monkeypatch.setattr(state_machine.coordinator, "submit_queued_order_intents", submit_mock)

    executed = await state_machine.execute_requested_approvals()

    assert executed == 1
    submit_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_worker_state_machine_advances_active_executions(monkeypatch):
    state_machine = WorkerExecutionStateMachine()
    advance_mock = AsyncMock(return_value=2)
    monkeypatch.setattr(state_machine.coordinator, "reconcile_active_order_intents", advance_mock)

    advanced = await state_machine.advance_active_executions()

    assert advanced == 2
    advance_mock.assert_awaited_once()


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


@pytest.mark.asyncio
async def test_worker_processes_reconcile_ack_controls():
    position_id = "PHASE2RECON"
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_operator_control(
            control_key=f"reconcile_ack:{position_id}",
            value={
                "position_id": position_id,
                "resolution": "retain",
                "status": "pending",
                "requested_at": datetime.now().isoformat(),
            },
            payload={"type": "reconcile_ack"},
            source="test",
        )

    runtime = WorkerRuntime()
    runtime._state_machine.resolve_reconcile_required = AsyncMock(
        return_value={"status": "retained", "position_id": position_id}
    )

    await runtime._process_operator_controls_once()

    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control(f"reconcile_ack:{position_id}")
    assert control is not None
    assert control["value"]["status"] == "completed"
    assert any(
        call.kwargs
        == {
            "position_id": position_id,
            "resolution": "retain",
            "source": "worker_operator_control",
        }
        for call in runtime._state_machine.resolve_reconcile_required.await_args_list
    )


@pytest.mark.asyncio
async def test_worker_runs_quote_loop_but_skips_live_broker_reconcile_tasks_in_paper_mode(
    monkeypatch,
):
    runtime = WorkerRuntime()
    fake_lease = MagicMock()

    monkeypatch.setattr(cfg.trading, "mode", TradingMode.PAPER)
    monkeypatch.setattr("execution.bootstrap.initialize_memory_layer", MagicMock())
    monkeypatch.setattr("execution.bootstrap.WorkerLease.acquire", MagicMock(return_value=fake_lease))
    monkeypatch.setattr("execution.bootstrap.scheduler.start", AsyncMock())
    monkeypatch.setattr("execution.bootstrap.scheduler.stop", AsyncMock())
    monkeypatch.setattr(runtime, "_maintain_broker_stream", AsyncMock())
    monkeypatch.setattr(runtime, "_write_status", AsyncMock())
    monkeypatch.setattr(runtime, "_approval_loop", AsyncMock())
    monkeypatch.setattr(runtime, "_operator_control_loop", AsyncMock())
    monkeypatch.setattr(runtime, "_heartbeat_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_quote_freshness_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_orders_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_positions_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_gtts_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_broker_connection_loop", AsyncMock())
    monkeypatch.setattr(runtime._reconciler, "run_daily_loss_loop", AsyncMock())

    await runtime.start()
    try:
        task_names = {task.get_name() for task in runtime._tasks}
        assert task_names == {
            "worker-approval-loop",
            "worker-operator-control-loop",
            "worker-heartbeat-loop",
            "worker-reconcile-quote-loop",
        }
    finally:
        await runtime.stop()
