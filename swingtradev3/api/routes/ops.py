"""Phase 6 + 7: operator-visible state + write endpoints.

Phase 6 (read-only): block_new_entries, reconciliation_status, recent runs,
open incidents.

Phase 7 (writes): manual flatten, per-position close, operator-mode flips
(trading/new-entries/exit-only), kill-switch clear, and reconcile-required
acknowledgement. Writes do NOT place orders directly — they flip operator
control flags which the worker processes on its next tick. This preserves
the Phase 6 mutation-lock invariant ("all execution writes go through the
worker").
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from execution.auth_preflight import is_session_fresh, read_auth_session_age_hours
from execution.operator_controls import (
    active_block_reasons,
    clear_block_new_entries,
    clear_flatten_request,
    is_block_new_entries_active,
    is_exit_only_mode,
    is_new_entries_enabled,
    is_trading_enabled,
    read_block_new_entries,
    read_exit_only_mode,
    read_flatten_request,
    read_new_entries_enabled,
    read_reconciliation_status,
    read_trading_enabled,
    read_worker_status,
    request_flatten,
    request_reconcile_ack,
    set_exit_only_mode,
    set_new_entries_enabled,
    set_trading_enabled,
)
from memory.db import session_scope
from memory.models import ReconciliationRunRow
from memory.repositories import MemoryRepository


router = APIRouter()


# ---------------------------------------------------------------------------
# Read endpoints (Phase 6 carry-over + new /ops/safety)
# ---------------------------------------------------------------------------


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
    status_info = read_reconciliation_status()
    with session_scope() as session:
        repo = MemoryRepository(session)
        open_incidents = repo.list_failure_incidents(status="open")
    return {
        "block_new_entries": {
            "active": is_block_new_entries_active(),
            "reasons": active_block_reasons(),
            "record": block,
        },
        "reconciliation_status": status_info,
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


@router.get("/safety")
async def get_safety_state() -> dict[str, Any]:
    """Phase 7: aggregate operator-control / kill-switch / auth snapshot."""
    fresh, stale_reason, age_hours = is_session_fresh()

    with session_scope() as session:
        repo = MemoryRepository(session)
        open_incidents = repo.list_failure_incidents(status="open")

    reasons_active = {r: True for r in active_block_reasons()}
    worker_status = read_worker_status() or {}

    def _switch(
        name: str,
        incident_ids: tuple[str, ...] = (),
        incident_prefixes: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        return {
            "active": bool(reasons_active.get(name)),
            "open_incidents": [
                inc
                for inc in open_incidents
                if (
                    str(inc.get("incident_id", "")) in incident_ids
                    or any(
                        str(inc.get("incident_id", "")).startswith(prefix)
                        for prefix in incident_prefixes
                    )
                )
            ],
        }

    ddpi_status: dict[str, Any] | None
    try:
        from ops.phase0_check import check_ddpi_poa

        ddpi = check_ddpi_poa()
        ddpi_status = {"status": ddpi.status, "detail": ddpi.detail}
    except Exception as exc:  # pragma: no cover
        ddpi_status = {"status": "UNKNOWN", "detail": str(exc)}

    return {
        "operator_controls": {
            "trading_enabled": {
                "enabled": is_trading_enabled(),
                "record": read_trading_enabled(),
            },
            "new_entries_enabled": {
                "enabled": is_new_entries_enabled(),
                "record": read_new_entries_enabled(),
            },
            "exit_only_mode": {
                "enabled": is_exit_only_mode(),
                "record": read_exit_only_mode(),
            },
            "flatten_requested": read_flatten_request(),
        },
        "block_new_entries": {
            "active": is_block_new_entries_active(),
            "reasons": active_block_reasons(),
            "record": read_block_new_entries(),
        },
        "kill_switches": {
            "broker_disconnected": _switch("broker_disconnected", ("broker_disconnected",)),
            "stream_unavailable": _switch("stream_unavailable", ("stream_unavailable",)),
            "stale_auth": _switch("stale_auth", ("stale_auth",)),
            "stale_quotes": _switch("stale_quotes", ("stale_quotes",)),
            "daily_loss_limit": _switch("daily_loss_limit", ("daily_loss_limit",)),
            "order_submission_failures": _switch(
                "order_submission_failures", ("order_submission_failures",)
            ),
            "gtt_recovery_failures": _switch(
                "gtt_recovery_failures",
                incident_prefixes=("protection:",),
            ),
            "positions_drift": _switch("positions_drift", ("reconcile_positions",)),
            "orders_drift": _switch("orders_drift", ("reconcile_orders",)),
            "gtts_drift": _switch("gtts_drift", ("reconcile_gtts",)),
        },
        "worker_status": worker_status,
        "runtime_counters": worker_status.get("safety_counters") or {},
        "auth_session": {
            "fresh": fresh,
            "reason": stale_reason,
            "age_hours": age_hours if age_hours is not None else read_auth_session_age_hours(),
        },
        "ddpi_poa": ddpi_status,
        "open_incidents": open_incidents,
    }


# ---------------------------------------------------------------------------
# Write endpoints (Phase 7)
# ---------------------------------------------------------------------------


class FlattenRequestBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)
    tickers: list[str] | None = None
    multi_day_holdings_acked: list[str] | None = None


class ClosePositionBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)
    multi_day_holdings_acked: list[str] | None = None


class BlockClearBody(BaseModel):
    reason: str | None = None
    source: str = "operator"


class ModeUpdateBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=200)
    trading_enabled: bool | None = None
    new_entries_enabled: bool | None = None
    exit_only_mode: bool | None = None


class ReconcileAckBody(BaseModel):
    resolution: str = Field(..., description="broker_close or retain")


@router.post("/flatten", status_code=status.HTTP_202_ACCEPTED)
async def post_flatten(body: FlattenRequestBody) -> dict[str, Any]:
    result = request_flatten(
        source="api",
        reason=body.reason,
        tickers=body.tickers,
        multi_day_holdings_acked=body.multi_day_holdings_acked,
    )
    return {"accepted": True, "control": result.get("value")}


@router.delete("/flatten")
async def delete_flatten() -> dict[str, Any]:
    result = clear_flatten_request(source="api", reason="operator_cancel")
    if result is None:
        raise HTTPException(status_code=404, detail="no flatten request to clear")
    return {"cleared": True, "control": result.get("value")}


@router.post("/positions/{ticker}/close", status_code=status.HTTP_202_ACCEPTED)
async def post_close_position(ticker: str, body: ClosePositionBody) -> dict[str, Any]:
    normalized = ticker.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="ticker required")
    result = request_flatten(
        source="api",
        reason=body.reason,
        tickers=[normalized],
        multi_day_holdings_acked=body.multi_day_holdings_acked,
    )
    return {"accepted": True, "ticker": normalized, "control": result.get("value")}


@router.post("/block/clear")
async def post_block_clear(body: BlockClearBody) -> dict[str, Any]:
    result = clear_block_new_entries(source=body.source or "operator", reason=body.reason)
    return {"cleared": True, "control": result.get("value")}


@router.post("/mode")
async def post_mode(body: ModeUpdateBody) -> dict[str, Any]:
    results: dict[str, Any] = {}
    if body.trading_enabled is not None:
        results["trading_enabled"] = set_trading_enabled(
            enabled=body.trading_enabled,
            source="api",
            reason=body.reason,
        ).get("value")
    if body.new_entries_enabled is not None:
        results["new_entries_enabled"] = set_new_entries_enabled(
            enabled=body.new_entries_enabled,
            source="api",
            reason=body.reason,
        ).get("value")
    if body.exit_only_mode is not None:
        results["exit_only_mode"] = set_exit_only_mode(
            enabled=body.exit_only_mode,
            source="api",
            reason=body.reason,
        ).get("value")
    if not results:
        raise HTTPException(status_code=400, detail="no mode flag provided")
    return {"updated": results}


@router.post("/reconcile/ack/{position_id}", status_code=status.HTTP_202_ACCEPTED)
async def post_reconcile_ack(position_id: str, body: ReconcileAckBody) -> dict[str, Any]:
    normalized_position = position_id.strip().upper()
    normalized_resolution = body.resolution.strip().lower()
    if not normalized_position:
        raise HTTPException(status_code=400, detail="position_id required")
    if normalized_resolution not in {"broker_close", "retain"}:
        raise HTTPException(status_code=400, detail="invalid_resolution")

    result = request_reconcile_ack(
        position_id=normalized_position,
        resolution=normalized_resolution,
        source="api",
    )
    return {"accepted": True, "control": result.get("value")}
