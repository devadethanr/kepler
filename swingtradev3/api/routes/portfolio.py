from __future__ import annotations

from fastapi import APIRouter
from typing import Any

from paths import CONTEXT_DIR
from storage import read_json
from models import AccountState
from api.tasks.event_bus import event_bus

router = APIRouter()


@router.get("/summary")
async def get_portfolio_summary() -> dict[str, Any]:
    """Get aggregated portfolio views."""
    state_payload = read_json(CONTEXT_DIR / "state.json", {})
    if not state_payload:
        return {
            "cash_inr": 0.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "open_positions_count": 0,
            "sector_exposure": {},
            "risk_utilization": 0.0,
        }

    state = AccountState.model_validate(state_payload)

    open_positions = len(state.positions)
    total_pnl = state.realized_pnl + state.unrealized_pnl

    sector_exposure: dict[str, float] = {}
    total_invested = 0.0
    for pos in state.positions:
        val = pos.quantity * (pos.current_price or pos.entry_price)
        total_invested += val
        sector = pos.sector or "Unknown"
        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + val

    return {
        "cash_inr": state.cash_inr,
        "realized_pnl": state.realized_pnl,
        "unrealized_pnl": state.unrealized_pnl,
        "total_pnl": total_pnl,
        "open_positions_count": open_positions,
        "sector_exposure": sector_exposure,
        "total_invested": total_invested,
    }


@router.get("/failed-events")
async def get_failed_events():
    """List all failed events."""
    return [fp.model_dump(mode="json") for fp in event_bus.get_failed_events()]


@router.post("/failed-events/{event_id}/retry")
async def retry_failed_event(event_id: str):
    """Manually retry a failed event by event ID."""
    success = await event_bus.retry_failed_event(event_id)
    if success:
        return {"message": "Retry scheduled"}
    return {"error": "Event not found"}, 404
