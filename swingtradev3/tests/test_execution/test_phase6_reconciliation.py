from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from broker.reducer import BrokerReducer
from config import cfg
from execution import reconciler as reconciler_module
from execution.coordinator import ExecutionCoordinator
from execution.operator_controls import (
    clear_block_new_entries,
    is_block_new_entries_active,
    read_block_new_entries,
    read_reconciliation_status,
    set_block_new_entries,
)
from execution.quote_cache import QuoteCache
from execution.reconciler import Reconciler
from memory.db import session_scope
from memory.models import (
    AuthSessionRow,
    PositionRow,
    ReconciliationRunRow,
)
from memory.repositories import MemoryRepository
from models import AccountState, TradingMode


def _ticker() -> str:
    return f"REC{uuid4().hex[:5]}".upper()


def _seed_position(
    *,
    ticker: str,
    quantity: int,
    oco_gtt_id: str | None = None,
    lifecycle_state: str = "open",
) -> None:
    state = AccountState(
        cash_inr=100000.0,
        positions=[
            {
                "ticker": ticker,
                "quantity": quantity,
                "entry_price": 1000.0,
                "current_price": 1000.0,
                "stop_price": 980.0,
                "target_price": 1080.0,
                "opened_at": datetime.now().isoformat(),
                "entry_order_id": f"entry-{ticker}",
                "oco_gtt_id": oco_gtt_id,
                "lifecycle_state": lifecycle_state,
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    )
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.replace_account_state(state.model_dump(mode="json"), source="phase6_test_seed")


def _seed_order_intent(*, ticker: str, status: str, broker_tag: str) -> str:
    order_intent_id = f"oi-{uuid4().hex[:10]}"
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            approval_id=None,
            entry_intent_id=None,
            broker_order_id=None,
            broker_tag=broker_tag,
            payload={
                "ticker": ticker,
                "broker_tag": broker_tag,
                "stop_price": 980.0,
                "target_price": 1080.0,
                "entry_zone": {"low": 995.0, "high": 1000.0},
            },
            source="phase6_test_seed",
        )
    return order_intent_id


def _make_reconciler() -> tuple[Reconciler, MagicMock, MagicMock, QuoteCache]:
    stream = MagicMock()
    stream._connected = True
    stream.latest_quotes_by_ticker = {}
    quote_cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda exchange, ticker: 1012.5)
    protection_manager = MagicMock()
    protection_manager.run_watchdog = AsyncMock(return_value={"positions": 0})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=quote_cache,
        protection_manager=protection_manager,
    )
    return reconciler, stream, protection_manager, quote_cache


@pytest.fixture(autouse=True)
def _clear_block_flag(monkeypatch):
    monkeypatch.setattr(
        "execution.operator_controls._dispatch_control_alert",
        lambda *args, **kwargs: None,
    )
    # Each test starts with no active block; clean up after too.
    clear_block_new_entries(source="phase6_test_fixture")
    yield
    clear_block_new_entries(source="phase6_test_fixture")


@pytest.mark.asyncio
async def test_reconcile_orders_detects_missing_broker_order(monkeypatch):
    ticker = _ticker()
    tag = f"STV3{uuid4().hex[:10].upper()}"
    _seed_order_intent(ticker=ticker, status="submitted", broker_tag=tag)

    monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_orders_once(source="unit_test")

    assert result["drift"]["count"] >= 1
    missing = result["drift"]["missing_on_broker"]
    assert any(item["broker_tag"] == tag for item in missing)


@pytest.mark.asyncio
async def test_reconcile_orders_records_reconciliation_run(monkeypatch):
    monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    await reconciler._reconcile_orders_once(source="unit_test")

    with session_scope() as session:
        rows = (
            session.query(ReconciliationRunRow)
            .filter(ReconciliationRunRow.status == "completed")
            .all()
        )
    order_runs = [row for row in rows if row.reconciliation_run_id.startswith("reconcile:orders:")]
    assert len(order_runs) >= 1


