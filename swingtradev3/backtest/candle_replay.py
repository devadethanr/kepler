from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from swingtradev3.agents.research_agent import ResearchAgent
from swingtradev3.config import cfg
from swingtradev3.models import TradeRecord, TradingMode


@dataclass
class BacktestResult:
    trades: list[TradeRecord]


async def run_backtest() -> BacktestResult:
    if cfg.trading.mode != TradingMode.BACKTEST and cfg.backtest.use_llm:
        raise RuntimeError("Backtest execution should be launched with backtest mode")
    agent = ResearchAgent()
    await agent.run()
    return BacktestResult(trades=[])
