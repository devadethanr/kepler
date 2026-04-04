from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    mode: str
    uptime_seconds: float | None = None
    services: dict[str, str] = Field(default_factory=dict)
