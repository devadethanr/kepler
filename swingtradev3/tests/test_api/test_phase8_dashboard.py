from __future__ import annotations

import inspect
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.main import app
from api.routes import approvals, dashboard, portfolio, positions, sse, trades
from config import cfg
from memory.db import session_scope
from memory.repositories import MemoryRepository
from api.tasks.session_phase import IST, session_snapshot


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield


@pytest.fixture
def restore_portfolio_memory():
    with session_scope() as session:
        repo = MemoryRepository(session)
        original_state = repo.get_account_state_payload()
        original_trades = repo.get_trades_payload()

    yield

    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.replace_account_state(original_state, source="test_phase8_restore")
        repo.replace_trades(original_trades, source="test_phase8_restore")


def _phase8_state() -> dict[str, object]:
    return {
        "cash_inr": 123456.0,
        "realized_pnl": 1500.0,
        "unrealized_pnl": 225.5,
        "drawdown_pct": 1.2,
        "weekly_loss_pct": 0.4,
        "consecutive_losses": 1,
        "positions": [
            {
                "ticker": "PHASE8DASH",
                "quantity": 4,
                "entry_price": 100.0,
                "current_price": 112.5,
                "stop_price": 94.0,
                "target_price": 130.0,
                "opened_at": "2026-04-29T09:20:00",
                "entry_order_id": "phase8-entry-order",
                "lifecycle_state": "open",
                "thesis_score": 8.1,
                "research_date": "2026-04-28",
                "skill_version": "phase8-test",
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    }


def _phase8_trade() -> dict[str, object]:
    return {
        "trade_id": "phase8-trade-1",
        "ticker": "PHASE8DASH",
        "quantity": 4,
        "entry_price": 100.0,
        "exit_price": 118.0,
        "opened_at": "2026-04-25T09:20:00",
        "closed_at": "2026-04-28T14:55:00",
        "exit_reason": "target_hit",
        "pnl_abs": 72.0,
        "pnl_pct": 18.0,
        "setup_type": "breakout",
        "thesis_reasoning": "Phase 8 dashboard route test",
        "research_date": "2026-04-24",
        "skill_version": "phase8-test",
        "risk_flags": [],
    }


def test_phase8_dashboard_reads_repository_backed_runtime_state(restore_portfolio_memory):
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.replace_account_state(_phase8_state(), source="test_phase8_dashboard")
        repo.replace_trades([_phase8_trade()], source="test_phase8_dashboard")

    snapshot_response = client.get("/dashboard/snapshot")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["portfolio"]["cash_inr"] == 123456.0
    assert snapshot["portfolio"]["total_pnl"] == 1725.5
    assert snapshot["portfolio"]["sector_exposure"]["IT"] == 450.0
    assert snapshot["counts"]["positions"] == 1
    assert snapshot["positions"][0]["ticker"] == "PHASE8DASH"

    positions_response = client.get("/positions")
    assert positions_response.status_code == 200
    assert positions_response.json()[0]["ticker"] == "PHASE8DASH"

    trades_response = client.get("/trades")
    assert trades_response.status_code == 200
    assert trades_response.json()[0]["trade_id"] == "phase8-trade-1"

    portfolio_response = client.get("/portfolio/summary")
    assert portfolio_response.status_code == 200
    assert portfolio_response.json()["total_invested"] == 450.0

    quotes_response = client.get("/dashboard/quotes")
    assert quotes_response.status_code == 200
    quotes = quotes_response.json()["quotes"]
    assert quotes == [
        {
            "ticker": "PHASE8DASH",
            "price": 112.5,
            "source": "position",
            "stale": True,
            "position_state": "open",
            "updated_at": None,
        }
    ]

    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.update_position_price(
            position_id="PHASE8DASH",
            current_price=113.25,
            source="test_phase8_dashboard",
        )

    fresh_quotes_response = client.get("/dashboard/quotes")
    assert fresh_quotes_response.status_code == 200
    fresh_quote = fresh_quotes_response.json()["quotes"][0]
    assert fresh_quote["ticker"] == "PHASE8DASH"
    assert fresh_quote["price"] == 113.25
    assert fresh_quote["stale"] is False
    assert fresh_quote["position_state"] == "open"
    assert fresh_quote["updated_at"] is not None


def test_phase8_dashboard_events_are_durable_and_cursor_filtered():
    with session_scope() as session:
        repo = MemoryRepository(session)
        baseline = repo.get_latest_execution_event_id() or 0
        repo.append_execution_event(
            event_type="phase8_test_a",
            entity_type="dashboard",
            entity_id="phase8-a",
            source="test_phase8",
            payload={"sequence": 1},
        )
        repo.append_execution_event(
            event_type="phase8_test_b",
            entity_type="dashboard",
            entity_id="phase8-b",
            source="test_phase8",
            payload={"sequence": 2},
        )

    response = client.get(f"/dashboard/events?after_id={baseline}&limit=10")
    assert response.status_code == 200
    events = [
        event for event in response.json() if event["source"] == "test_phase8"
    ]
    assert [event["event_type"] for event in events] == [
        "phase8_test_a",
        "phase8_test_b",
    ]
    assert all(event["event_id"] > baseline for event in events)

    latest_response = client.get("/dashboard/events?event_type=phase8_test_b&limit=1")
    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert len(latest) == 1
    assert latest[0]["event_type"] == "phase8_test_b"
    assert latest[0]["payload"] == {"sequence": 2}


def test_phase8_activity_endpoint_exposes_agents_sources_and_audit_trail():
    with session_scope() as session:
        repo = MemoryRepository(session)
        baseline = repo.get_latest_execution_event_id() or 0
        repo.append_execution_event(
            event_type="overnight_agent_step",
            entity_type="agent",
            entity_id="evidence_assembler",
            source="overnight_test_agent",
            payload={"task": "assemble candidate evidence"},
        )

    response = client.get("/dashboard/activity")
    assert response.status_code == 200
    payload = response.json()
    assert "agents" in payload
    assert "observed_sources" in payload
    assert "scan_status" in payload
    assert "worker_status" in payload
    assert "session" in payload
    assert payload["event_count"] >= 1
    assert any(
        source["agent_name"] == "overnight_test_agent"
        and source["last_event"] == "overnight_agent_step"
        for source in payload["observed_sources"]
    )
    assert any(
        event["event_id"] > baseline
        and event["source"] == "overnight_test_agent"
        and event["payload"] == {"task": "assemble candidate evidence"}
        for event in payload["recent_events"]
    )


def test_phase8_sse_frames_and_resume_cursor_are_stable():
    frame = sse._sse_frame(
        event="execution_event",
        event_id=42,
        data={
            "type": "phase8_test",
            "created_at": datetime(2026, 4, 29, 9, 30, tzinfo=IST),
        },
    )
    assert frame.startswith("id: 42\nevent: execution_event\ndata: ")
    payload = json.loads(frame.split("data: ", 1)[1])
    assert payload["type"] == "phase8_test"
    assert payload["created_at"] == "2026-04-29T09:30:00+05:30"

    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/sse/live",
            "query_string": b"",
            "headers": [(b"last-event-id", b"41")],
        }
    )
    assert sse._cursor_from_request(request, None) == 41
    assert sse._cursor_from_request(request, 43) == 43


