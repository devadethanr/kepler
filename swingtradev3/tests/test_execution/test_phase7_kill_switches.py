"""Phase 7 (P14): automatic kill-switch tests.

Covers the four new / newly wired auto kill switches:
- P3 daily_loss_limit
- P5 order_submission_failures
- P6 gtt_recovery_failures
- P7 broker_disconnected

Plus P4 per-order auth preflight.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from broker.reducer import BrokerReducer
from config import cfg
from execution import reconciler as reconciler_module
from execution.failure_tracker import FailureCounter
from execution.operator_controls import (
    active_block_reasons,
    clear_block_new_entries,
    is_exit_only_mode,
    set_block_new_entries,
    set_exit_only_mode,
)
from execution.quote_cache import QuoteCache
from execution.reconciler import Reconciler
from memory.db import session_scope
from memory.repository import MemoryRepository
from models import TradingMode


@pytest.fixture(autouse=True)
def _reset_controls():
    with session_scope() as session:
        repo = MemoryRepository(session)
        existing_open_incidents = {
            str(item.get("incident_id") or "")
            for item in repo.list_failure_incidents(status="open")
        }
    with patch("execution.operator_controls._dispatch_control_alert"):
        clear_block_new_entries(source="test_reset_p7ks")
        set_exit_only_mode(enabled=False, source="test_reset_p7ks")
    yield
    with patch("execution.operator_controls._dispatch_control_alert"):
        clear_block_new_entries(source="test_reset_p7ks")
        set_exit_only_mode(enabled=False, source="test_reset_p7ks")
    with session_scope() as session:
        repo = MemoryRepository(session)
        for incident in repo.list_failure_incidents(status="open"):
            incident_id = str(incident.get("incident_id") or "")
            if incident_id in existing_open_incidents:
                continue
            repo.upsert_failure_incident(
                incident_id=incident_id,
                status="resolved",
                severity=str(incident.get("severity") or "warning"),
                payload={"resolved_at": datetime.now().isoformat(), "source": "test_reset_p7ks"},
                source="test_reset_p7ks",
            )


def _make_reconciler() -> Reconciler:
    stream = MagicMock()
    stream._connected = True
    stream._reconnect_exhausted = False
    stream.connection_status.return_value = {
        "connected": True,
        "reconnect_exhausted": False,
        "last_connect_at": None,
        "last_disconnect_at": None,
    }
    stream.latest_quotes_by_ticker = {}
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda exchange, ticker: 1000.0)
    protection = MagicMock()
    protection.run_watchdog = AsyncMock(return_value={})
    return Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection,
    )


# ---------------------------------------------------------------------------
# FailureCounter (shared helper)
# ---------------------------------------------------------------------------


def test_failure_counter_trips_on_nth_failure():
    counter = FailureCounter(threshold=3)
    assert counter.record_failure() is False
    assert counter.record_failure() is False
    assert counter.record_failure() is True
    # Further failures while tripped return False (no repeat alert).
    assert counter.record_failure() is False
    assert counter.is_tripped() is True


def test_failure_counter_success_resets():
    counter = FailureCounter(threshold=2)
    counter.record_failure()
    counter.record_failure()
    assert counter.is_tripped() is True
    assert counter.record_success() is True
    assert counter.count == 0
    assert counter.is_tripped() is False


# ---------------------------------------------------------------------------
# P7 — broker disconnect runtime loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broker_disconnect_trips_after_grace(monkeypatch):
    reconciler = _make_reconciler()
    stream = reconciler._stream
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

    # Simulate "disconnected 60 seconds ago" with default grace of 30s.
    past = datetime.now() - timedelta(seconds=60)
    reconciler._disconnect_since = past
    stream.connection_status.return_value = {
        "connected": False,
        "reconnect_exhausted": False,
        "last_connect_at": None,
        "last_disconnect_at": past.isoformat(),
    }

    with patch("execution.operator_controls._dispatch_control_alert"):
        result = await reconciler._check_broker_connection(source="unit")

    assert result["status"] == "disconnected"
    assert "broker_disconnected" in active_block_reasons()


@pytest.mark.asyncio
async def test_broker_disconnect_exhausted_trips_immediately():
    reconciler = _make_reconciler()
    stream = reconciler._stream
    with patch.object(cfg.trading, "mode", TradingMode.LIVE):
        stream.connection_status.return_value = {
            "connected": False,
            "reconnect_exhausted": True,
            "last_connect_at": None,
            "last_disconnect_at": datetime.now().isoformat(),
        }

        with patch("execution.operator_controls._dispatch_control_alert"):
            result = await reconciler._check_broker_connection(source="unit")

    assert result["status"] == "disconnected"
    assert "broker_disconnected" in active_block_reasons()


@pytest.mark.asyncio
async def test_broker_reconnect_clears_block():
    reconciler = _make_reconciler()
    stream = reconciler._stream

    with patch.object(cfg.trading, "mode", TradingMode.LIVE):
        # First trip
        stream.connection_status.return_value = {
            "connected": False,
            "reconnect_exhausted": True,
            "last_connect_at": None,
            "last_disconnect_at": datetime.now().isoformat(),
        }
        with patch("execution.operator_controls._dispatch_control_alert"):
            await reconciler._check_broker_connection(source="unit")
        assert "broker_disconnected" in active_block_reasons()

        # Recovery
        stream.connection_status.return_value = {
            "connected": True,
            "reconnect_exhausted": False,
            "last_connect_at": datetime.now().isoformat(),
            "last_disconnect_at": None,
        }
        with patch("execution.operator_controls._dispatch_control_alert"):
            result = await reconciler._check_broker_connection(source="unit")

    assert result["status"] == "connected"
    assert "broker_disconnected" not in active_block_reasons()


@pytest.mark.asyncio
async def test_broker_disconnect_within_grace_does_not_trip():
    reconciler = _make_reconciler()
    stream = reconciler._stream

    # Just went down 5 seconds ago, grace is 30.
    reconciler._disconnect_since = datetime.now() - timedelta(seconds=5)
    with patch.object(cfg.trading, "mode", TradingMode.LIVE):
        stream.connection_status.return_value = {
            "connected": False,
            "reconnect_exhausted": False,
            "last_connect_at": None,
            "last_disconnect_at": datetime.now().isoformat(),
        }

        with patch("execution.operator_controls._dispatch_control_alert"):
            result = await reconciler._check_broker_connection(source="unit")

    assert result["status"] == "in_grace"
    assert "broker_disconnected" not in active_block_reasons()


@pytest.mark.asyncio
async def test_quote_freshness_is_observability_only_in_paper(monkeypatch):
    ticker = "RELIANCE"
    stream = MagicMock()
    stream._connected = False
    stream.latest_quotes_by_ticker = {}
    stream.connection_status.return_value = {
        "connected": False,
        "reconnect_exhausted": False,
        "last_connect_at": None,
        "last_disconnect_at": None,
    }
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda exchange, tkr: 0.0)
    protection = MagicMock()
    protection.run_watchdog = AsyncMock(return_value={})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection,
    )

    with patch.object(cfg.trading, "mode", TradingMode.PAPER):
        monkeypatch.setattr(
            "memory.repository.MemoryRepository.list_positions",
            lambda self: [{"ticker": ticker, "state": "open"}],
        )
        result = await reconciler._check_quote_freshness(source="unit")

    assert result["stale_ratio"] >= 1.0
    assert "stale_quotes" not in active_block_reasons()


@pytest.mark.asyncio
async def test_auth_freshness_does_not_block_in_paper(monkeypatch):
    reconciler = _make_reconciler()
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)
    monkeypatch.setattr(
        "execution.auth_preflight.is_session_fresh",
        lambda max_age_hours=None: (False, "stale", 30.0),
    )

    with patch.object(cfg.trading, "mode", TradingMode.PAPER):
        await reconciler._check_auth_freshness(source="unit")

    assert "stale_auth" not in active_block_reasons()


@pytest.mark.asyncio
async def test_scheduler_auth_preflight_does_not_block_in_paper(monkeypatch):
    from api.tasks.scheduler import TradingScheduler

    set_block_new_entries(reason="stale_auth", source="test_seed")
    monkeypatch.setattr(
        "execution.auth_preflight.is_session_fresh",
        lambda: (False, "stale", 30.0),
    )

    with patch.object(cfg.trading, "mode", TradingMode.PAPER):
        await TradingScheduler()._auth_preflight()

    assert "stale_auth" not in active_block_reasons()


@pytest.mark.asyncio
async def test_non_live_relaxation_clears_live_broker_latches():
    reconciler = _make_reconciler()
    with patch("execution.operator_controls._dispatch_control_alert"):
        reconciler._open_incident(
            incident_id="broker_disconnected",
            severity="critical",
            payload={"at": datetime.now(timezone.utc).isoformat()},
        )
        set_block_new_entries(reason="broker_disconnected", source="test_seed")

    with patch.object(cfg.trading, "mode", TradingMode.PAPER):
        await reconciler.relax_runtime_guards_for_non_live(source="unit")

    assert "broker_disconnected" not in active_block_reasons()


# ---------------------------------------------------------------------------
# P3 — daily loss kill switch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_daily_loss_breached_flips_block_and_exit_only(monkeypatch):
    reconciler = _make_reconciler()

    snapshot = {
        "breached": True,
        "realized_pnl": -2000.0,
        "equity": 50000.0,
        "loss_pct": 0.04,
        "threshold_pct": 0.025,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_to_thread(func, *args, **kwargs):
        return snapshot

    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)

    with patch("execution.operator_controls._dispatch_control_alert"):
        await reconciler._check_daily_loss(source="unit")

    assert "daily_loss_limit" in active_block_reasons()
    assert is_exit_only_mode() is True


@pytest.mark.asyncio
async def test_daily_loss_clean_does_not_trip(monkeypatch):
    reconciler = _make_reconciler()
    snapshot = {
        "breached": False,
        "realized_pnl": 0.0,
        "equity": 50000.0,
        "loss_pct": 0.0,
        "threshold_pct": 0.025,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_to_thread(func, *args, **kwargs):
        return snapshot

    monkeypatch.setattr("asyncio.to_thread", fake_to_thread)

    with patch("execution.operator_controls._dispatch_control_alert"):
        await reconciler._check_daily_loss(source="unit")

    assert "daily_loss_limit" not in active_block_reasons()


# ---------------------------------------------------------------------------
# P4 — per-order auth preflight (coordinator path)
# ---------------------------------------------------------------------------


def test_auth_preflight_returns_stale_when_token_too_old(monkeypatch):
    from execution.auth_preflight import is_session_fresh

    monkeypatch.setattr("execution.auth_preflight.has_kite_session", lambda: True)
    monkeypatch.setattr(
        "execution.auth_preflight.read_auth_session_age_hours",
        lambda: 30.0,
    )

    fresh, reason, age = is_session_fresh()
    assert fresh is False
    assert reason == "stale"
    assert age == 30.0


def test_auth_preflight_returns_fresh_when_recent(monkeypatch):
    from execution.auth_preflight import is_session_fresh

    monkeypatch.setattr("execution.auth_preflight.has_kite_session", lambda: True)
    monkeypatch.setattr(
        "execution.auth_preflight.read_auth_session_age_hours",
        lambda: 2.0,
    )

    fresh, reason, age = is_session_fresh()
    assert fresh is True
    assert reason is None
    assert age == 2.0


def test_auth_preflight_missing_session_fails_closed(monkeypatch):
    from execution.auth_preflight import is_session_fresh

    monkeypatch.setattr("execution.auth_preflight.has_kite_session", lambda: False)

    fresh, reason, age = is_session_fresh()
    assert fresh is False
    assert reason == "missing"
    assert age is None


def test_auth_preflight_age_handles_timezone_aware_created_at(monkeypatch):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from execution.auth_preflight import read_auth_session_age_hours

    ist = ZoneInfo("Asia/Kolkata")
    monkeypatch.setattr(
        "execution.auth_preflight._now",
        lambda: datetime(2026, 4, 22, 10, 0, 0, tzinfo=ist),
    )
    monkeypatch.setattr(
        "memory.repository.MemoryRepository.get_auth_session_payload",
        lambda _self: {"created_at": "2026-04-22T08:00:00+05:30"},
    )

    age_hours = read_auth_session_age_hours()

    assert age_hours is not None
    assert round(age_hours, 2) == 2.0


# ---------------------------------------------------------------------------
# Daily-loss pure helper
# ---------------------------------------------------------------------------


def test_daily_loss_exceeded_pure_helper_breaches():
    from risk.daily_loss import daily_loss_exceeded

    breached, loss_pct = daily_loss_exceeded(equity=100000.0, realized_pnl=-3000.0)
    assert breached is True
    assert round(loss_pct, 4) == 0.03


def test_daily_loss_exceeded_pure_helper_within_limit():
    from risk.daily_loss import daily_loss_exceeded

    breached, loss_pct = daily_loss_exceeded(equity=100000.0, realized_pnl=-1000.0)
    assert breached is False
    assert round(loss_pct, 4) == 0.01


def test_daily_loss_exceeded_pure_helper_gains_are_zero_loss():
    from risk.daily_loss import daily_loss_exceeded

    breached, loss_pct = daily_loss_exceeded(equity=100000.0, realized_pnl=5000.0)
    assert breached is False
    assert loss_pct == 0.0


def test_daily_loss_exceeded_zero_equity_returns_false():
    from risk.daily_loss import daily_loss_exceeded

    breached, loss_pct = daily_loss_exceeded(equity=0.0, realized_pnl=-1000.0)
    assert breached is False
    assert loss_pct == 0.0
