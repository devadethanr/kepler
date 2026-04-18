"""
swingtradev3 Configuration
==========================

All configuration models loaded from config.yaml via Pydantic.
Single source of truth for all tunable values.

Sections:
  - Trading (mode, capital, universe)
  - Research (scan times, thresholds, filters, analyst loop)
  - Execution (polling, trailing, corporate actions)
  - Risk (per-trade limits, drawdown, position sizing)
  - Indicators (momentum, trend, volatility, volume, structure, RS, patterns)
  - LLM (models, temperatures, fallback chain, ADK routing)
  - Learning (trade review, lesson generation)
  - Schedule (market hours, 24-hour cycle timings)
  - Notifications (Telegram settings)
  - Backtest (dates, thresholds, walk-forward, optimizer)
  - API (FastAPI host, port, CORS, auth, rate limits)
  - Dashboard (Streamlit host, port, refresh)
  - Data (rate limits, cache TTLs)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from models import TradingMode
from paths import PROJECT_ROOT


# ═══════════════════════════════════════════════════════════
# TRADING
# ═══════════════════════════════════════════════════════════

class TradingConfig(BaseModel):
    mode: TradingMode
    capital_inr: float
    exchange: str
    universe: str
    max_positions: int
    min_cash_reserve_pct: float


# ═══════════════════════════════════════════════════════════
# RESEARCH
# ═══════════════════════════════════════════════════════════

class QuickFilterConfig(BaseModel):
    """Fast Python-based filters applied before LLM analysis."""
    min_market_cap_cr: float
    min_avg_volume: int
    max_promoter_pledge_pct: float
    below_200ema_disqualify: bool = True


class AnalystLoopConfig(BaseModel):
    """Monthly SKILL.md review and improvement loop."""
    enabled: bool = True
    cadence: str = "monthly"
    day_of_month: int = 1
    time: str
    min_trades_required: int


class QuarterlyAuditConfig(BaseModel):
    """Quarterly strategy audit requiring minimum trade count."""
    enabled: bool = True
    min_trades_required: int


class ResearchFilterConfig(BaseModel):
    """V2: Multi-signal candidate selection funnel thresholds."""
    min_priority_signals: int = 1
    batch_size: int = 10
    news_sweep_query: str = "Indian stock market today Nifty 200 news"
    options_pcr_threshold: float = 1.2
    options_oi_spike_pct: float = 20
    trend_filter_ema: int = 200
    min_volume_ratio: float = 1.0
    max_pledging_pct: float = 25
    min_delivery_pct: float = 50


class ResearchConfig(BaseModel):
    scan_start_time: str
    briefing_time: str
    min_score_threshold: float
    max_shortlist: int
    max_same_sector_positions: int
    exclude_earnings_within_days: int = 7
    exclude_corporate_actions_within_days: int = 5
    async_scan: bool = True
    quick_filter: QuickFilterConfig
    analyst_loop: AnalystLoopConfig
    quarterly_audit: QuarterlyAuditConfig
    filter: ResearchFilterConfig = Field(default_factory=ResearchFilterConfig)


# ═══════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════

class CorporateActionHandlingConfig(BaseModel):
    dividend_adjust_stop: bool = True
    alert_days_before_exdate: int = 5
    auto_adjust_timeout_hours: int = 12
    bonus_split_pause_entries: bool = True


class ExecutionConfig(BaseModel):
    poll_interval_minutes: int
    approval_timeout_hours: int
    trail_stop_at_pct: float
    trail_to_pct: float
    trail_stop_to_locked_profit_pct: float = 5.0
    trail_min_step_pct: float = 0.25
    trail_hysteresis_pct: float = 0.25
    trail_modify_cooldown_seconds: int = 300
    enable_trailing: bool = True
    avoid_fno_expiry_days: int
    max_entry_deviation_pct: float
    corporate_action_handling: CorporateActionHandlingConfig


# ═══════════════════════════════════════════════════════════
# RISK
# ═══════════════════════════════════════════════════════════

class ConfidenceBucketConfig(BaseModel):
    min_score: float
    capital_pct: float


class ConfidenceSizingConfig(BaseModel):
    high: ConfidenceBucketConfig
    medium: ConfidenceBucketConfig


class RiskConfig(BaseModel):
    max_risk_pct_per_trade: float
    max_weekly_loss_pct: float
    max_drawdown_pct: float
    min_rr_ratio: float
    confidence_sizing: ConfidenceSizingConfig


# ═══════════════════════════════════════════════════════════
# INDICATORS
# ═══════════════════════════════════════════════════════════

class IndicatorMomentumConfig(BaseModel):
    rsi_length: int
    rsi_overbought: float
    rsi_oversold: float
    macd_fast: int
    macd_slow: int
    macd_signal: int
    stoch_k: int
    stoch_d: int
    roc_length: int


class IndicatorTrendConfig(BaseModel):
    ema_fast: int
    ema_mid: int
    ema_slow: int
    adx_length: int
    adx_trend_threshold: float
    supertrend_length: int
    supertrend_multiplier: float


class IndicatorVolatilityConfig(BaseModel):
    atr_length: int
    atr_stop_multiplier: float
    bb_length: int
    bb_std: float
    bb_squeeze_threshold: float


class IndicatorVolumeConfig(BaseModel):
    volume_avg_periods: int
    volume_spike_multiplier: float
    mfi_length: int


class IndicatorStructureConfig(BaseModel):
    pivot_type: str
    sr_lookback_periods: int
    high_52w_proximity_alert_pct: float
    base_consolidation_min_weeks: int
    base_consolidation_max_weeks: int


class IndicatorRelativeStrengthConfig(BaseModel):
    periods: list[int]
    benchmark: str


class IndicatorPatternsConfig(BaseModel):
    min_strength: int
    enabled: list[str]


class IndicatorsConfig(BaseModel):
    timeframe: str
    candle_buffer_size: int
    weekly_candle_buffer: int
    momentum: IndicatorMomentumConfig
    trend: IndicatorTrendConfig
    volatility: IndicatorVolatilityConfig
    volume: IndicatorVolumeConfig
    structure: IndicatorStructureConfig
    relative_strength: IndicatorRelativeStrengthConfig
    patterns: IndicatorPatternsConfig


# ═══════════════════════════════════════════════════════════
# LLM
# ═══════════════════════════════════════════════════════════

class LLMRoleConfig(BaseModel):
    provider: str
    model: str
    temperature: float
    max_tokens: int


class LLMFallbackConfig(BaseModel):
    provider: str
    model: str


class LLMRolesConfig(BaseModel):
    research: LLMRoleConfig
    execution: LLMRoleConfig
    analyst: LLMRoleConfig


class LlmAdkConfig(BaseModel):
    """V2: ADK model routing via LiteLLM for each agent type."""
    root_model: str = "openai/meta/llama-3.1-70b-instruct"
    research_model: str = "openai/meta/llama-3.1-70b-instruct"
    execution_model: str = "openai/meta/llama-3.1-70b-instruct"
    learning_model: str = "openai/meta/llama-3.1-70b-instruct"
    judge_model: str = "openai/meta/llama-3.1-70b-instruct"


class LLMConfig(BaseModel):
    timeout_seconds: float
    max_tool_calls_per_stock: int
    roles: LLMRolesConfig
    fallback_chain: list[LLMFallbackConfig] = Field(default_factory=list)
    adk: LlmAdkConfig = Field(default_factory=LlmAdkConfig)


# ═══════════════════════════════════════════════════════════
# LEARNING
# ═══════════════════════════════════════════════════════════

class LearningConfig(BaseModel):
    min_trades_for_lesson: int
    min_trades_for_kelly: int
    max_lessons_per_month: int


# ═══════════════════════════════════════════════════════════
# SCHEDULE
# ═══════════════════════════════════════════════════════════

class ScheduleConfig(BaseModel):
    auth_refresh: str
    market_open: str
    market_close: str
    research_start: str
    briefing_time: str
    timezone: str


# ═══════════════════════════════════════════════════════════
# NOTIFICATIONS
# ═══════════════════════════════════════════════════════════

class TelegramConfig(BaseModel):
    enabled: bool = True
    require_entry_approval: bool = True
    alert_on_levels: list[str] = Field(default_factory=list)
    daily_summary: bool = True
    daily_summary_time: str = "16:00"


class NotificationsConfig(BaseModel):
    telegram: TelegramConfig


# ═══════════════════════════════════════════════════════════
# BACKTEST
# ═══════════════════════════════════════════════════════════

class WalkForwardConfig(BaseModel):
    enabled: bool = True
    in_sample_months: int
    out_sample_months: int
    n_windows: int


class OptimizerConfig(BaseModel):
    enabled: bool = False
    n_trials: int
    metric: str
    search_space: dict[str, list[float | int]]


class BacktestThresholdConfig(BaseModel):
    min_win_rate: float
    min_sharpe: float
    max_drawdown: float
    min_profit_factor: float
    min_wfe_ratio: float
    min_total_trades: int


class BacktestConfig(BaseModel):
    use_llm: bool = False
    start_date: str
    end_date: str
    initial_capital: float
    fee_model: str
    fill_price: str
    slippage_pct: float
    brokerage_per_order: float
    cache_data: bool = True
    cache_dir: str
    thresholds: BacktestThresholdConfig
    walk_forward: WalkForwardConfig
    optimizer: OptimizerConfig


# ═══════════════════════════════════════════════════════════
# V2 ADDITIONS — API, DASHBOARD, SCHEDULER, DATA
# ═══════════════════════════════════════════════════════════

class ApiRateLimitConfig(BaseModel):
    requests_per_minute: int = 60
    burst: int = 10


class ApiConfig(BaseModel):
    """V2: FastAPI server settings."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])
    api_key_env: str = "FASTAPI_API_KEY"
    rate_limit: ApiRateLimitConfig = Field(default_factory=ApiRateLimitConfig)

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "")


