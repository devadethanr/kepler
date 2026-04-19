"""Phase 6: operator-visible reconciliation state.

Exposes the kill-switch (``block_new_entries``), latest reconciliation status,
recent reconciliation_runs, and open failure_incidents so operators and the
dashboard can verify Phase 6 health without running raw SQL.

Read-only endpoints. No writes; operator remediation actions live in
``operator_controls`` helpers invoked by the worker and future Phase 8 UI.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from sqlalchemy import select

from execution.operator_controls import (
    active_block_reasons,
    is_block_new_entries_active,
    read_block_new_entries,
    read_reconciliation_status,
)
from memory.db import session_scope
from memory.models import ReconciliationRunRow
from memory.repositories import MemoryRepository


router = APIRouter()


def _recent_reconciliation_runs(limit: int = 20) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = (
            session.scalars(
                select(ReconciliationRunRow)
                .order_by(ReconciliationRunRow.updated_at.desc())
                .limit(limit)
            ).all()
        )
        return [
            {
                "reconciliation_run_id": row.reconciliation_run_id,
                "status": row.status,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "payload": dict(row.payload or {}),
            }
            for row in rows
        ]


@router.get("/reconciliation")
async def get_reconciliation_state() -> dict[str, Any]:
    """Aggregate snapshot of Phase 6 state."""
    block = read_block_new_entries()
    status = read_reconciliation_status()
    with session_scope() as session:
        repo = MemoryRepository(session)
        open_incidents = repo.list_failure_incidents(status="open")
    return {
        "block_new_entries": {
            "active": is_block_new_entries_active(),
            "reasons": active_block_reasons(),
            "record": block,
        },
        "reconciliation_status": status,
        "recent_runs": _recent_reconciliation_runs(limit=20),
        "open_incidents": open_incidents,
    }


@router.get("/block")
async def get_block_state() -> dict[str, Any]:
    """Compact kill-switch view for UI headers / badges."""
    return {
        "active": is_block_new_entries_active(),
        "reasons": active_block_reasons(),
        "record": read_block_new_entries(),
    }
