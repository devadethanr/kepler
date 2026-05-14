from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import pytest

from execution.operator_controls import clear_block_new_entries
from memory.db import session_scope
from memory.models import ApprovalRow, EntryIntentRow, OrderIntentRow
from memory.repository import MemoryRepository
from models import PendingApproval


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


@pytest.fixture
def persist_approvals() -> Callable[[Iterable[dict[str, Any]]], list[dict[str, Any]]]:
    """Seed approvals through the durable memory layer and remove seeded rows."""
    seeded_approval_ids: set[str] = set()
    seeded_entry_intent_ids: set[str] = set()
    seeded_order_intent_ids: set[str] = set()

    def _seed(payload: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = [
            PendingApproval.model_validate(item).model_dump(mode="json")
            for item in payload
        ]
        for item in normalized:
            seeded_approval_ids.add(str(item["approval_id"]))
            seeded_entry_intent_ids.add(str(item["entry_intent_id"]))
            seeded_order_intent_ids.add(str(item["order_intent_id"]))

        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.replace_pending_approvals(normalized, source="test_execution")

        return normalized

    yield _seed

    with session_scope() as session:
        for approval_id in seeded_approval_ids:
            row = session.get(ApprovalRow, approval_id)
            if row is not None:
                session.delete(row)
        for entry_intent_id in seeded_entry_intent_ids:
            row = session.get(EntryIntentRow, entry_intent_id)
            if row is not None:
                session.delete(row)
        for order_intent_id in seeded_order_intent_ids:
            row = session.get(OrderIntentRow, order_intent_id)
            if row is not None:
                session.delete(row)