class DashboardConfig(BaseModel):
    """V2: Streamlit dashboard settings."""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8501
    refresh_interval_seconds: int = 30
    theme: str = "light"


class SchedulerOvernightConfig(BaseModel):
    start_time: str = "22:00"
    end_time: str = "06:00"
    global_market_tracking_minutes: int = 120
    news_monitoring_minutes: int = 30
    macro_updates_hours: int = 4
    gift_nifty_minutes: int = 15
    gift_nifty_start: str = "05:00"


class SchedulerMorningConfig(BaseModel):
    news_digest_time: str = "06:00"
    regime_check_time: str = "06:30"
    fii_dii_check_time: str = "07:00"
    earnings_check_time: str = "07:30"
    briefing_generation_time: str = "08:00"
    briefing_send_time: str = "08:30"
    approval_reminder_time: str = "08:45"
    premarket_setup_time: str = "09:00"


class SchedulerMarketHoursConfig(BaseModel):
    opening_range_end: str = "09:45"
    position_monitoring_minutes: int = 15
    gtt_health_check_minutes: int = 30
    intraday_news_minutes: int = 60
    entry_window_start: str = "10:30"
    mid_morning_regime_check: str = "11:00"
    lunch_volume_check_start: str = "12:00"
    lunch_volume_check_end: str = "13:00"
    afternoon_review: str = "13:00"
    late_day_news: str = "14:00"
    final_entry_window: str = "14:30"
    closing_prep: str = "15:00"
    market_close_actions: str = "15:30"


