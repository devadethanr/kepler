from __future__ import annotations

from dataclasses import dataclass

from config import cfg
from models import AccountState
from policy.effective_policy import resolve_effective_policy
from risk import circuit_breakers
from risk.position_sizer import calculate_position_size


@dataclass
class RiskDecision:
    approved: bool
    quantity: int
    reason: str


class SelfHealingRiskEngine:
    def evaluate(
        self,
        state: AccountState,
        score: float,
        entry_price: float,
        stop_price: float,
        target_price: float,
        sector: str | None = None,
    ) -> RiskDecision:
        if circuit_breakers.max_positions_reached(state):
            return RiskDecision(False, 0, "max_positions_reached")
        if circuit_breakers.weekly_loss_exceeded(state):
            return RiskDecision(False, 0, "weekly_loss_limit")
        if circuit_breakers.drawdown_exceeded(state):
            return RiskDecision(False, 0, "drawdown_limit")
        if entry_price <= stop_price:
            return RiskDecision(False, 0, "invalid_stop")
        rr_ratio = (target_price - entry_price) / (entry_price - stop_price)
        if rr_ratio < cfg.risk.min_rr_ratio:
            return RiskDecision(False, 0, "risk_reward_too_low")
        policy = resolve_effective_policy()
        normalized_sector = str(sector or "").strip().lower()
        if normalized_sector and normalized_sector != "unknown":
            existing = sum(
                1
                for position in state.positions
                if str(position.lifecycle_state or "open").lower() in {"open", "closing"}
                and str(position.sector or "").strip().lower() == normalized_sector
            )
            if existing >= policy.max_same_sector_positions:
                return RiskDecision(False, 0, "max_same_sector_positions")
        available_capital = state.cash_inr * (1 - cfg.trading.min_cash_reserve_pct)
        quantity = calculate_position_size(available_capital, score, entry_price)
        if quantity <= 0:
            return RiskDecision(False, 0, "position_size_zero")
        max_risk = state.cash_inr * cfg.risk.max_risk_pct_per_trade
        actual_risk = quantity * (entry_price - stop_price)
        if actual_risk > max_risk:
            quantity = int(max_risk // (entry_price - stop_price))
        if quantity <= 0:
            return RiskDecision(False, 0, "risk_budget_exceeded")
        return RiskDecision(True, quantity, "approved")
