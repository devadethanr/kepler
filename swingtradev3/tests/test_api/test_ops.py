from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import cfg
from execution.operator_controls import read_worker_status, write_worker_status
from memory.db import session_scope
from memory.repositories import MemoryRepository


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with (
        patch.object(cfg.api, "enabled", False),
        patch("api.routes.ops.is_session_fresh", return_value=(True, None, 1.0)),
    ):
        yield


def test_reconcile_ack_route_queues_worker_control():
    response = client.post("/ops/reconcile/ack/RELIANCE", json={"resolution": "retain"})

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    with session_scope() as session:
        repo = MemoryRepository(session)
        control = repo.get_operator_control("reconcile_ack:RELIANCE")
    assert control is not None
    assert control["value"]["status"] == "pending"
    assert control["value"]["resolution"] == "retain"


def test_reconcile_ack_route_rejects_invalid_resolution():
    response = client.post("/ops/reconcile/ack/RELIANCE", json={"resolution": "nonsense"})

    assert response.status_code == 400


def test_ops_safety_exposes_worker_runtime_counters():
    original_status = read_worker_status()
    status = {
        "is_running": True,
        "current_phase": "market_hours",
        "total_jobs": 7,
        "next_run": "2026-04-22 10:05:00",
        "next_task": "In 4 min",
        "failed_events": 0,
        "safety_counters": {
            "coordinator": {
                "order_submission_failures": {"count": 2, "threshold": 3, "tripped": False}
            }
        },
    }

    try:
        write_worker_status(status)
        response = client.get("/ops/safety")
        assert response.status_code == 200
        body = response.json()
        assert body["worker_status"]["is_running"] is True
        assert (
            body["runtime_counters"]["coordinator"]["order_submission_failures"]["count"] == 2
        )
    finally:
        if original_status:
            write_worker_status(original_status)
