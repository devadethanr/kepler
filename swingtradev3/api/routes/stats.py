from __future__ import annotations

from fastapi import APIRouter
from typing import Any

from paths import CONTEXT_DIR
from storage import read_json
from models import StatsSnapshot

router = APIRouter()

@router.get("", response_model=StatsSnapshot)
async def get_stats():
    """Get overall performance metrics and stats."""
    payload = read_json(CONTEXT_DIR / "stats.json", {})
    return StatsSnapshot.model_validate(payload)
