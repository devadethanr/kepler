from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


DecisionAction = Literal[
    "BUY_NOW",
    "BUY_ONLY_ABOVE_TRIGGER",
    "WAIT_FOR_PULLBACK",
    "AVOID_NO_TRADE",
]
TradeBias = Literal["BULLISH", "BEARISH", "NEUTRAL", "MIXED"]
FunnelRoute = Literal["full_debate", "lightweight", "skip"]
SkepticVerdict = Literal["PASS", "CAUTION", "VETO"]
PortfolioFit = Literal["ACCEPTABLE", "DOWNGRADE", "REJECT"]
PlanAction = Literal["activate", "defer", "cancel"]


class EntryZoneModel(BaseModel):
    low: float = 0.0
    high: float = 0.0

    @model_validator(mode="after")
    def normalize_order(self) -> "EntryZoneModel":
        if self.low > 0 and self.high > 0 and self.high < self.low:
            self.low, self.high = self.high, self.low
        return self


class RegimeSynthesis(BaseModel):
    regime: str = "neutral"
    confidence: float = 0.0
    summary: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    source: str = "deterministic"


class UniverseFunnelCandidate(BaseModel):
    ticker: str
    score: float = 0.0
    setup_type: str = "unknown"
    sector: str | None = None
    route: FunnelRoute = "full_debate"
    reason: str = ""
    candidate_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_ticker(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("ticker"):
            payload = dict(value)
            payload["ticker"] = str(payload["ticker"]).strip().upper()
            return payload
        return value


class UniverseFunnelResult(BaseModel):
    run_id: str
    candidates: list[UniverseFunnelCandidate] = Field(default_factory=list)
    skipped: list[UniverseFunnelCandidate] = Field(default_factory=list)
    full_debate_count: int = 0


class EvidenceTraceItem(BaseModel):
    evidence_id: str
    source_type: str
    summary: str
    url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class CandidateContextV1(BaseModel):
    schema_version: str = "candidate_context_v1"
    run_id: str
    ticker: str
    scan_date: str
    candidate: UniverseFunnelCandidate
    stock_data: dict[str, Any] = Field(default_factory=dict)
    memory_packet: dict[str, Any] = Field(default_factory=dict)
    evidence_trace: list[EvidenceTraceItem] = Field(default_factory=list)
    portfolio_snapshot: dict[str, Any] = Field(default_factory=dict)
    open_positions: list[dict[str, Any]] = Field(default_factory=list)
    effective_policy: dict[str, Any] = Field(default_factory=dict)
    regime: RegimeSynthesis = Field(default_factory=RegimeSynthesis)
    degraded_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_context_ticker(cls, value: Any) -> Any:
        if isinstance(value, dict) and value.get("ticker"):
            payload = dict(value)
            payload["ticker"] = str(payload["ticker"]).strip().upper()
            return payload
        return value


class ThesisReport(BaseModel):
    report_id: str = ""
    ticker: str
    setup_quality: str = "unknown"
    thesis: str = ""
    catalysts: list[str] = Field(default_factory=list)
    invalidation: list[str] = Field(default_factory=list)
    confidence_score: int = Field(default=0, ge=0, le=10)
    source: str = "deterministic"


class SkepticReport(BaseModel):
    report_id: str = ""
    ticker: str
    verdict: SkepticVerdict = "CAUTION"
    critique: str = ""
    risks: list[str] = Field(default_factory=list)
    confidence_penalty: int = Field(default=0, ge=0, le=10)
    source: str = "deterministic"


class PortfolioFitReport(BaseModel):
    report_id: str = ""
    ticker: str
    fit: PortfolioFit = "DOWNGRADE"
    reasons: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    sector_exposure_count: int = 0
    recommended_risk_pct: float = 0.0
    source: str = "deterministic"


class FinalIntentDecision(BaseModel):
    report_id: str = ""
    ticker: str
    decision: DecisionAction
    confidence_score: int = Field(default=0, ge=0, le=10)
    setup_type: str = "unknown"
    bias: TradeBias = "NEUTRAL"
    entry_zone: EntryZoneModel = Field(default_factory=EntryZoneModel)
    stop_price: float = 0.0
    target_price: float = 0.0
    holding_days_expected: int = 0
    confidence_reasoning: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    source_reports: dict[str, str] = Field(default_factory=dict)
    evidence_trace_ids: list[str] = Field(default_factory=list)
    portfolio_fit: PortfolioFit = "DOWNGRADE"
    run_id: str | None = None

    @property
    def actionable_for_approval(self) -> bool:
        return self.decision in {"BUY_NOW", "BUY_ONLY_ABOVE_TRIGGER"}

    @property
    def entry_intent_status(self) -> str:
        if self.actionable_for_approval:
            return "proposed"
        if self.decision == "WAIT_FOR_PULLBACK":
            return "watching"
        return "rejected"


class PolicyProposal(BaseModel):
    key: str
    value: Any
    reason: str
    proposer: str = "phase13_slow_brain"
    status: str = "proposed"


class SessionPlanItem(BaseModel):
    entry_intent_id: str | None = None
    approval_id: str | None = None
    order_intent_id: str | None = None
    ticker: str
    action: PlanAction
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SessionExecutionPlan(BaseModel):
    plan_id: str
    trading_date: str
    status: str
    generated_at: datetime
    items: list[SessionPlanItem] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    session_readiness: dict[str, Any] = Field(default_factory=dict)


class SlowBrainRunResult(BaseModel):
    run_id: str
    status: str
    regime: RegimeSynthesis
    funnel: UniverseFunnelResult
    decisions: list[FinalIntentDecision] = Field(default_factory=list)
    approval_candidates: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)