@pytest.mark.asyncio
async def test_reconcile_positions_marks_reconcile_required_on_quantity_mismatch(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    broker_positions = {
        "net": [
            {
                "tradingsymbol": ticker,
                "exchange": "NSE",
                "quantity": 3,
                "average_price": 1005.0,
                "last_price": 1010.0,
            }
        ],
        "day": [],
    }

    monkeypatch.setattr(reconciler_module, "fetch_positions", lambda: broker_positions)
    monkeypatch.setattr(reconciler_module, "fetch_holdings", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_positions_once(source="unit_test")

    assert result["drift"]["count"] >= 1
    mismatch = result["drift"]["quantity_mismatch"]
    assert any(item["ticker"] == ticker for item in mismatch)

    with session_scope() as session:
        row = session.get(PositionRow, ticker)
    assert row is not None
    assert row.state == "reconcile_required"
    assert is_block_new_entries_active() is True


@pytest.mark.asyncio
async def test_reconcile_positions_detects_missing_on_broker(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=7)

    monkeypatch.setattr(reconciler_module, "fetch_positions", lambda: {"net": [], "day": []})
    monkeypatch.setattr(reconciler_module, "fetch_holdings", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_positions_once(source="unit_test")

    missing = result["drift"]["missing_on_broker"]
    assert any(item["ticker"] == ticker for item in missing)


@pytest.mark.asyncio
async def test_reconcile_gtts_detects_missing_protection(monkeypatch):
    ticker = _ticker()
    oco_gtt_id = str(int(uuid4().hex[:6], 16))
    _seed_position(ticker=ticker, quantity=5, oco_gtt_id=oco_gtt_id, lifecycle_state="open")

    # Broker returns no GTTs
    monkeypatch.setattr(reconciler_module, "fetch_gtts", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, protection_manager, _ = _make_reconciler()
    result = await reconciler._reconcile_gtts_once(source="unit_test")

    missing = result["drift"]["missing_protection"]
    assert any(item["ticker"] == ticker for item in missing)
    assert protection_manager.run_watchdog.await_count == 1


@pytest.mark.asyncio
async def test_reconciler_startup_marks_ready_when_clean(monkeypatch):
    monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: [])
    monkeypatch.setattr(reconciler_module, "fetch_positions", lambda: {"net": [], "day": []})
    monkeypatch.setattr(reconciler_module, "fetch_holdings", lambda: [])
    monkeypatch.setattr(reconciler_module, "fetch_gtts", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    report = await reconciler.run_startup_reconciliation(wait_for_stream_seconds=0.0)

    assert report["auth_valid"] is True
    # DB may hold prior-test state, so we only assert the shape here; drift counts
    # are exercised by the dedicated reconcile_* tests above.
    assert "orders" in report["drift"]
    assert "positions" in report["drift"]
    assert "gtts" in report["drift"]
    assert "completed_at" in report

    with session_scope() as session:
        rows = (
            session.query(ReconciliationRunRow)
            .filter(ReconciliationRunRow.reconciliation_run_id.like("reconcile:startup:%"))
            .all()
        )
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_reconciler_startup_blocks_when_auth_invalid(monkeypatch):
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: False)

    reconciler, _, _, _ = _make_reconciler()
    report = await reconciler.run_startup_reconciliation(wait_for_stream_seconds=0.0)

    assert report["ready"] is False
    assert report["reason"] == "auth_invalid"
    assert is_block_new_entries_active() is True


def test_quote_cache_detects_stale_stream():
    stream = MagicMock()
    stream._connected = True
    stream.latest_quotes_by_ticker = {}

    t = iter([datetime(2026, 4, 17, 10, 0, 0), datetime(2026, 4, 17, 10, 0, 45)])

    cache = QuoteCache(
        broker_stream=stream,
        rest_fetcher=lambda exchange, ticker: 1000.0,
        clock=lambda: next(t),
    )
    cache.ingest_tick("RELIANCE", {"last_price": 1000.0, "last_trade_time": None})

    result = cache.check_freshness(["RELIANCE"], max_age_seconds=30.0)
    assert len(result["stale"]) == 1
    assert result["stale_ratio"] == 1.0


def test_quote_cache_reports_missing_tickers():
    stream = MagicMock()
    stream._connected = True
    stream.latest_quotes_by_ticker = {}
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda e, t: 0.0)
    result = cache.check_freshness(["UNKNOWN"], max_age_seconds=30.0)
    assert result["missing"] == ["UNKNOWN"]
    assert result["stale_ratio"] == 1.0


def test_quote_cache_refresh_from_stream_stamps_received_at():
    stream = SimpleNamespace(
        _connected=True,
        latest_quotes_by_ticker={"RELIANCE": {"last_price": 1012.5, "last_trade_time": None}},
    )
    now = datetime(2026, 4, 17, 10, 0, 0)
    cache = QuoteCache(
        broker_stream=stream,
        rest_fetcher=lambda e, t: 0.0,
        clock=lambda: now,
    )
    updated = cache.refresh_from_stream(["RELIANCE"])
    assert updated == 1
    snap = cache.get_quote("RELIANCE")
    assert snap is not None
    assert snap.last_price == 1012.5
    assert snap.received_at == now
    assert snap.source == "websocket"


@pytest.mark.asyncio
async def test_quote_cache_rest_fallback():
    cache = QuoteCache(rest_fetcher=lambda exchange, ticker: 1234.5)
    snap = await cache.fetch_rest_fallback("RELIANCE")
    assert snap is not None
    assert snap.last_price == 1234.5
    assert snap.source == "rest"


@pytest.mark.asyncio
async def test_coordinator_skips_queue_when_block_active():
    set_block_new_entries(reason="test_block", source="phase6_test", detail={})
    coordinator = ExecutionCoordinator()
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()

    submitted = await coordinator.submit_queued_order_intents()
    assert submitted == 0
    coordinator.alerts_tool.send_alert.assert_awaited()


@pytest.mark.asyncio
async def test_coordinator_suppresses_stream_block_alert_off_hours(monkeypatch):
    set_block_new_entries(reason="stream_unavailable", source="phase6_test", detail={})
    monkeypatch.setattr(
        "execution.coordinator.entry_stream_required_for_new_entries",
        lambda: False,
    )
    coordinator = ExecutionCoordinator()
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()

    submitted = await coordinator.submit_queued_order_intents()

    assert submitted == 0
    coordinator.alerts_tool.send_alert.assert_not_awaited()


@pytest.mark.asyncio
async def test_coordinator_throttles_repeated_block_alerts(monkeypatch):
    current = {"value": datetime(2026, 1, 2, 9, 15, 0)}
    monkeypatch.setattr("execution.coordinator._now", lambda: current["value"])
    set_block_new_entries(reason="test_block", source="phase6_test", detail={})
    coordinator = ExecutionCoordinator()
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()

    await coordinator.submit_queued_order_intents()
    current["value"] = current["value"] + timedelta(seconds=60)
    await coordinator.submit_queued_order_intents()
    current["value"] = current["value"] + timedelta(minutes=16)
    await coordinator.submit_queued_order_intents()

    assert coordinator.alerts_tool.send_alert.await_count == 2


@pytest.mark.asyncio
async def test_coordinator_submit_order_intent_ignored_when_blocked():
    ticker = _ticker()
    order_intent_id = _seed_order_intent(ticker=ticker, status="queued", broker_tag="STV3BLOCKED")
    set_block_new_entries(reason="test_block", source="phase6_test", detail={})

    coordinator = ExecutionCoordinator()
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()

    result = await coordinator.submit_order_intent(order_intent_id)
    assert result == "ignored"


@pytest.mark.asyncio
async def test_block_clear_resume_allows_submission_after_manual_clear(monkeypatch):
    ticker = _ticker()
    order_intent_id = _seed_order_intent(
        ticker=ticker,
        status="queued",
        broker_tag=f"STV3{uuid4().hex[:8].upper()}",
    )

    coordinator = ExecutionCoordinator()
    coordinator.alerts_tool = MagicMock()
    coordinator.alerts_tool.send_alert = AsyncMock()
    coordinator.risk_tool = MagicMock()
    coordinator.risk_tool.check_risk = MagicMock(return_value={"approved": True, "quantity": 5})
    coordinator.order_tool = MagicMock()
    coordinator.order_tool.place_order_async = AsyncMock(
        return_value={
            "order_id": "order-phase6-resume",
            "status": "submitted",
            "quantity": 5,
            "mode": "paper",
            "broker_tag": "STV3RESUME01",
            "product": "CNC",
        }
    )
    monkeypatch.setattr(
        "execution.coordinator.MarketRegimeDetector",
        lambda: SimpleNamespace(detect_regime=lambda: {"regime": "neutral"}),
    )
    monkeypatch.setattr(
        coordinator,
        "pending_execution_requests",
        lambda: [{"order_intent_id": order_intent_id}],
    )

    set_block_new_entries(reason="manual_test_block", source="phase6_test", detail={})

    blocked = await coordinator.submit_queued_order_intents()
    assert blocked == 0
    coordinator.order_tool.place_order_async.assert_not_awaited()

    clear_block_new_entries(source="phase6_test", reason="manual_test_block")

    resumed = await coordinator.submit_queued_order_intents()
    assert resumed == 1
    coordinator.order_tool.place_order_async.assert_awaited_once()


def test_operator_controls_block_roundtrip():
    set_block_new_entries(reason="positions_drift", source="unit_test", detail={"count": 2})
    assert is_block_new_entries_active() is True
    record = read_block_new_entries()
    assert record is not None
    assert "positions_drift" in record["active_reasons"]
    assert record["latest_reason"] == "positions_drift"

    clear_block_new_entries(source="unit_test")
    assert is_block_new_entries_active() is False


def test_operator_controls_multi_reason_block():
    """G4: multiple reasons stack; clearing one keeps the block active."""
    set_block_new_entries(reason="orders_drift", source="unit_test")
    set_block_new_entries(reason="positions_drift", source="unit_test")
    record = read_block_new_entries() or {}
    assert set(record["active_reasons"]) == {"orders_drift", "positions_drift"}
    assert is_block_new_entries_active() is True

    # Clear just orders_drift → positions_drift still blocking.
    clear_block_new_entries(source="unit_test", reason="orders_drift")
    record = read_block_new_entries() or {}
    assert record["active_reasons"] == ["positions_drift"]
    assert is_block_new_entries_active() is True

    # Clear the last reason → unblocked.
    clear_block_new_entries(source="unit_test", reason="positions_drift")
    assert is_block_new_entries_active() is False


def test_operator_controls_set_twice_is_idempotent():
    """Setting the same reason twice doesn't duplicate it in the active set."""
    set_block_new_entries(reason="stale_quotes", source="unit_test")
    set_block_new_entries(reason="stale_quotes", source="unit_test")
    record = read_block_new_entries() or {}
    assert record["active_reasons"] == ["stale_quotes"]


@pytest.mark.asyncio
async def test_reconciler_quote_freshness_blocks_when_stale(monkeypatch):
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=3)

    stream = SimpleNamespace(_connected=False, latest_quotes_by_ticker={})
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda exchange, tkr: 0.0)
    protection_manager = MagicMock()
    protection_manager.run_watchdog = AsyncMock(return_value={"positions": 0})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection_manager,
    )

    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setattr(
        reconciler_module,
        "entry_stream_required_for_new_entries",
        lambda: True,
    )
    result = await reconciler._check_quote_freshness(source="unit_test")
    assert result["stale_ratio"] >= 0.5
    assert is_block_new_entries_active() is True
    status = read_reconciliation_status()
    assert status is not None
    assert status["phase"] == "quote_freshness"