class SchedulerPostMarketConfig(BaseModel):
    eod_data_collection: str = "15:30"
    pnl_calculation: str = "15:45"
    fii_dii_final: str = "16:00"
    options_analysis: str = "16:15"
    corporate_action_check: str = "16:30"
    observation_logging: str = "17:00"
    state_snapshot: str = "17:30"


class SchedulerEveningResearchConfig(BaseModel):
    start_time: str = "18:00"
    signal_sweep_minutes: int = 15
    filtering_minutes: int = 15
    deep_analysis_minutes: int = 90
    scoring_minutes: int = 30
    briefing_send_time: str = "20:30"
    approval_window_open: str = "20:45"


class SchedulerWindDownConfig(BaseModel):
    final_news_scan: str = "21:00"
    state_persistence: str = "21:15"
    log_rotation: str = "21:30"
    health_check: str = "21:45"
    overnight_mode_start: str = "22:00"


class SchedulerConfig(BaseModel):
    """V2: 24-hour operational cycle timings."""
    overnight: SchedulerOvernightConfig = Field(default_factory=SchedulerOvernightConfig)
    morning: SchedulerMorningConfig = Field(default_factory=SchedulerMorningConfig)
    market_hours: SchedulerMarketHoursConfig = Field(default_factory=SchedulerMarketHoursConfig)
    post_market: SchedulerPostMarketConfig = Field(default_factory=SchedulerPostMarketConfig)
    evening_research: SchedulerEveningResearchConfig = Field(default_factory=SchedulerEveningResearchConfig)
    wind_down: SchedulerWindDownConfig = Field(default_factory=SchedulerWindDownConfig)


