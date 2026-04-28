from __future__ import annotations

import pytest

from execution.operator_controls import clear_block_new_entries


@pytest.fixture(autouse=True)
def _clear_block_new_entries_between_tests():
    """Ensure the Phase 6 block_new_entries kill-switch does not leak across tests.

    Tests that exercise the reconciler or fail-closed worker startup may persist
    a ``block_new_entries=True`` operator control row. Without this cleanup, later
    coordinator tests see the block active and short-circuit to ``ignored``.
    """
    clear_block_new_entries(source="test_execution_conftest")
    yield
    clear_block_new_entries(source="test_execution_conftest")
