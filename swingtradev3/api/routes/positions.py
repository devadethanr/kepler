from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import List

from paths import CONTEXT_DIR
from storage import read_json
from models import PositionState, AccountState

router = APIRouter()

@router.get("", response_model=List[PositionState])
async def get_positions():
    """List all open positions."""
    state_payload = read_json(CONTEXT_DIR / "state.json", {})
    if not state_payload:
        return []
    state = AccountState.model_validate(state_payload)
    return state.positions

@router.get("/{ticker}", response_model=PositionState)
async def get_position(ticker: str):
    """Get details for a specific position by ticker."""
    state_payload = read_json(CONTEXT_DIR / "state.json", {})
    if not state_payload:
        raise HTTPException(status_code=404, detail="No active state found")
    state = AccountState.model_validate(state_payload)
    
    for pos in state.positions:
        if pos.ticker.lower() == ticker.lower() or (pos.entry_order_id and pos.entry_order_id.lower() == ticker.lower()):
            return pos
            
    raise HTTPException(status_code=404, detail="Position not found")
