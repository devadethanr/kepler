from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text, func

from intent_ids import approval_id as build_approval_id
from intent_ids import entry_intent_id as build_entry_intent_id
from intent_ids import order_intent_id as build_order_intent_id
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


# ── SQLAlchemy rows ────────────────────────────────────────────────

class AccountStateRow(TimestampMixin, Base):
    __tablename__ = "account_state"

    account_key: Mapped[str] = mapped_column(String(32), primary_key=True, default="primary")
    cash_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    drawdown_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    weekly_loss_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PositionRow(TimestampMixin, Base):
    __tablename__ = "positions"

    position_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_price: Mapped[float] = mapped_column(Float, nullable=False)
    target_price: Mapped[float] = mapped_column(Float, nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ApprovalRow(TimestampMixin, Base):
    __tablename__ = "approvals"

    approval_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    entry_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    order_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    approved: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    execution_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at_effective: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class TradeRow(TimestampMixin, Base):
    __tablename__ = "trades"

    trade_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    opened_at_effective: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at_effective: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pnl_abs: Mapped[float] = mapped_column(Float, nullable=False)
    pnl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    exit_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class AuthSessionRow(TimestampMixin, Base):
    __tablename__ = "auth_sessions"

    session_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ExecutionEventRow(Base):
    __tablename__ = "execution_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class NewsArticleRow(TimestampMixin, Base):
    __tablename__ = "news_articles"

    news_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="unknown", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tickers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class NewsProviderHealthRow(TimestampMixin, Base):
    __tablename__ = "news_provider_health"

    provider: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    items_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_emitted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class EntryIntentRow(TimestampMixin, Base):
    __tablename__ = "entry_intents"

    intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    order_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class OrderIntentRow(TimestampMixin, Base):
    __tablename__ = "order_intents"

    order_intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    entry_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    broker_tag: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class BrokerOrderRow(TimestampMixin, Base):
    __tablename__ = "broker_orders"

    broker_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    exchange_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    order_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted", nullable=False)
    broker_tag: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class BrokerFillRow(TimestampMixin, Base):
    __tablename__ = "broker_fills"

    fill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    broker_order_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    order_intent_id: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    fill_price: Mapped[float] = mapped_column(Float, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProtectiveTriggerRow(TimestampMixin, Base):
    __tablename__ = "protective_triggers"

    protective_trigger_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    position_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_arm", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PolicyOverlayRow(TimestampMixin, Base):
    __tablename__ = "policy_overlays"

    overlay_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ReconciliationRunRow(TimestampMixin, Base):
    __tablename__ = "reconciliation_runs"

    reconciliation_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="started", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class FailureIncidentRow(TimestampMixin, Base):
    __tablename__ = "failure_incidents"

    incident_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="warning", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class OperatorControlRow(TimestampMixin, Base):
    __tablename__ = "operator_controls"

    control_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CognitionRunRow(TimestampMixin, Base):
    __tablename__ = "cognition_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    phase: Mapped[str] = mapped_column(String(32), default="phase_13", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="started", index=True, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CognitionReportRow(TimestampMixin, Base):
    __tablename__ = "cognition_reports"

    report_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    ticker: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), default="v1", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ok", index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SessionExecutionPlanRow(TimestampMixin, Base):
    __tablename__ = "session_execution_plans"

    plan_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trading_date: Mapped[date] = mapped_column(index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ScanRunRow(TimestampMixin, Base):
    __tablename__ = "scan_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="idle", index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


# ── Pydantic models (runtime state / API contracts) ────────────────


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


class StoredKiteSessionPayload(BaseModel):
    api_key: str
    access_token: str
    public_token: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    user_shortname: str | None = None
    email: str | None = None
    broker: str | None = None
    user_type: str | None = None
    login_time: str | None = None
    created_at: str | None = None
    raw_session: dict[str, Any] = Field(default_factory=dict)


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
    product: str = "CNC"
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
    slow_brain_run_id: str | None = None
    slow_brain_decision: str | None = None
    portfolio_fit: str | None = None
    source_reports: dict[str, str] = Field(default_factory=dict)
    evidence_trace_ids: list[str] = Field(default_factory=list)
    funnel_route: str | None = None
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


# ── V2 Models — Layer Contracts ────────────────────────────────────


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
    diagnostics: dict[str, Any] = Field(default_factory=dict)


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
