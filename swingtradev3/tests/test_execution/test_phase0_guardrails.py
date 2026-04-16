from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import approvals as approvals_route
from config import cfg
from models import AccountState, TradingMode
from tools.execution.order_execution import OrderExecutionTool

client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield


def _state() -> AccountState:
    return AccountState(cash_inr=100000)


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


@pytest.mark.asyncio
async def test_live_order_blocked_when_live_guard_disabled(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    tool = OrderExecutionTool()
    tool.risk_tool.check_risk = MagicMock(
        return_value={"approved": True, "quantity": 10, "reason": "ok"}
    )

    with patch("tools.execution.order_execution.place_live_order") as mock_place:
        result = await tool.place_order_async(
            state=_state(),
            ticker="RELIANCE",
            side="buy",
            score=8.2,
            price=1010.0,
            stop_price=980.0,
            target_price=1080.0,
            quantity=5,
        )

    assert result["status"] == "blocked"
    assert result["reason"] == "LIVE_TRADING_ENABLED=false"
    mock_place.assert_not_called()


@pytest.mark.asyncio
async def test_live_order_requires_kite_session(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "true")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    tool = OrderExecutionTool()
    tool.risk_tool.check_risk = MagicMock(
        return_value={"approved": True, "quantity": 10, "reason": "ok"}
    )

    with patch("tools.execution.order_execution.has_kite_session", return_value=False):
        with patch("tools.execution.order_execution.place_live_order") as mock_place:
            result = await tool.place_order_async(
                state=_state(),
                ticker="RELIANCE",
                side="buy",
                score=8.2,
                price=1010.0,
                stop_price=980.0,
                target_price=1080.0,
                quantity=5,
            )

    assert result["status"] == "blocked"
    assert result["reason"] == "KITE_SESSION_REQUIRED"
    mock_place.assert_not_called()


@pytest.mark.asyncio
async def test_live_order_stays_submitted_until_fill_confirmation(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "true")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    tool = OrderExecutionTool()
    tool.risk_tool.check_risk = MagicMock(
        return_value={"approved": True, "quantity": 10, "reason": "ok"}
    )
    tool.gtt_manager.place_gtt_async = AsyncMock()

    with patch("tools.execution.order_execution.has_kite_session", return_value=True):
        with patch("tools.execution.order_execution.place_live_order", return_value="kite-order-123"):
            result = await tool.place_order_async(
                state=_state(),
                ticker="RELIANCE",
                side="buy",
                score=8.2,
                price=1010.0,
                stop_price=980.0,
                target_price=1080.0,
                quantity=5,
            )

    assert result["status"] == "submitted"
    assert result["order_id"] == "kite-order-123"
    assert result["quantity"] == 5
    assert result["average_price"] is None
    assert result["stop_gtt_id"] is None
    assert result["target_gtt_id"] is None
    assert result["protection_status"] == "pending_fill_confirmation"
    tool.gtt_manager.place_gtt_async.assert_not_called()


def test_approval_route_respects_live_guardrails(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

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
    assert "blocked by runtime guardrails" in body["message"]
    assert payload[0]["approved"] is True
    assert payload[0]["execution_requested"] is False
    mock_write.assert_called_once()
    mock_broadcast.assert_awaited_once()


def test_approval_route_rejects_expired_payload(monkeypatch):
    expired = _approval_payload()
    expired[0]["expires_at"] = (datetime.now() - timedelta(minutes=5)).isoformat()

    mock_write = MagicMock()
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "read_json", lambda *_args, **_kwargs: expired)
    monkeypatch.setattr(approvals_route, "write_json", mock_write)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post("/approvals/RELIANCE/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "expired"
    mock_write.assert_not_called()
    mock_broadcast.assert_not_awaited()


def test_approval_route_is_idempotent_for_already_queued_execution(monkeypatch):
    payload = _approval_payload()
    payload[0]["approved"] = True
    payload[0]["execution_requested"] = True
    payload[0]["execution_request_id"] = "existing123"

    mock_write = MagicMock()
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "read_json", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(approvals_route, "write_json", mock_write)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post("/approvals/RELIANCE/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert "already queued" in body["message"].lower()
    mock_write.assert_not_called()
    mock_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_position_monitor_requires_live_exit_only(monkeypatch):
    from api.tasks.scheduler import TradingScheduler

    scheduler = TradingScheduler()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    fake_now = datetime(2026, 4, 16, 10, 0)

    with patch("api.tasks.scheduler._now_ist", return_value=fake_now):
        with patch("storage.read_json", return_value={"positions": [{"ticker": "RELIANCE"}]}):
            with patch("google.adk.Runner") as mock_runner:
                await scheduler._position_monitor()

    mock_runner.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_position_monitor_runs_in_live_exit_only(monkeypatch):
    from api.tasks.scheduler import TradingScheduler

    scheduler = TradingScheduler()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "true")

    fake_now = datetime(2026, 4, 16, 10, 0)

    with patch("api.tasks.scheduler._now_ist", return_value=fake_now):
        with patch("storage.read_json", return_value={"positions": [{"ticker": "RELIANCE"}]}):
            with patch("google.adk.Runner") as mock_runner:
                runner_instance = mock_runner.return_value
                runner_instance.run_async = MagicMock(side_effect=_empty_event_stream)
                await scheduler._position_monitor()

    mock_runner.assert_called_once()
    runner_instance.run_async.assert_called_once()
