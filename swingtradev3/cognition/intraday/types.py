from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

IST = ZoneInfo("Asia/Kolkata")

ExceptionKind = Literal[
    "broker_inconsistency",
    "major_gap_or_shock",
    "corporate_action_surprise",
    "unexpected_regime_break",
]
ExceptionSeverity = Literal["warning", "critical"]
AdvisoryAction = Literal[
    "monitor",
    "alert_operator",
    "review_position",
    "suggest_block_new_entries",
    "suggest_exit_review",
]


class ExceptionCase(BaseModel):
    case_id: str
    kind: ExceptionKind
    severity: ExceptionSeverity = "warning"
    source: str
    ticker: str | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(IST))
    summary: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ExceptionAdvice(BaseModel):
    case_id: str
    kind: ExceptionKind
    risk_level: ExceptionSeverity
    advisory_action: AdvisoryAction
    summary: str
    rationale: str
    immediate_checks: list[str] = Field(default_factory=list)
    deterministic_policy_hook: str | None = None
    confidence_score: int = Field(ge=0, le=10)
    advisory_only: Literal[True] = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(IST))
