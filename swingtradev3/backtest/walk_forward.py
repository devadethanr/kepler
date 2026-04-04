from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from backtest.data_fetcher import BacktestDataFetcher
from backtest.engine import BacktestEngine, BacktestResult
from config import cfg


@dataclass
class WalkForwardResult:
    windows: list[dict[str, Any]]
    combined_metrics: dict[str, float]
    passed: bool


class WalkForwardValidator:
    def __init__(self, engine: BacktestEngine | None = None) -> None:
        self.engine = engine or BacktestEngine()
        self.in_sample_months = cfg.backtest.walk_forward.in_sample_months
        self.out_sample_months = cfg.backtest.walk_forward.out_sample_months
        self.n_windows = cfg.backtest.walk_forward.n_windows

    def run(
        self,
        tickers: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> WalkForwardResult:
        start = datetime.fromisoformat(start_date or cfg.backtest.start_date)
        end = datetime.fromisoformat(end_date or cfg.backtest.end_date)

        total_months = (end.year - start.year) * 12 + (end.month - start.month)
        if total_months <= 0:
            return WalkForwardResult(
                windows=[],
                combined_metrics={"total_trades": 0, "avg_return": 0, "avg_sharpe": 0},
                passed=False,
            )

        window_size = self.in_sample_months + self.out_sample_months

        windows = []
        step = max(1, (total_months - window_size) // self.n_windows)

        for i in range(self.n_windows):
            in_sample_start = start + timedelta(days=i * step * 30)
            in_sample_end = in_sample_start + timedelta(days=self.in_sample_months * 30)
            out_sample_end = in_sample_end + timedelta(days=self.out_sample_months * 30)

            if out_sample_end > end:
                break

            print(
                f"Window {i + 1}: {in_sample_start.date()} to {out_sample_end.date()}"
            )

            in_result = self.engine.run(
                tickers,
                start_date=in_sample_start.isoformat()[:10],
                end_date=in_sample_end.isoformat()[:10],
            )

            out_result = self.engine.run(
                tickers,
                start_date=in_sample_end.isoformat()[:10],
                end_date=out_sample_end.isoformat()[:10],
            )

            window = {
                "window": i + 1,
                "in_sample": {
                    "trades": len(in_result.trades),
                    "return": in_result.metrics.get("total_return", 0),
                    "sharpe": in_result.metrics.get("sharpe_ratio", 0),
                },
                "out_sample": {
                    "trades": len(out_result.trades),
                    "return": out_result.metrics.get("total_return", 0),
                    "sharpe": out_result.metrics.get("sharpe_ratio", 0),
                },
            }
            windows.append(window)

        combined = self._combine_metrics(windows)

        wfe_ratio = self._calculate_wfe(windows)
        combined["wfe_ratio"] = wfe_ratio
        combined["passed"] = wfe_ratio >= cfg.backtest.thresholds.min_wfe_ratio

        return WalkForwardResult(
            windows=windows,
            combined_metrics=combined,
            passed=combined["passed"],
        )

    def _combine_metrics(self, windows: list[dict]) -> dict[str, float]:
        if not windows:
            return {"total_trades": 0, "avg_return": 0, "avg_sharpe": 0}

        total_trades = sum(w["out_sample"]["trades"] for w in windows)
        avg_return = sum(w["out_sample"]["return"] for w in windows) / len(windows)
        avg_sharpe = sum(w["out_sample"]["sharpe"] for w in windows) / len(windows)

        return {
            "total_trades": total_trades,
            "avg_return": avg_return,
            "avg_sharpe": avg_sharpe,
        }

    def _calculate_wfe(self, windows: list[dict]) -> float:
        """Calculate Walk-Forward Efficiency ratio."""
        if not windows:
            return 0.0

        out_sample_returns = [w["out_sample"]["return"] for w in windows]
        in_sample_returns = [w["in_sample"]["return"] for w in windows]

        out_cum = sum(out_sample_returns)
        in_cum = sum(in_sample_returns)

        if in_cum == 0:
            return 0.0

        return out_cum / in_cum if in_cum > 0 else 0.0


def compute_wfe_ratio(in_sample_return: float, out_of_sample_return: float) -> float:
    """Legacy helper for WFE ratio calculation."""
    if in_sample_return == 0:
        return 0.0
    return out_of_sample_return / in_sample_return
