"""Phase 7 (P14): flatten + reconcile-ack integration tests.

Exercises the worker-side flatten executor via ``ExecutionCoordinator``:
- flatten-all with no tickers
- flatten single ticker
- DDPI guard on multi-day holdings
- flatten skipped on stale auth
- reconcile-required ack (broker_close / retain)
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from config import cfg
from execution.coordinator import ExecutionCoordinator
from execution.operator_controls import (
    active_block_reasons,
    clear_block_new_entries,
    clear_flatten_request,
    is_flatten_requested,
    read_flatten_request,
    request_flatten,
    set_block_new_entries,
    set_exit_only_mode,
    set_new_entries_enabled,
    set_trading_enabled,
)
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import AccountState, TradingMode


def _ticker() -> str:
    return f"FLT{uuid4().hex[:5]}".upper()


def _seed_position(
    *,
    ticker: str,
    quantity: int,
    opened_days_ago: int = 0,
    oco_gtt_id: str | None = None,
    lifecycle_state: str = "open",
    product: str = "CNC",
) -> None:
    opened_at = datetime.now() - timedelta(days=opened_days_ago)
    state = AccountState(
        cash_inr=100000.0,
        positions=[
            {
                "ticker": ticker,
                "quantity": quantity,
                "entry_price": 1000.0,
                "current_price": 1050.0,
                "stop_price": 980.0,
                "target_price": 1080.0,
                "opened_at": opened_at.isoformat(),
                "entry_order_id": f"entry-{ticker}",
                "product": product,
                "oco_gtt_id": oco_gtt_id,
                "lifecycle_state": lifecycle_state,
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    )
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.replace_account_state(state.model_dump(mode="json"), source="phase7_flatten_test_seed")


def _seed_protection_incident(ticker: str) -> None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_failure_incident(
            incident_id=f"protection:{ticker}",
            status="open",
            severity="critical",
            payload={"ticker": ticker, "detail": "seeded", "at": datetime.now().isoformat()},
            source="phase7_flatten_test_seed",
        )


@pytest.fixture(autouse=True)
def _reset_controls():
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=True, source="test_reset")
        set_new_entries_enabled(enabled=True, source="test_reset")
        set_exit_only_mode(enabled=False, source="test_reset")
        clear_flatten_request(source="test_reset")
        clear_block_new_entries(source="test_reset")
    with session_scope() as session:
        repo = MemoryRepository(session)
        for incident in repo.list_failure_incidents(status="open"):
            incident_id = str(incident.get("incident_id") or "")
            if incident_id.startswith("protection:"):
                repo.upsert_failure_incident(
                    incident_id=incident_id,
                    status="resolved",
                    severity=str(incident.get("severity") or "critical"),
                    payload={"resolved_at": datetime.now().isoformat(), "source": "test_reset"},
                    source="test_reset",
                )
    yield
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=True, source="test_reset")
        clear_flatten_request(source="test_reset")
        clear_block_new_entries(source="test_reset")


def _patch_auth_fresh(monkeypatch, fresh: bool = True):
    monkeypatch.setattr(
        "execution.coordinator.is_session_fresh",
        lambda **kwargs: (fresh, None if fresh else "stale", 1.0 if fresh else 30.0),
    )


def _patch_ddpi_pass(monkeypatch):
    monkeypatch.setattr(
        "ops.phase0_check.check_ddpi_poa",
        lambda: SimpleNamespace(status="PASS", detail="ok", name="ddpi_poa"),
    )


def _patch_ddpi_warn(monkeypatch):
    monkeypatch.setattr(
        "ops.phase0_check.check_ddpi_poa",
        lambda: SimpleNamespace(status="WARN", detail="ddpi_missing", name="ddpi_poa"),
    )


def _build_coordinator() -> ExecutionCoordinator:
    coordinator = ExecutionCoordinator()
    # Override async-heavy collaborators with mocks so the test never hits the
    # live Kite path.
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()
    coordinator.gtt_manager = MagicMock()
    coordinator.gtt_manager.cancel_gtt_async = AsyncMock()
    coordinator.order_tool = MagicMock()
    coordinator.order_tool.place_exit_order_async = AsyncMock(
        return_value={
            "order_id": "exit-abc",
            "status": "filled",
            "average_price": 1055.0,
            "quantity": 10,
            "mode": "paper",
        }
    )
    return coordinator


@pytest.mark.asyncio
async def test_flatten_all_closes_every_open_position(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, opened_days_ago=0)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="operator_flatten")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 1
    coordinator.order_tool.place_exit_order_async.assert_awaited_once()
    call_kwargs = coordinator.order_tool.place_exit_order_async.await_args.kwargs
    assert call_kwargs["ticker"] == ticker
    assert call_kwargs["quantity"] == 10
    assert call_kwargs["product"] == "CNC"
    # Request is cleared after processing.
    assert is_flatten_requested() is False


@pytest.mark.asyncio
async def test_flatten_single_ticker_ignores_others(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    keep = _ticker()
    close = _ticker()

    # Seed two positions.
    state = AccountState(
        cash_inr=100000.0,
        positions=[
            {
                "ticker": keep,
                "quantity": 5,
                "entry_price": 500.0,
                "current_price": 510.0,
                "stop_price": 480.0,
                "target_price": 540.0,
                "opened_at": datetime.now().isoformat(),
                "lifecycle_state": "open",
                "sector": "FIN",
                "pending_corporate_action": {},
            },
            {
                "ticker": close,
                "quantity": 10,
                "entry_price": 1000.0,
                "current_price": 1050.0,
                "stop_price": 980.0,
                "target_price": 1080.0,
                "opened_at": datetime.now().isoformat(),
                "lifecycle_state": "open",
                "sector": "IT",
                "pending_corporate_action": {},
            },
        ],
    )
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.replace_account_state(state.model_dump(mode="json"), source="phase7_flatten_test_seed")

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="single", tickers=[close])

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        await coordinator.process_flatten_request()

    coordinator.order_tool.place_exit_order_async.assert_awaited_once()
    call_kwargs = coordinator.order_tool.place_exit_order_async.await_args.kwargs
    assert call_kwargs["ticker"] == close


@pytest.mark.asyncio
async def test_flatten_blocked_on_stale_auth(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    _patch_auth_fresh(monkeypatch, fresh=False)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="should_block")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 0
    coordinator.order_tool.place_exit_order_async.assert_not_awaited()
    # Request stays pending — operator needs to resolve auth first.
    assert is_flatten_requested() is True


@pytest.mark.asyncio
async def test_paper_mode_flatten_skips_auth_preflight(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.PAPER)
    _patch_auth_fresh(monkeypatch, fresh=False)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="paper_flatten")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 1
    coordinator.order_tool.place_exit_order_async.assert_awaited_once()


@pytest.mark.asyncio
async def test_flatten_blocked_without_trading_enabled(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    with patch("execution.operator_controls._dispatch_control_alert"):
        set_trading_enabled(enabled=False, source="test", reason="stop")
        request_flatten(source="api", reason="test")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 0
    coordinator.order_tool.place_exit_order_async.assert_not_awaited()


@pytest.mark.asyncio
async def test_flatten_blocked_without_ddpi_for_multi_day_holding(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_warn(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, opened_days_ago=3)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="no_ddpi")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        await coordinator.process_flatten_request()

    coordinator.order_tool.place_exit_order_async.assert_not_awaited()
    record = read_flatten_request() or {}
    results = record.get("results") or []
    assert any(item["outcome"].get("status") == "blocked" for item in results)


@pytest.mark.asyncio
async def test_flatten_allowed_with_multi_day_ack(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_warn(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, opened_days_ago=3)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(
            source="api",
            reason="ack_multi_day",
            multi_day_holdings_acked=[ticker],
        )

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 1


@pytest.mark.asyncio
async def test_flatten_allowed_same_day_without_ddpi(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_warn(monkeypatch)
    ticker = _ticker()
    # Opened today — no DDPI requirement for intraday sells.
    _seed_position(ticker=ticker, quantity=10, opened_days_ago=0)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="intraday")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 1


@pytest.mark.asyncio
async def test_flatten_cancels_existing_gtt(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, oco_gtt_id="gtt-xyz-123")

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="test_gtt_cancel")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        await coordinator.process_flatten_request()

    coordinator.gtt_manager.cancel_gtt_async.assert_awaited_once_with("gtt-xyz-123")


@pytest.mark.asyncio
async def test_flatten_rejects_reconcile_required_position(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, lifecycle_state="reconcile_required")

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="blocked_state")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 0
    coordinator.order_tool.place_exit_order_async.assert_not_awaited()
    record = read_flatten_request() or {}
    assert any(
        item["outcome"].get("reason") == "reconcile_required"
        for item in (record.get("results") or [])
    )


@pytest.mark.asyncio
async def test_failed_flatten_does_not_mark_position_closing(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    with patch("execution.operator_controls._dispatch_control_alert"):
        request_flatten(source="api", reason="failed_exit")

    coordinator = _build_coordinator()
    coordinator.order_tool.place_exit_order_async = AsyncMock(
        return_value={
            "status": "failed",
            "reason": "broker_rejected",
            "quantity": 10,
            "mode": "paper",
        }
    )
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 0
    with session_scope() as session:
        repo = MemoryRepository(session)
        rows = [row for row in repo.list_positions() if row["ticker"].upper() == ticker]
    assert len(rows) == 1
    assert rows[0]["state"] == "open"


@pytest.mark.asyncio
async def test_flatten_clears_gtt_recovery_block_when_position_is_manually_exited(monkeypatch):
    _patch_auth_fresh(monkeypatch)
    _patch_ddpi_pass(monkeypatch)
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)
    _seed_protection_incident(ticker)
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_block_new_entries(reason="gtt_recovery_failures", source="seed")
        request_flatten(source="api", reason="manual_exit")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        submitted = await coordinator.process_flatten_request()

    assert submitted == 1
    assert "gtt_recovery_failures" not in active_block_reasons()
    with session_scope() as session:
        repo = MemoryRepository(session)
        open_incidents = repo.list_failure_incidents(status="open")
    assert all(item["incident_id"] != f"protection:{ticker}" for item in open_incidents)


@pytest.mark.asyncio
async def test_reconcile_ack_broker_close_creates_trade_and_deletes_position(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, lifecycle_state="reconcile_required")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await coordinator.resolve_reconcile_required(
            position_id=ticker,
            resolution="broker_close",
            source="test",
        )

    assert result["status"] == "broker_closed"
    # Position should be gone.
    with session_scope() as session:
        repo = MemoryRepository(session)
        remaining = repo.list_positions()
    assert all(p["ticker"].upper() != ticker for p in remaining)


@pytest.mark.asyncio
async def test_reconcile_ack_retain_flips_lifecycle_back_to_open(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.update_position_state(
            position_id=ticker,
            new_state="reconcile_required",
            source="seed",
            detail="seed",
        )

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await coordinator.resolve_reconcile_required(
            position_id=ticker,
            resolution="retain",
            source="test",
        )

    assert result["status"] == "retained"
    with session_scope() as session:
        repo = MemoryRepository(session)
        rows = [p for p in repo.list_positions() if p["ticker"].upper() == ticker]
    assert len(rows) == 1
    assert rows[0]["state"] == "open"


@pytest.mark.asyncio
async def test_reconcile_ack_rejects_position_not_in_reconcile_required_state():
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, lifecycle_state="open")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await coordinator.resolve_reconcile_required(
            position_id=ticker,
            resolution="broker_close",
            source="test",
        )

    assert result["status"] == "rejected"
    assert result["reason"] == "position_not_reconcile_required"


@pytest.mark.asyncio
async def test_reconcile_ack_broker_close_clears_gtt_recovery_block(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10, lifecycle_state="reconcile_required")
    _seed_protection_incident(ticker)
    with patch("execution.operator_controls._dispatch_control_alert"):
        set_block_new_entries(reason="gtt_recovery_failures", source="seed")

    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await coordinator.resolve_reconcile_required(
            position_id=ticker,
            resolution="broker_close",
            source="test",
        )

    assert result["status"] == "broker_closed"
    assert "gtt_recovery_failures" not in active_block_reasons()


@pytest.mark.asyncio
async def test_reconcile_ack_rejects_invalid_resolution():
    coordinator = _build_coordinator()
    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await coordinator.resolve_reconcile_required(
            position_id="RELIANCE",
            resolution="nonsense",
            source="test",
        )
    assert result["status"] == "rejected"
    assert result["reason"] == "invalid_resolution"
