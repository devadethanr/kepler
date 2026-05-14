from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import List

from memory.db import session_scope
from memory.repository import MemoryRepository
from models import PositionState

router = APIRouter()
ACTIVE_POSITION_STATES = {"open", "closing"}

@router.get("", response_model=List[PositionState])
async def get_positions():
    """List all open positions."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        positions = repo.list_positions(states=ACTIVE_POSITION_STATES)
    return [PositionState.model_validate(position["payload"]) for position in positions]

@router.get("/{ticker}", response_model=PositionState)
async def get_position(ticker: str):
    """Get details for a specific position by ticker."""
    normalized = ticker.strip().lower()
    with session_scope() as session:
        repo = MemoryRepository(session)
        positions = repo.list_positions(states=ACTIVE_POSITION_STATES)

    for position in positions:
        payload = PositionState.model_validate(position["payload"])
        if payload.ticker.lower() == normalized:
            return payload
        if payload.entry_order_id and payload.entry_order_id.lower() == normalized:
            return payload

    raise HTTPException(status_code=404, detail="Position not found")
