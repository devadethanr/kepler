from __future__ import annotations

from fastapi import APIRouter

from ..schemas.health import HealthResponse
from health_manager import get_all_statuses

router = APIRouter()


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {
        "app": "running",
    }
    services.update(get_all_statuses())
    
    return HealthResponse(
        status="ok",
        mode="paper",
        services=services,
    )
