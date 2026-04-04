from __future__ import annotations

from config import cfg
from models import AccountState


def weekly_loss_exceeded(state: AccountState) -> bool:
    return state.weekly_loss_pct >= cfg.risk.max_weekly_loss_pct


def drawdown_exceeded(state: AccountState) -> bool:
    return state.drawdown_pct >= cfg.risk.max_drawdown_pct


def max_positions_reached(state: AccountState) -> bool:
    return len(state.positions) >= cfg.trading.max_positions
