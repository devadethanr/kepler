from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from agents.research_agent import ResearchAgent
from backtest.data_fetcher import BacktestDataFetcher
from backtest.engine import BacktestEngine
from config import cfg
from models import TradeRecord, TradingMode


@dataclass
class BacktestResult:
    trades: list[TradeRecord]
    equity_curve: list
    final_capital: float
    metrics: dict


def run_backtest_cli(tickers: list[str] | None = None) -> BacktestResult:
    if tickers is None:
        from data.nifty200_loader import Nifty200Loader

        tickers = Nifty200Loader().load()[:50]

    engine = BacktestEngine()
    result = engine.run(tickers)

    return BacktestResult(
        trades=result.trades,
        equity_curve=result.equity_curve,
        final_capital=result.final_capital,
        metrics=result.metrics,
    )


async def run_backtest() -> BacktestResult:
    if cfg.trading.mode != TradingMode.BACKTEST and cfg.backtest.use_llm:
        raise RuntimeError("Backtest execution should be launched with backtest mode")

    tickers = None
    if not cfg.backtest.use_llm:
        from data.nifty200_loader import Nifty200Loader

        tickers = Nifty200Loader().load()[:50]

    result = run_backtest_cli(tickers)
    return result