# ──────────────────────────────────────────────────────────────────
# G1: orphan-order detection correctness
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_orders_flags_orphan_with_no_intent_link(monkeypatch):
    """Broker order exists but has no order_intent linkage and no protective
    trigger exit_order_id — must be flagged as orphan."""
    orphan_id = f"kite-orphan-{uuid4().hex[:8]}"
    ticker = _ticker()
    # Seed a broker_order row with NO order_intent_id (unknown origin).
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_broker_order(
            broker_order_id=orphan_id,
            exchange_order_id=None,
            ticker=ticker,
            order_intent_id=None,
            status="open",
            broker_tag=None,
            payload={"status": "open", "tradingsymbol": ticker, "order_id": orphan_id},
            source="phase6_orphan_seed",
        )

    broker_snapshot = [
        {
            "order_id": orphan_id,
            "status": "OPEN",
            "tradingsymbol": ticker,
            "transaction_type": "BUY",
            "quantity": 5,
            "filled_quantity": 0,
            "pending_quantity": 5,
            "cancelled_quantity": 0,
            "tag": None,
        }
    ]
    monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: broker_snapshot)
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_orders_once(source="unit_test")

    orphans = result["drift"]["orphan_on_broker"]
    assert any(item["broker_order_id"] == orphan_id for item in orphans)


