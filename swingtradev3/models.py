from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from intent_ids import approval_id as build_approval_id
from intent_ids import entry_intent_id as build_entry_intent_id
from intent_ids import order_intent_id as build_order_intent_id


class TradingMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class MarketRegime(str, Enum):
    BULL = "bull"
    BEAR = "bear"
    CHOPPY = "choppy"
    TRANSITION = "transition"


class VolatilityState(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class PendingCorporateAction(BaseModel):
    type: str | None = None
    amount: float | None = None
    ex_date: date | None = None
    gtt_adjustment_sent: bool = False
    adjustment_alert_sent_at: datetime | None = None
    requires_manual_action: bool = False


class PositionState(BaseModel):
    ticker: str
    quantity: int
    entry_price: float
    current_price: float | None = None
    stop_price: float
    target_price: float
    opened_at: datetime
    entry_order_id: str | None = None
    oco_gtt_id: str | None = None
    lifecycle_state: Literal[
        "pending_entry",
        "open",
        "closing",
        "closed",
        "reconcile_required",
        "operator_intervention",
    ] = "open"
    thesis_score: float | None = None
    research_date: date | None = None
    skill_version: str | None = None
    sector: str | None = None
    pending_corporate_action: PendingCorporateAction = Field(
        default_factory=PendingCorporateAction
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_gtt_identity(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        oco_gtt_id = payload.get("oco_gtt_id") or payload.get("stop_gtt_id") or payload.get("target_gtt_id")
        if oco_gtt_id in (None, ""):
            return payload
        payload["oco_gtt_id"] = str(oco_gtt_id)
        payload.pop("stop_gtt_id", None)
        payload.pop("target_gtt_id", None)
        return payload


class AccountState(BaseModel):
    cash_inr: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    drawdown_pct: float = 0.0
    weekly_loss_pct: float = 0.0
    consecutive_losses: int = 0
    positions: list[PositionState] = Field(default_factory=list)


class EntryZone(BaseModel):
    low: float
    high: float


class ResearchDecision(BaseModel):
    ticker: str
    score: float
    setup_type: Literal["breakout", "pullback", "earnings_play", "sector_rotation", "skip"]
    entry_zone: EntryZone
    stop_price: float
    target_price: float
    holding_days_expected: int
    confidence_reasoning: str
    risk_flags: list[str] = Field(default_factory=list)
    sector: str | None = None
    research_date: date | None = None
    skill_version: str | None = None
    current_price: float | None = None


class PendingApproval(BaseModel):
    ticker: str
    score: float
    setup_type: str
    entry_zone: EntryZone
    stop_price: float
    target_price: float
    holding_days_expected: int
    confidence_reasoning: str
    risk_flags: list[str] = Field(default_factory=list)
    sector: str | None = None
    approved: bool | None = None
    approval_id: str | None = None
    entry_intent_id: str | None = None
    order_intent_id: str | None = None
    execution_requested: bool = False
    execution_request_id: str | None = None
    status: str | None = None
    broker_tag: str | None = None
    created_at: datetime
    expires_at: datetime
    research_date: date | None = None
    skill_version: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_identity(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        payload = dict(value)
        ticker = str(payload.get("ticker") or "").strip().upper()
        if ticker:
            payload["ticker"] = ticker
        payload["entry_intent_id"] = str(
            payload.get("entry_intent_id") or build_entry_intent_id(payload)
        )
        payload["order_intent_id"] = str(
            payload.get("order_intent_id") or build_order_intent_id(payload)
        )
        payload["approval_id"] = str(
            payload.get("approval_id") or build_approval_id(payload)
        )
        if "execution_requested" not in payload:
            payload["execution_requested"] = False
        return payload


class TradeRecord(BaseModel):
    trade_id: str
    ticker: str
    quantity: int
    entry_price: float
    exit_price: float
    opened_at: datetime
    closed_at: datetime
    exit_reason: str
    pnl_abs: float
    pnl_pct: float
    setup_type: str | None = None
    thesis_reasoning: str | None = None
    research_date: date | None = None
    skill_version: str | None = None
    risk_flags: list[str] = Field(default_factory=list)


class TradeObservation(BaseModel):
    trade_id: str
    ticker: str
    observation: str
    thesis_held: bool
    exit_reason: str
    created_at: datetime


class StatsSnapshot(BaseModel):
    win_rate: float = 0.0
    sharpe: float = 0.0
    avg_winner_pct: float = 0.0
    avg_loser_pct: float = 0.0
    kelly_multiplier: float = 0.0
    best_setup_type: str | None = None
    worst_setup_type: str | None = None
    trade_count: int = 0


class CorporateAction(BaseModel):
    ticker: str
    action_type: Literal["dividend", "bonus", "split", "rights"]
    ex_date: date
    value: float | None = None
    ratio: str | None = None


class GTTOrder(BaseModel):
    oco_gtt_id: str
    ticker: str
    stop_price: float
    target_price: float
    status: Literal[
        "active",
        "triggered",
        "disabled",
        "expired",
        "cancelled",
        "rejected",
        "deleted",
    ] = "active"
    triggered_leg: Literal["stop", "target"] | None = None
    exit_order_id: str | None = None
    exit_exchange_order_id: str | None = None
    exit_order_status: str | None = None
    exit_rejection_reason: str | None = None


class FundamentalsSnapshot(BaseModel):
    ticker: str
    pe_ratio: float | None = None
    eps_growth_3yr_pct: float | None = None
    debt_equity: float | None = None
    market_cap_cr: float | None = None
    dividend_yield: float | None = None
    promoter_holding_pct: float | None = None
    promoter_pledge_pct: float | None = None
    fii_holding_pct: float | None = None
    dii_holding_pct: float | None = None
    revenue_growth_pct: float | None = None
    roce: float | None = None
    sector: str | None = None
    industry: str | None = None
    is_stale: bool = False
    as_of: date | None = None
    source: str = "cache"


# ─────────────────────────────────────────────────────────────
# V2 Models — Layer Contracts (Gemini Compatible)
# ─────────────────────────────────────────────────────────────


class RegimeState(BaseModel):
    regime: MarketRegime
    confidence: float
    volatility_state: VolatilityState
    nifty_trend: str | None = None
    vix: float | None = None
    fii_flow_direction: str | None = None
    as_of: datetime | None = None


class Signals(BaseModel):
    news: bool = False
    fii: bool = False
    breakout: bool = False
    mean_reversion: bool = False
    backtest: bool = False


class StockScore(BaseModel):
    ticker: str
    score: float
    setup_type: str
    entry_zone: EntryZone
    stop_price: float
    target_price: float
    holding_days_expected: int
    confidence_reasoning: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    sector: str | None = None
    signals: Signals = Field(default_factory=Signals)


class ScanResult(BaseModel):
    scan_date: date
    regime: RegimeState | None = None
    total_screened: int = 0
    qualified_count: int = 0
    shortlist: list[StockScore] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    approval_id: str
    ticker: str
    score: float
    setup_type: str
    entry_zone: EntryZone
    stop_price: float
    target_price: float
    confidence_reasoning: str
    created_at: datetime
    expires_at: datetime


class ApprovalResponse(BaseModel):
    approval_id: str
    decision: Literal["approved", "rejected", "expired"]
    ticker: str
    order_id: str | None = None
    gtt_stop_id: str | None = None
    gtt_target_id: str | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: str
    mode: TradingMode
    uptime_seconds: float | None = None
    services: dict[str, str] = Field(default_factory=dict)


class ScanStatusResponse(BaseModel):
    status: Literal["idle", "running", "completed", "failed"]
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: str | None = None
    result: ScanResult | None = None
