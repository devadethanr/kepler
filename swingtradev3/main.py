from __future__ import annotations

import argparse
import asyncio

import schedule

from agents.execution_agent import ExecutionAgent
from agents.research_agent import ResearchAgent
from auth.token_manager import TokenManager
from backtest.candle_replay import run_backtest
from config import cfg
from logging_config import setup_logging
from paths import ensure_runtime_dirs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="swingtradev3 entrypoint")
    parser.add_argument("--mode", choices=["backtest", "paper", "live"], default=cfg.trading.mode.value)
    return parser


async def _run_scheduled() -> None:
    research_agent = ResearchAgent()
    execution_agent = ExecutionAgent()
    token_manager = TokenManager()

    schedule.every().day.at(cfg.schedule.auth_refresh).do(lambda: asyncio.run(token_manager.refresh()))
    schedule.every().day.at(cfg.schedule.research_start).do(lambda: asyncio.run(research_agent.run()))
    schedule.every(cfg.execution.poll_interval_minutes).minutes.do(
        lambda: asyncio.run(execution_agent.poll())
    )

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


def main() -> None:
    ensure_runtime_dirs()
    setup_logging()
    args = _build_parser().parse_args()
    if args.mode == "backtest":
        asyncio.run(run_backtest())
        return
    asyncio.run(_run_scheduled())


if __name__ == "__main__":
    main()