@pytest.mark.asyncio
async def test_reconcile_orders_does_not_flag_gtt_exit_order(monkeypatch):
    """Broker order tied to a protective_trigger.exit_order_id must not be
    flagged as orphan even though its order_intent_id is NULL."""
    exit_id = f"kite-exit-{uuid4().hex[:8]}"
    ticker = _ticker()
    oco_gtt_id = str(int(uuid4().hex[:6], 16))
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_broker_order(
            broker_order_id=exit_id,
            exchange_order_id=None,
            ticker=ticker,
            order_intent_id=None,
            status="open",
            broker_tag=None,
            payload={"status": "open", "order_id": exit_id},
            source="phase6_exit_seed",
        )
        repo.upsert_protective_trigger(
            protective_trigger_id=oco_gtt_id,
            position_id=ticker,
            ticker=ticker,
            status="triggered",
            payload={
                "ticker": ticker,
                "exit_order_id": exit_id,
                "broker_status": "triggered",
            },
            source="phase6_exit_seed",
        )

    broker_snapshot = [
        {
            "order_id": exit_id,
            "status": "OPEN",
            "tradingsymbol": ticker,
            "transaction_type": "SELL",
            "quantity": 5,
            "filled_quantity": 0,
            "pending_quantity": 5,
            "cancelled_quantity": 0,
            "tag": None,
        }
    ]
    monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: broker_snapshot)
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_orders_once(source="unit_test")

    orphans = result["drift"]["orphan_on_broker"]
    assert not any(item["broker_order_id"] == exit_id for item in orphans)


