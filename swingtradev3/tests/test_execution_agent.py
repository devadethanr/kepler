"""Tests for execution_agent.py — Phase 3 execution operations.

Tests cover: startup sequence, approval lifecycle, PAUSE handling,
trailing stops, GTT health check, entry validity, daily snapshot.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path

from swingtradev3.agents.execution_agent import ExecutionAgent
from swingtradev3.models import AccountState, PositionState
from swingtradev3.paper.gtt_simulator import GTTSimulator
from swingtradev3.paths import CONTEXT_DIR, PROJECT_ROOT
from swingtradev3.storage import read_json, write_json
from swingtradev3.tools.execution.gtt_manager import GTTManager
from swingtradev3.tools.execution.order_execution import OrderExecutionTool


def _make_position(ticker: str = "INFY", **kwargs) -> PositionState:
    defaults = dict(
        ticker=ticker,
        quantity=10,
        entry_price=100.0,
        current_price=100.0,
        stop_price=95.0,
        target_price=115.0,
        opened_at=datetime.utcnow(),
        entry_order_id="ord-1",
        stop_gtt_id="gtt-1",
    )
    defaults.update(kwargs)
    return PositionState(**defaults)


def _make_state(**kwargs) -> AccountState:
    defaults = dict(cash_inr=20000.0)
    defaults.update(kwargs)
    return AccountState(**defaults)


def _ensure_clean_context() -> None:
    """Ensure context files are clean before each test."""
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(CONTEXT_DIR / "state.json", _make_state().model_dump(mode="json"))
    write_json(CONTEXT_DIR / "pending_approvals.json", [])
    write_json(CONTEXT_DIR / "trades.json", [])
    write_json(CONTEXT_DIR / "trade_observations.json", [])
    # Remove PAUSE file if present
    pause_file = PROJECT_ROOT / "PAUSE"
    if pause_file.exists():
        pause_file.unlink()


# -- PAUSE handling -----------------------------------------------------------


def test_pause_file_blocks_polling() -> None:
    """PAUSE file present → poll returns immediately without processing."""
    _ensure_clean_context()
    pause_file = PROJECT_ROOT / "PAUSE"
    try:
        pause_file.touch()
        agent = ExecutionAgent()
        state = asyncio.run(agent.poll())
        assert state is not None
    finally:
        if pause_file.exists():
            pause_file.unlink()


def test_no_pause_allows_polling() -> None:
    """Without PAUSE file, poll proceeds normally."""
    _ensure_clean_context()
    agent = ExecutionAgent()
    state = asyncio.run(agent.poll())
    assert state is not None
    assert isinstance(state, AccountState)


# -- Entry validity -----------------------------------------------------------


def test_entry_still_valid_within_zone() -> None:
    agent = ExecutionAgent()
    approval = {"entry_zone": {"high": 100.0}}
    # Price at exactly the zone top — valid
    assert agent._entry_still_valid(approval, 100.0) is True
    # Price just above zone but within 3% — valid
    assert agent._entry_still_valid(approval, 102.5) is True


def test_entry_expired_above_zone() -> None:
    agent = ExecutionAgent()
    approval = {"entry_zone": {"high": 100.0}}
    # Price 4% above zone — invalid (>3% default)
    assert agent._entry_still_valid(approval, 104.0) is False


# -- Approval lifecycle -------------------------------------------------------


def test_approval_expiry() -> None:
    """Stale approvals should be expired automatically."""
    _ensure_clean_context()
    now = datetime.utcnow()
    stale_approval = {
        "ticker": "SBIN",
        "score": 8.0,
        "setup_type": "breakout",
        "entry_zone": {"low": 790.0, "high": 800.0},
        "stop_price": 770.0,
        "target_price": 850.0,
        "holding_days_expected": 10,
        "confidence_reasoning": "Strong setup",
        "risk_flags": [],
        "approved": None,
        "created_at": (now - timedelta(hours=20)).isoformat(),
        "expires_at": (now - timedelta(hours=4)).isoformat(),  # already expired
    }
    write_json(CONTEXT_DIR / "pending_approvals.json", [stale_approval])

    agent = ExecutionAgent()
    state = asyncio.run(agent.poll())
    # The expired approval should have been removed
    remaining = read_json(CONTEXT_DIR / "pending_approvals.json", [])
    # TelegramHandler.expire_stale() removes expired items
    assert len(remaining) == 0


# -- Trailing stops -----------------------------------------------------------


def test_trailing_stop_breakeven() -> None:
    """Position +5% → stop moves to breakeven (entry price)."""
    _ensure_clean_context()
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 95.0, 115.0)
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        positions=[
            _make_position(
                "INFY",
                entry_price=100.0,
                stop_price=95.0,
                current_price=105.5,  # +5.5% → triggers breakeven trail
                stop_gtt_id="gtt-1",
            )
        ]
    )
    write_json(CONTEXT_DIR / "state.json", state.model_dump(mode="json"))

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    asyncio.run(agent._check_trailing(state))

    # Stop should have moved to entry price (100.0) from 95.0
    assert state.positions[0].stop_price == 100.0
    # Simulator GTT should also be updated
    gtt = simulator.get("gtt-1")
    assert gtt is not None
    assert gtt.stop_price == 100.0


def test_trailing_stop_locked_profit() -> None:
    """Position +10% → stop moves to entry + locked_profit_pct (5%)."""
    _ensure_clean_context()
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 100.0, 115.0)  # already at breakeven
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        positions=[
            _make_position(
                "INFY",
                entry_price=100.0,
                stop_price=100.0,  # already at breakeven
                current_price=111.0,  # +11% → triggers locked profit trail
                stop_gtt_id="gtt-1",
            )
        ]
    )

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    asyncio.run(agent._check_trailing(state))

    # Stop should be at entry + 5% = 105.0
    assert state.positions[0].stop_price == 105.0


def test_trailing_stop_never_widens() -> None:
    """Stop should only tighten, never widen."""
    _ensure_clean_context()
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 108.0, 115.0)
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        positions=[
            _make_position(
                "INFY",
                entry_price=100.0,
                stop_price=108.0,  # already tighter than breakeven
                current_price=105.5,  # +5.5% would set to 100.0 — but 108 > 100
                stop_gtt_id="gtt-1",
            )
        ]
    )

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    asyncio.run(agent._check_trailing(state))

    # Stop should remain at 108.0 (not reduced to 100.0)
    assert state.positions[0].stop_price == 108.0


# -- GTT trigger processing --------------------------------------------------


def test_gtt_stop_trigger_closes_position() -> None:
    """Stop-loss GTT triggers → position closed, trade recorded."""
    _ensure_clean_context()
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 95.0, 115.0)
    # Simulate stop hit
    simulator.process_candle("gtt-1", candle_low=94.0, candle_high=96.0)
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        cash_inr=18000.0,
        positions=[
            _make_position("INFY", stop_gtt_id="gtt-1", quantity=10, entry_price=100.0)
        ],
    )

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    asyncio.run(agent._process_gtt_triggers(state))

    # Position should be removed
    assert len(state.positions) == 0
    # Cash should increase by exit_price * quantity
    assert state.cash_inr > 18000.0
    # Trade should be recorded
    trades = read_json(CONTEXT_DIR / "trades.json", [])
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "stop_loss"


def test_gtt_target_trigger_closes_position() -> None:
    """Target GTT triggers → position closed, trade recorded."""
    _ensure_clean_context()
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 95.0, 115.0)
    # Simulate target hit
    simulator.process_candle("gtt-1", candle_low=110.0, candle_high=116.0)
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        cash_inr=18000.0,
        positions=[
            _make_position("INFY", stop_gtt_id="gtt-1", quantity=10, entry_price=100.0)
        ],
    )

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    asyncio.run(agent._process_gtt_triggers(state))

    assert len(state.positions) == 0
    trades = read_json(CONTEXT_DIR / "trades.json", [])
    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "target"
    assert trades[0]["pnl_abs"] > 0


# -- Daily snapshot -----------------------------------------------------------


def test_daily_snapshot_created() -> None:
    """Daily snapshot file should be created after poll."""
    _ensure_clean_context()
    from datetime import date

    snapshot_path = CONTEXT_DIR / "daily" / f"{date.today().isoformat()}.json"
    if snapshot_path.exists():
        snapshot_path.unlink()

    agent = ExecutionAgent()
    state = _make_state()
    agent._save_daily_snapshot(state)

    assert snapshot_path.exists()
    data = read_json(snapshot_path, {})
    assert data["cash_inr"] == 20000.0


# -- GTT health check --------------------------------------------------------


def test_gtt_health_check_alerts_on_missing() -> None:
    """Missing GTT during poll → alert (no auto-replace)."""
    _ensure_clean_context()
    simulator = GTTSimulator()  # empty — no GTTs
    gtt_mgr = GTTManager(simulator=simulator)

    state = _make_state(
        positions=[_make_position("INFY", stop_gtt_id="gtt-missing")]
    )

    agent = ExecutionAgent(gtt_manager=gtt_mgr)
    # Should not raise, just alert
    asyncio.run(agent._check_gtt_health(state))
    # Position should still exist (not removed during health check)
    assert len(state.positions) == 1


# -- Startup ------------------------------------------------------------------


def test_startup_runs_without_error() -> None:
    """Startup sequence should complete without raising."""
    _ensure_clean_context()
    agent = ExecutionAgent()
    state = asyncio.run(agent.startup())
    assert isinstance(state, AccountState)


# -- Circuit limit check ------------------------------------------------------


def test_circuit_limit_check_no_crash() -> None:
    """Circuit limit check should not crash on normal prices."""
    _ensure_clean_context()
    state = _make_state(
        positions=[_make_position("INFY", entry_price=100.0, current_price=105.0)]
    )
    agent = ExecutionAgent()
    asyncio.run(agent._check_circuit_limits(state))
    # Should complete without error
    assert True
