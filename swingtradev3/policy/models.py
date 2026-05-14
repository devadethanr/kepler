from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


PolicyKey = Literal[
    "min_score_threshold",
    "max_position_size_pct",
    "new_entries_enabled",
    "max_same_sector_positions",
    "trail_stop_at_pct",
    "trail_to_pct",
    "debate_top_n",
]


class PolicyOverlay(BaseModel):
    overlay_id: str
    key: PolicyKey
    value: Any
    status: str
    reason: str
    proposer: str
    approver: str | None = None
    expires_at: str | None = None
    rollback_handle: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class AppliedOverlay(BaseModel):
    overlay_id: str
    key: str
    value: Any
    reason: str
    proposer: str
    approver: str | None = None
    expires_at: str | None = None


class IgnoredOverlay(BaseModel):
    overlay_id: str
    key: str
    reason: str


class EffectivePolicy(BaseModel):
    min_score_threshold: float
    max_position_size_pct: float
    new_entries_enabled: bool
    max_same_sector_positions: int
    trail_stop_at_pct: float
    trail_to_pct: float
    debate_top_n: int
    base: dict[str, Any]
    sources: dict[str, str]
    applied_overlays: list[AppliedOverlay] = Field(default_factory=list)
    ignored_overlays: list[IgnoredOverlay] = Field(default_factory=list)
    operator_controls: dict[str, Any] = Field(default_factory=dict)
    resolved_at_ist: datetime

    def value_for(self, key: PolicyKey) -> Any:
        return getattr(self, key)
