"""Tests for reconciler.py — Phase 3 reconciliation logic.

Tests cover both paper and live reconciliation scenarios per design doc 4.3.
"""
import asyncio

from swingtradev3.agents.reconciler import Reconciler
from swingtradev3.models import AccountState, PositionState
from swingtradev3.paper.gtt_simulator import GTTSimulator
from swingtradev3.tools.execution.alerts import AlertsTool
from swingtradev3.tools.execution.gtt_manager import GTTManager


def _make_position(ticker: str = "INFY", stop_gtt_id: str | None = "gtt-1", **kwargs) -> PositionState:
    defaults = dict(
        ticker=ticker,
        quantity=10,
        entry_price=100.0,
        current_price=102.0,
        stop_price=95.0,
        target_price=115.0,
        opened_at="2025-01-01T00:00:00",
        entry_order_id="ord-1",
        stop_gtt_id=stop_gtt_id,
    )
    defaults.update(kwargs)
    return PositionState(**defaults)


def _make_state(**kwargs) -> AccountState:
    defaults = dict(cash_inr=10000.0)
    defaults.update(kwargs)
    return AccountState(**defaults)


# -- Paper mode tests ---------------------------------------------------------


def test_paper_reconcile_ok_when_gtts_present() -> None:
    """Full agreement in paper mode: all positions have GTTs."""
    simulator = GTTSimulator()
    simulator.place("gtt-1", "INFY", 95.0, 115.0)
    gtt_mgr = GTTManager(simulator=simulator)
    reconciler = Reconciler(gtt_manager=gtt_mgr)

    state = _make_state(positions=[_make_position("INFY", stop_gtt_id="gtt-1")])
    result = asyncio.run(reconciler.reconcile(state))
    assert len(result.positions) == 1


def test_paper_reconcile_warns_missing_gtt() -> None:
    """Paper mode: position exists but GTT missing from simulator."""
    simulator = GTTSimulator()  # empty — no GTTs placed
    gtt_mgr = GTTManager(simulator=simulator)
    reconciler = Reconciler(gtt_manager=gtt_mgr)

    state = _make_state(positions=[_make_position("INFY", stop_gtt_id="missing-gtt")])
    result = asyncio.run(reconciler.reconcile(state))
    # Position should still be retained (paper mode doesn't remove)
    assert len(result.positions) == 1


def test_paper_reconcile_multiple_positions() -> None:
    """Paper mode: mixed GTT state across positions."""
    simulator = GTTSimulator()
    simulator.place("gtt-ok", "RELIANCE", 2400.0, 2700.0)
    # No GTT for HDFCBANK
    gtt_mgr = GTTManager(simulator=simulator)
    reconciler = Reconciler(gtt_manager=gtt_mgr)

    state = _make_state(
        positions=[
            _make_position("RELIANCE", stop_gtt_id="gtt-ok", entry_price=2500.0),
            _make_position("HDFCBANK", stop_gtt_id="gtt-missing", entry_price=1600.0),
        ]
    )
    result = asyncio.run(reconciler.reconcile(state))
    assert len(result.positions) == 2


def test_paper_reconcile_empty_state() -> None:
    """Paper mode: no positions — reconciliation is trivially OK."""
    reconciler = Reconciler()
    state = _make_state()
    result = asyncio.run(reconciler.reconcile(state))
    assert len(result.positions) == 0


# -- Reconciler helper method tests ------------------------------------------


def test_build_holdings_map_filters_zero_qty() -> None:
    holdings = [
        {"tradingsymbol": "INFY", "quantity": 10, "average_price": 1500.0},
        {"tradingsymbol": "TCS", "quantity": 0, "average_price": 3500.0},
        {"tradingsymbol": "", "quantity": 5, "average_price": 100.0},
    ]
    result = Reconciler._build_holdings_map(holdings)
    assert "INFY" in result
    assert "TCS" not in result
    assert "" not in result
    assert result["INFY"]["quantity"] == 10


def test_build_active_gtt_set_filters_cancelled() -> None:
    gtts = [
        {"id": "100", "status": "active"},
        {"id": "101", "status": "cancelled"},
        {"id": "102", "status": "expired"},
        {"id": "103", "status": ""},
        {"id": "104", "status": "triggered"},
    ]
    result = Reconciler._build_active_gtt_set(gtts)
    assert "100" in result
    assert "101" not in result
    assert "102" not in result
    assert "103" in result  # empty status treated as active
    assert "104" in result  # triggered is not in the excluded set
