from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import approvals as approvals_route
from config import cfg
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import AccountState, PendingApproval, TradingMode
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
        with patch(
            "tools.execution.order_execution.calculate_live_order_margins",
            return_value=[{"total": 5000.0}],
        ):
            with patch(
                "tools.execution.order_execution.fetch_margins",
                return_value={"equity": {"available": {"cash": 100000.0}}},
            ):
                with patch(
                    "tools.execution.order_execution.place_live_order",
                    return_value="kite-order-123",
                ):
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
    assert result["broker_tag"]
    assert result["oco_gtt_id"] is None
    assert result["protection_status"] == "pending_fill_confirmation"
    tool.gtt_manager.place_gtt_async.assert_not_called()


def test_approval_route_respects_live_guardrails(monkeypatch, persist_approvals):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    payload = persist_approvals(_approval_payload())
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "project_all_managed_files", lambda: None)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post(f"/approvals/{PendingApproval.model_validate(payload[0]).approval_id}/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert "blocked by runtime guardrails" in body["message"]
    with session_scope() as session:
        repo = MemoryRepository(session)
        approval = repo.get_approval(str(payload[0]["approval_id"]))
        order_intent = repo.get_order_intent(str(payload[0]["order_intent_id"]))
    assert approval is not None
    assert approval["approved"] is True
    assert approval["execution_requested"] is False
    assert order_intent is not None
    assert order_intent["status"] == "approved"
    mock_broadcast.assert_awaited_once()


def test_approval_route_rejects_expired_payload(monkeypatch, persist_approvals):
    expired_payload = _approval_payload()
    expired_payload[0]["expires_at"] = (datetime.now() - timedelta(minutes=5)).isoformat()
    expired = persist_approvals(expired_payload)

    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "project_all_managed_files", lambda: None)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post(f"/approvals/{PendingApproval.model_validate(expired[0]).approval_id}/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "expired"
    with session_scope() as session:
        repo = MemoryRepository(session)
        approval = repo.get_approval(str(expired[0]["approval_id"]))
    assert approval is not None
    assert approval["status"] == "expired"
    assert approval["execution_requested"] is False
    mock_broadcast.assert_not_awaited()


def test_approval_route_is_idempotent_for_already_queued_execution(monkeypatch, persist_approvals):
    queued_payload = _approval_payload()
    queued_payload[0]["approved"] = True
    queued_payload[0]["execution_requested"] = True
    queued_payload[0]["execution_request_id"] = "existing123"
    payload = persist_approvals(queued_payload)
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "project_all_managed_files", lambda: None)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post(f"/approvals/{PendingApproval.model_validate(payload[0]).approval_id}/yes")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "approved"
    assert "already queued" in body["message"].lower()
    assert payload[0]["order_intent_id"] == PendingApproval.model_validate(payload[0]).order_intent_id
    with session_scope() as session:
        repo = MemoryRepository(session)
        order_intent = repo.get_order_intent(str(payload[0]["order_intent_id"]))
    assert order_intent is not None
    assert order_intent["status"] == "queued"
    mock_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_position_monitor_requires_live_protection(monkeypatch):
    from api.tasks.scheduler import TradingScheduler

    scheduler = TradingScheduler()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    fake_now = datetime(2026, 4, 16, 10, 0)

    with patch("api.tasks.scheduler._now_ist", return_value=fake_now):
        with patch("storage.read_json", return_value={"positions": [{"ticker": "RELIANCE"}]}):
            with patch("execution.trailing_engine.TrailingEngine.run_once", new=AsyncMock()) as mock_run:
                await scheduler._position_monitor()

    mock_run.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_position_monitor_runs_in_live_mode(monkeypatch):
    from api.tasks.scheduler import TradingScheduler

    scheduler = TradingScheduler()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setenv("NEW_ENTRIES_ENABLED", "false")
    monkeypatch.setenv("EXIT_ONLY_MODE", "false")

    fake_now = datetime(2026, 4, 16, 10, 0)

    with patch("api.tasks.scheduler._now_ist", return_value=fake_now):
        with patch("storage.read_json", return_value={"positions": [{"ticker": "RELIANCE"}]}):
            with patch("execution.trailing_engine.TrailingEngine.run_once", new=AsyncMock()) as mock_run:
                await scheduler._position_monitor()

    mock_run.assert_awaited_once()