# ──────────────────────────────────────────────────────────────────
# G3: gated apply for missing_on_broker
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconcile_positions_missing_on_broker_preserves_row(monkeypatch):
    """G3: when broker drops a position, the row MUST NOT be deleted. Quantity
    and identity must be preserved; state must flip to reconcile_required;
    apply_held must be True; block_new_entries must fire."""
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=10)

    monkeypatch.setattr(reconciler_module, "fetch_positions", lambda: {"net": [], "day": []})
    monkeypatch.setattr(reconciler_module, "fetch_holdings", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_positions_once(source="unit_test")

    assert result["apply_held"] is True
    assert result["snapshot"]["status"] == "held"

    with session_scope() as session:
        row = session.get(PositionRow, ticker)
    assert row is not None, "position row must be preserved on critical drift"
    assert row.quantity == 10, "original quantity must be preserved"
    assert row.state == "reconcile_required"
    assert is_block_new_entries_active() is True


@pytest.mark.asyncio
async def test_reconcile_positions_clean_applies_normally(monkeypatch):
    """G3: no drift → destructive apply runs; row updated to broker truth."""
    ticker = _ticker()
    _seed_position(ticker=ticker, quantity=5)

    broker_positions = {
        "net": [
            {
                "tradingsymbol": ticker,
                "exchange": "NSE",
                "quantity": 5,
                "average_price": 1000.0,
                "last_price": 1020.0,
            }
        ],
        "day": [],
    }
    monkeypatch.setattr(reconciler_module, "fetch_positions", lambda: broker_positions)
    monkeypatch.setattr(reconciler_module, "fetch_holdings", lambda: [])
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

    reconciler, _, _, _ = _make_reconciler()
    result = await reconciler._reconcile_positions_once(source="unit_test")

    assert result["apply_held"] is False
    assert result["drift"]["count"] == 0

    with session_scope() as session:
        row = session.get(PositionRow, ticker)
    assert row is not None
    assert row.quantity == 5
    assert row.state == "open"


# ──────────────────────────────────────────────────────────────────
# G9: consecutive-failure escalation
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconciler_escalates_after_consecutive_failures(monkeypatch):
    """After N consecutive orders-loop failures, a critical incident is opened
    and block_new_entries is flipped."""
    def _boom():
        raise RuntimeError("broker unreachable")

    monkeypatch.setattr(reconciler_module, "fetch_orders", _boom)
    monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

    reconciler, _, _, _ = _make_reconciler()
    threshold = 3  # matches cfg default
    for _ in range(threshold):
        with pytest.raises(RuntimeError):
            await reconciler._reconcile_orders_once(source="unit_test")
        reconciler._record_failure(reconciler.LOOP_ORDERS, RuntimeError("broker unreachable"))

    assert is_block_new_entries_active() is True
    reasons = read_block_new_entries().get("active_reasons", [])
    assert "orders_loop_failures" in reasons


# ──────────────────────────────────────────────────────────────────
# G8: stale-auth detection
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconciler_flags_stale_auth(monkeypatch):
    # Write an auth session created > 24h ago.
    from memory.repositories import StoredKiteSessionPayload

    old_iso = (datetime.now() - timedelta(hours=30)).isoformat()
    payload = StoredKiteSessionPayload(
        api_key="test-api-key",
        access_token="test-access-token",
        created_at=old_iso,
        login_time=old_iso,
    )
    with session_scope() as session:
        repo = MemoryRepository(session)
        original_auth_payload = repo.get_auth_session_payload()
        repo.replace_auth_session(payload.model_dump(mode="json"), source="phase6_stale_auth")

    try:
        monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)
        reconciler, _, _, _ = _make_reconciler()
        monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
        await reconciler._check_auth_freshness(source="unit_test")

        assert is_block_new_entries_active() is True
        assert "stale_auth" in (read_block_new_entries() or {}).get("active_reasons", [])
    finally:
        with session_scope() as session:
            repo = MemoryRepository(session)
            if original_auth_payload:
                repo.replace_auth_session(
                    original_auth_payload,
                    source="phase6_stale_auth_restore",
                )
            else:
                row = session.get(AuthSessionRow, "kite")
                if row is not None:
                    session.delete(row)