class DataConfig(BaseModel):
    """V2: Data layer settings — rate limits, cache TTLs."""
    kite_rate_limit_per_second: int = 3
    cache_ttl_minutes: int = 30
    parquet_cache_enabled: bool = True
    parquet_cache_dir: str = ".backtest_cache"
    news_cache_ttl_minutes: int = 60
    fundamentals_cache_ttl_hours: int = 24
    macro_cache_ttl_hours: int = 4


# ═══════════════════════════════════════════════════════════
# ROOT CONFIG
# ═══════════════════════════════════════════════════════════

class AppConfig(BaseModel):
    # Core
    trading: TradingConfig
    research: ResearchConfig
    execution: ExecutionConfig
    risk: RiskConfig
    indicators: IndicatorsConfig
    llm: LLMConfig
    learning: LearningConfig
    schedule: ScheduleConfig
    notifications: NotificationsConfig
    backtest: BacktestConfig

    # V2 additions
    api: ApiConfig = Field(default_factory=ApiConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    data: DataConfig = Field(default_factory=DataConfig)

    @model_validator(mode="after")
    def validate_thresholds(self) -> "AppConfig":
        if self.research.max_shortlist < self.trading.max_positions:
            raise ValueError("research.max_shortlist must be >= trading.max_positions")
        return self


def _load_yaml_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=1)
def load_config(config_path: Path | None = None) -> AppConfig:
    load_dotenv(PROJECT_ROOT / ".env")
    path = config_path or (PROJECT_ROOT / "config.yaml")
    return AppConfig.model_validate(_load_yaml_config(path))


cfg = load_config()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class RuntimeFlags:
    """Environment-controlled safety gates for the live runtime."""

    @property
    def live_trading_enabled(self) -> bool:
        return _env_bool("LIVE_TRADING_ENABLED", False)

    @property
    def new_entries_enabled(self) -> bool:
        return _env_bool("NEW_ENTRIES_ENABLED", False)

    @property
    def exit_only_mode(self) -> bool:
        return _env_bool("EXIT_ONLY_MODE", False)

    @property
    def use_slow_brain(self) -> bool:
        return _env_bool("USE_SLOW_BRAIN", False)

    @property
    def use_exception_analyst(self) -> bool:
        return _env_bool("USE_EXCEPTION_ANALYST", False)

    def live_entry_block_reason(self, mode: TradingMode | str) -> str | None:
        mode_value = mode.value if isinstance(mode, TradingMode) else str(mode)
        if mode_value != TradingMode.LIVE.value:
            return None
        if not self.live_trading_enabled:
            return "LIVE_TRADING_ENABLED=false"
        if self.exit_only_mode:
            return "EXIT_ONLY_MODE=true"
        if not self.new_entries_enabled:
            return "NEW_ENTRIES_ENABLED=false"
        return None


runtime_flags = RuntimeFlags()
