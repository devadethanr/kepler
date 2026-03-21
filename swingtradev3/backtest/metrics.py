from __future__ import annotations

from dataclasses import dataclass

from swingtradev3.models import TradeRecord


@dataclass
class MetricsReport:
    sharpe: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    passed: bool


def summarize(trades: list[TradeRecord]) -> MetricsReport:
    if not trades:
        return MetricsReport(0.0, 0.0, 0.0, 0.0, False)
    wins = [trade.pnl_abs for trade in trades if trade.pnl_abs > 0]
    losses = [abs(trade.pnl_abs) for trade in trades if trade.pnl_abs < 0]
    win_rate = len(wins) / len(trades)
    profit_factor = (sum(wins) / sum(losses)) if losses else float("inf")
    return MetricsReport(
        sharpe=0.0,
        win_rate=win_rate,
        profit_factor=profit_factor,
        max_drawdown=0.0,
        passed=win_rate >= 0.45 and profit_factor >= 1.3,
    )