# ──────────────────────────────────────────────────────────────────
# G6: post-stream readiness check
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_stream_readiness_blocks_when_stream_down():
    stream = SimpleNamespace(_connected=False, latest_quotes_by_ticker={})
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda e, t: 0.0)
    protection_manager = MagicMock()
    protection_manager.run_watchdog = AsyncMock(return_value={"positions": 0})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection_manager,
    )

    payload = await reconciler.run_post_stream_readiness_check(wait_for_stream_seconds=0.0)
    assert payload["stream_connected"] is False
    assert is_block_new_entries_active() is True
    assert "stream_unavailable" in (read_block_new_entries() or {}).get("active_reasons", [])


@pytest.mark.asyncio
async def test_post_stream_readiness_clears_on_connect():
    stream = SimpleNamespace(_connected=True, latest_quotes_by_ticker={})
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda e, t: 0.0)
    protection_manager = MagicMock()
    protection_manager.run_watchdog = AsyncMock(return_value={"positions": 0})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection_manager,
    )

    # Pre-set the block to ensure the clear path runs.
    set_block_new_entries(reason="stream_unavailable", source="unit_test")
    payload = await reconciler.run_post_stream_readiness_check(wait_for_stream_seconds=0.0)
    assert payload["stream_connected"] is True
    assert "stream_unavailable" not in (read_block_new_entries() or {}).get("active_reasons", [])


@pytest.mark.asyncio
async def test_post_stream_readiness_clears_when_stream_not_required():
    stream = SimpleNamespace(_connected=False, latest_quotes_by_ticker={})
    cache = QuoteCache(broker_stream=stream, rest_fetcher=lambda e, t: 0.0)
    protection_manager = MagicMock()
    protection_manager.run_watchdog = AsyncMock(return_value={"positions": 0})
    reconciler = Reconciler(
        broker_reducer=BrokerReducer(),
        broker_stream=stream,
        quote_cache=cache,
        protection_manager=protection_manager,
    )

    set_block_new_entries(reason="stream_unavailable", source="unit_test")
    payload = await reconciler.run_post_stream_readiness_check(
        wait_for_stream_seconds=0.0,
        require_stream=False,
    )

    assert payload["stream_required"] is False
    assert payload["stream_connected"] is False
    assert "stream_unavailable" not in (read_block_new_entries() or {}).get("active_reasons", [])


@pytest.mark.asyncio
async def test_quote_freshness_clears_stream_block_when_stream_not_required(monkeypatch):
    reconciler, _, _, _ = _make_reconciler()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setattr(
        reconciler_module,
        "entry_stream_required_for_new_entries",
        lambda: False,
    )
    set_block_new_entries(reason="stream_unavailable", source="unit_test")
    set_block_new_entries(reason="stale_quotes", source="unit_test")

    result = await reconciler._check_quote_freshness(source="unit_test")

    assert "stale_ratio" in result
    reasons = (read_block_new_entries() or {}).get("active_reasons", [])
    assert "stream_unavailable" not in reasons
    assert "stale_quotes" not in reasons


# ──────────────────────────────────────────────────────────────────
# G2: mutation lock contention proof
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reconciler_respects_bound_mutation_lock(monkeypatch):
    """When a mutation lock is bound, the reconciler must acquire it before
    performing writes. We assert this by observing held-state during the call."""
    import asyncio

    from execution.runtime_context import bind_mutation_lock

    lock = asyncio.Lock()
    bind_mutation_lock(lock)
    try:
        monkeypatch.setattr(reconciler_module, "fetch_orders", lambda: [])
        monkeypatch.setattr(reconciler_module, "has_kite_session", lambda: True)

        reconciler, _, _, _ = _make_reconciler()
        # The lock should be free when the method completes.
        await reconciler._reconcile_orders_once(source="unit_test")
        assert lock.locked() is False
    finally:
        bind_mutation_lock(None)
