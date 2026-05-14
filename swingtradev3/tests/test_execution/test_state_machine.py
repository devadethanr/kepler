from __future__ import annotations

import pytest

from execution.coordinator import ExecutionCoordinator


@pytest.mark.parametrize(
    ("broker_status", "requested_quantity", "filled_quantity", "expected"),
    [
        ("COMPLETE", 5, 5, "entry_filled"),
        ("OPEN", 5, 0, "entry_open"),
        ("OPEN", 5, 2, "entry_partially_filled"),
        ("REJECTED", 5, 0, "failed"),
        ("CANCELLED", 5, 0, "cancelled"),
    ],
)
def test_order_intent_state_machine_derives_entry_status(
    broker_status: str,
    requested_quantity: int,
    filled_quantity: int,
    expected: str,
):
    coordinator = ExecutionCoordinator()

    assert (
        coordinator._derive_intent_status(
            broker_status=broker_status,
            requested_quantity=requested_quantity,
            filled_quantity=filled_quantity,
        )
        == expected
    )
