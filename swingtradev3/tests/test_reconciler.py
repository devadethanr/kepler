import asyncio

from swingtradev3.agents.reconciler import Reconciler
from swingtradev3.models import AccountState, PositionState


def test_reconciler_runs_with_missing_gtt() -> None:
    state = AccountState(
        cash_inr=1000.0,
        positions=[
            PositionState(
                ticker="INFY",
                quantity=1,
                entry_price=100.0,
                current_price=100.0,
                stop_price=95.0,
                target_price=110.0,
                opened_at="2025-01-01T00:00:00",
                entry_order_id="missing",
                stop_gtt_id="missing",
            )
        ],
    )
    reconciled = asyncio.run(Reconciler().reconcile(state))
    assert len(reconciled.positions) == 1