def test_phase8_session_phase_uses_ist_holidays_and_segments():
    holiday_market_time = datetime(2026, 5, 1, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    holiday_snapshot = session_snapshot(holiday_market_time)
    assert holiday_snapshot["current_phase"] == "market_closed"
    assert holiday_snapshot["market_status"] == "closed"
    assert holiday_snapshot["day_label"] == "CLOSED"
    assert holiday_snapshot["holiday"] == "Maharashtra Day"
    assert {segment["key"] for segment in holiday_snapshot["segments"]} >= {
        "overnight_monitoring",
        "pre_market_prep",
        "market_hours",
        "post_market",
        "evening_research",
        "wind_down",
    }

    trading_time = datetime(2026, 5, 4, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    trading_snapshot = session_snapshot(trading_time)
    assert trading_snapshot["current_phase"] == "market_hours"
    assert trading_snapshot["market_status"] == "open"
    assert trading_snapshot["day_label"] == "T-0"


def test_phase8_knowledge_routes_are_explicitly_deferred_mocks():
    graph_response = client.get("/dashboard/knowledge/graph")
    assert graph_response.status_code == 200
    graph = graph_response.json()
    assert graph["phase"] == "phase_14_mock"
    assert graph["nodes"]
    assert graph["edges"]

    stock_response = client.get("/dashboard/knowledge/stock/reliance")
    assert stock_response.status_code == 200
    stock = stock_response.json()
    assert stock["phase"] == "phase_14_mock"
    assert stock["ticker"] == "RELIANCE"


def test_phase8_dashboard_routes_do_not_use_route_level_json_storage():
    for module in (approvals, dashboard, portfolio, positions, trades):
        source = inspect.getsource(module)
        assert "from storage import read_json" not in source
        assert "from storage import write_json" not in source
        assert "read_json(" not in source
        assert "write_json(" not in source


def test_api_auth_fails_closed_when_enabled_without_configured_key(monkeypatch):
    monkeypatch.setattr(cfg.api, "enabled", True)
    monkeypatch.delenv("FASTAPI_API_KEY", raising=False)

    health_response = client.get("/health")
    assert health_response.status_code == 200

    missing_key_response = client.get("/positions")
    assert missing_key_response.status_code == 403
    assert "no API key is configured" in missing_key_response.json()["detail"]

    monkeypatch.setenv("FASTAPI_API_KEY", "phase8-secret")
    wrong_key_response = client.get("/positions", headers={"X-API-Key": "wrong"})
    assert wrong_key_response.status_code == 403

    correct_key_response = client.get("/positions", headers={"X-API-Key": "phase8-secret"})
    assert correct_key_response.status_code == 200
