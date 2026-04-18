from __future__ import annotations

from copy import deepcopy
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from broker.reducer import BrokerReducer
from config import cfg
from execution.bootstrap import WorkerRuntime
from memory.db import session_scope
from memory.models import BrokerOrderRow, ProtectiveTriggerRow
from models import TradingMode
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"


def _empty_state() -> dict[str, object]:
    return {
        "cash_inr": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "drawdown_pct": 0.0,
        "weekly_loss_pct": 0.0,
        "consecutive_losses": 0,
        "positions": [],
    }


def test_restart_recovery_reconstructs_orders_positions_and_gtt_from_broker_truth():
    reducer = BrokerReducer()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    suffix = uuid.uuid4().hex[:8]
    position_ticker = f"INF{suffix[:2]}".upper()
    gtt_id = int(suffix[:6], 16)

    stale_state = _empty_state()
    stale_state["positions"] = [
        {
            "ticker": "SBIN",
            "quantity": 1,
            "entry_price": 500.0,
            "current_price": 505.0,
            "stop_price": 480.0,
            "target_price": 540.0,
            "opened_at": "2026-04-10T09:15:00",
            "entry_order_id": "stale-order",
            "oco_gtt_id": None,
            "pending_corporate_action": {},
        }
    ]
    orders = [
        {
            "order_id": f"open-order-{suffix}",
            "exchange_order_id": f"exchange-order-{suffix}",
            "status": "OPEN",
            "tradingsymbol": "RELIANCE",
            "exchange": "NSE",
            "transaction_type": "BUY",
            "quantity": 5,
            "filled_quantity": 0,
            "pending_quantity": 5,
            "cancelled_quantity": 0,
            "average_price": 0,
            "price": 2500.0,
            "tag": f"STV3REL{suffix}".upper()[:20],
            "order_timestamp": "2026-04-17 09:15:00",
            "exchange_update_timestamp": "2026-04-17 09:15:00",
        }
    ]
    gtts = [
        {
            "id": gtt_id,
            "status": "active",
            "condition": {
                "exchange": "NSE",
                "tradingsymbol": position_ticker,
                "trigger_values": [1400.0, 1600.0],
            },
            "orders": [
                {"tradingsymbol": position_ticker, "result": None},
                {"tradingsymbol": position_ticker, "result": None},
            ],
        }
    ]
    positions = {
        "net": [
            {
                "tradingsymbol": position_ticker,
                "quantity": 2,
                "average_price": 1500.0,
                "last_price": 1510.0,
            }
        ]
    }

    try:
        write_json(STATE_PATH, stale_state)
        with patch("broker.reducer.fetch_orders", return_value=orders):
            with patch("broker.reducer.fetch_gtts", return_value=gtts):
                with patch("broker.reducer.fetch_positions", return_value=positions):
                    with patch("broker.reducer.fetch_holdings", return_value=[]):
                        result = reducer.sync_from_broker(source="restart_recovery_test")
                        write_json(STATE_PATH, _empty_state())
                        replay = BrokerReducer().sync_from_broker(source="restart_recovery_replay")

        assert set(result["tracked_tickers"]) == {position_ticker, "RELIANCE"}
        assert set(replay["tracked_tickers"]) == {position_ticker, "RELIANCE"}
        projected = read_json(STATE_PATH, {})
        assert [item["ticker"] for item in projected["positions"]] == [position_ticker]
        assert projected["positions"][0]["oco_gtt_id"] == str(gtt_id)
        assert projected["positions"][0]["lifecycle_state"] == "open"

        with session_scope() as session:
            order_row = session.get(BrokerOrderRow, f"open-order-{suffix}")
            trigger_row = session.get(ProtectiveTriggerRow, str(gtt_id))
        assert order_row is not None
        assert order_row.status == "open"
        assert trigger_row is not None
        assert trigger_row.status == "active"
    finally:
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_worker_startup_runs_broker_sync_and_sets_quote_tracking(monkeypatch):
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    runtime = WorkerRuntime()

    async def wait_for_stop():
        await runtime._stop_event.wait()

    runtime._approval_loop = wait_for_stop  # type: ignore[method-assign]
    runtime._operator_control_loop = wait_for_stop  # type: ignore[method-assign]
    runtime._heartbeat_loop = wait_for_stop  # type: ignore[method-assign]
    runtime._broker_sync_loop = wait_for_stop  # type: ignore[method-assign]
    runtime._broker_reducer = MagicMock(
        sync_from_broker=MagicMock(return_value={"tracked_tickers": ["INFY", "RELIANCE"]})
    )
    runtime._broker_stream = MagicMock()
    runtime._write_status = AsyncMock()

    fake_lease = MagicMock()

    with patch("execution.bootstrap.initialize_memory_layer") as mock_init:
        with patch("execution.bootstrap.WorkerLease.acquire", return_value=fake_lease):
            with patch("execution.bootstrap.has_kite_session", return_value=True):
                with patch("execution.bootstrap.scheduler.start", new=AsyncMock()):
                    with patch("execution.bootstrap.scheduler.stop", new=AsyncMock()):
                        await runtime.start()
                        await runtime.stop()

    mock_init.assert_called_once()
    runtime._broker_reducer.sync_from_broker.assert_called_once_with(
        source="worker_startup_snapshot"
    )
    runtime._broker_stream.set_tracked_tickers.assert_called_once_with(
        ["INFY", "RELIANCE"],
        exchange=cfg.trading.exchange,
    )
    runtime._broker_stream.ensure_running.assert_called_once()
    runtime._broker_stream.stop.assert_called_once()
    fake_lease.release.assert_called_once()
