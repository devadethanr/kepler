from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

try:
    import quantstats as qs

    QUANTSTATS_AVAILABLE = True
except ImportError:
    QUANTSTATS_AVAILABLE = False

from config import cfg
from models import TradeRecord


@dataclass
class MetricsReport:
    sharpe: float
    win_rate: float
    profit_factor: float
    max_drawdown: float
    passed: bool
    full_report: dict[str, Any] | None = None


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


class QuantStatsMetrics:
    """QuantStats integration for full tearsheet generation."""

    def __init__(self) -> None:
        if not QUANTSTATS_AVAILABLE:
            raise RuntimeError(
                "quantstats package required. Install: pip install quantstats"
            )

    def from_backtest_result(
        self,
        equity_curve: list[dict[str, Any]],
        trades: list[TradeRecord],
        initial_capital: float,
    ) -> dict[str, Any]:
        """Generate QuantStats metrics from backtest results."""
        if not equity_curve:
            return self._empty_report()

        df = pd.DataFrame(equity_curve)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        returns = df["equity"].pct_change().dropna()

        if len(returns) < 2:
            return self._empty_report()

        try:
            metrics = qs.reports.metrics(
                returns,
                mode="full",
                display=False,
            )

            report = {
                "sharpe": qs.stats.sharpe(returns),
                "sortino": qs.stats.sortino(returns),
                "max_drawdown": qs.stats.max_drawdown(returns),
                "cagr": qs.stats.cagr(returns),
                "volatility": qs.stats.volatility(returns),
                "calmar": qs.stats.calmar(returns),
                "win_rate": self._calculate_trade_win_rate(trades),
                "profit_factor": self._calculate_profit_factor(trades),
                "total_trades": len(trades),
                "avg_win": self._avg_win(trades),
                "avg_loss": self._avg_loss(trades),
            }

            report["passed"] = self._check_thresholds(report)
            report["quantstats_metrics"] = (
                metrics.to_dict() if hasattr(metrics, "to_dict") else {}
            )

            return report
        except Exception as e:
            return {"error": str(e), **self._empty_report()}

    def _empty_report(self) -> dict[str, Any]:
        return {
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown": 0.0,
            "cagr": 0.0,
            "volatility": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "passed": False,
        }

    def _calculate_trade_win_rate(self, trades: list[TradeRecord]) -> float:
        if not trades:
            return 0.0
        wins = sum(1 for t in trades if t.pnl_abs > 0)
        return wins / len(trades)

    def _calculate_profit_factor(self, trades: list[TradeRecord]) -> float:
        wins = sum(t.pnl_abs for t in trades if t.pnl_abs > 0)
        losses = sum(abs(t.pnl_abs) for t in trades if t.pnl_abs < 0)
        return wins / losses if losses > 0 else float("inf")

    def _avg_win(self, trades: list[TradeRecord]) -> float:
        wins = [t.pnl_abs for t in trades if t.pnl_abs > 0]
        return sum(wins) / len(wins) if wins else 0.0

    def _avg_loss(self, trades: list[TradeRecord]) -> float:
        losses = [abs(t.pnl_abs) for t in trades if t.pnl_abs < 0]
        return sum(losses) / len(losses) if losses else 0.0

    def _check_thresholds(self, report: dict[str, Any]) -> bool:
        """Check if metrics meet minimum thresholds."""
        return (
            report.get("win_rate", 0) >= cfg.backtest.thresholds.min_win_rate
            and report.get("profit_factor", 0)
            >= cfg.backtest.thresholds.min_profit_factor
            and report.get("sharpe", 0) >= cfg.backtest.thresholds.min_sharpe
            and report.get("max_drawdown", 1) <= cfg.backtest.thresholds.max_drawdown
        )

    def generate_tearsheet(
        self,
        equity_curve: list[dict[str, Any]],
        output_path: str = "backtest_tearsheet.html",
    ) -> None:
        """Generate HTML tearsheet report."""
        if not QUANTSTATS_AVAILABLE:
            print("QuantStats not available")
            return

        df = pd.DataFrame(equity_curve)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        returns = df["equity"].pct_change().dropna()

        if len(returns) < 2:
            print("Insufficient data for tearsheet")
            return

        try:
            qs.reports.html(
                returns,
                output=output_path,
                title="SwingTradeV3 Backtest Results",
            )
            print(f"Tearsheet saved to: {output_path}")
        except Exception as e:
            print(f"Failed to generate tearsheet: {e}")


def generate_simple_report(result: Any) -> dict[str, Any]:
    """Generate simple metrics report without QuantStats."""
    trades = result.trades if hasattr(result, "trades") else []
    equity = result.equity_curve if hasattr(result, "equity_curve") else []
    final = result.final_capital if hasattr(result, "final_capital") else 0
    initial = cfg.backtest.initial_capital

    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_return": 0.0,
            "passed": False,
        }

    wins = [t.pnl_abs for t in trades if t.pnl_abs > 0]
    losses = [abs(t.pnl_abs) for t in trades if t.pnl_abs < 0]

    total_return = (final / initial - 1) if initial > 0 else 0
    win_rate = len(wins) / len(trades)
    profit_factor = sum(wins) / sum(losses) if losses else float("inf")

    passed = (
        win_rate >= cfg.backtest.thresholds.min_win_rate
        and profit_factor >= cfg.backtest.thresholds.min_profit_factor
    )

    return {
        "total_trades": len(trades),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_return": total_return,
        "final_capital": final,
        "passed": passed,
    }
