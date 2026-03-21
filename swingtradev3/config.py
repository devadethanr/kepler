from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

from .models import TradingMode
from .paths import PROJECT_ROOT


class QuickFilterConfig(BaseModel):
    min_market_cap_cr: float
    min_avg_volume: int
    max_promoter_pledge_pct: float
    below_200ema_disqualify: bool = True


class AnalystLoopConfig(BaseModel):
    enabled: bool = True
    cadence: str = "monthly"
    day_of_month: int = 1
    time: str
    min_trades_required: int


class QuarterlyAuditConfig(BaseModel):
    enabled: bool = True
    min_trades_required: int


class ResearchConfig(BaseModel):
    scan_start_time: str
    briefing_time: str
    min_score_threshold: float
    max_shortlist: int
    max_same_sector_positions: int
    async_scan: bool = True
    quick_filter: QuickFilterConfig
    analyst_loop: AnalystLoopConfig
    quarterly_audit: QuarterlyAuditConfig


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
    enable_trailing: bool = True
    avoid_fno_expiry_days: int
    max_entry_deviation_pct: float
    corporate_action_handling: CorporateActionHandlingConfig


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


class LLMConfig(BaseModel):
    timeout_seconds: float
    max_tool_calls_per_stock: int
    roles: LLMRolesConfig
    fallback_chain: list[LLMFallbackConfig] = Field(default_factory=list)


class LearningConfig(BaseModel):
    min_trades_for_lesson: int
    min_trades_for_kelly: int
    max_lessons_per_month: int


class ScheduleConfig(BaseModel):
    auth_refresh: str
    market_open: str
    market_close: str
    research_start: str
    briefing_time: str
    timezone: str


class TelegramConfig(BaseModel):
    enabled: bool = True
    require_entry_approval: bool = True
    alert_on_levels: list[str] = Field(default_factory=list)
    daily_summary: bool = True
    daily_summary_time: str = "16:00"


class NotificationsConfig(BaseModel):
    telegram: TelegramConfig


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


class TradingConfig(BaseModel):
    mode: TradingMode
    capital_inr: float
    exchange: str
    universe: str
    max_positions: int
    min_cash_reserve_pct: float


class AppConfig(BaseModel):
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
