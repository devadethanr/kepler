from __future__ import annotations

from fastapi import APIRouter, HTTPException
from typing import List

from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import TradeRecord

router = APIRouter()

@router.get("", response_model=List[TradeRecord])
async def get_trades():
    """List closed trades."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_trades_payload()
    return [TradeRecord.model_validate(t) for t in payload]

@router.get("/{trade_id}", response_model=TradeRecord)
async def get_trade(trade_id: str):
    """Get details for a specific trade by ID."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_trades_payload()
    for t in payload:
        if str(t.get("trade_id")) == trade_id:
            return TradeRecord.model_validate(t)
    raise HTTPException(status_code=404, detail="Trade not found")

@router.post("/{trade_id}/close")
async def close_trade(trade_id: str):
    """Deprecated: use POST /ops/positions/{ticker}/close (Phase 7)."""
    raise HTTPException(
        status_code=410,
        detail="Deprecated. Use POST /ops/positions/{ticker}/close to flatten a live position.",
    )
