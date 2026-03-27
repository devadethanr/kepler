from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

import schedule
from zoneinfo import ZoneInfo

from swingtradev3.agents.execution_agent import ExecutionAgent
from swingtradev3.agents.research_agent import ResearchAgent
from swingtradev3.auth.token_manager import TokenManager
from swingtradev3.backtest.candle_replay import run_backtest
from swingtradev3.config import cfg
from swingtradev3.logging_config import get_logger, setup_logging
from swingtradev3.paths import ensure_runtime_dirs


log = get_logger("decisions")
_tz = ZoneInfo(cfg.schedule.timezone)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="swingtradev3 entrypoint")
    parser.add_argument("--mode", choices=["backtest", "paper", "live"], default=cfg.trading.mode.value)
    return parser


def _is_market_hours() -> bool:
    """Check if current time is within market hours (09:15 - 15:30 IST)."""
    now = datetime.now(_tz)
    market_open = now.replace(
        hour=int(cfg.schedule.market_open.split(":")[0]),
        minute=int(cfg.schedule.market_open.split(":")[1]),
        second=0,
        microsecond=0,
    )
    market_close = now.replace(
        hour=int(cfg.schedule.market_close.split(":")[0]),
        minute=int(cfg.schedule.market_close.split(":")[1]),
        second=0,
        microsecond=0,
    )
    return market_open <= now <= market_close


async def _execution_poll(agent: ExecutionAgent) -> None:
    """Guarded execution poll — only runs during market hours."""
    if not _is_market_hours():
        log.info("Outside market hours — skipping execution poll")
        return
    await agent.poll()


async def _run_scheduled() -> None:
    research_agent = ResearchAgent()
    execution_agent = ExecutionAgent()
    token_manager = TokenManager()

    # Startup: run once immediately if within market hours
    if _is_market_hours():
        log.info("Market hours active — running startup sequence")
        await execution_agent.startup()
    else:
        log.info("Outside market hours — startup will run at market open")

    # Daily token refresh at 08:50
    schedule.every().day.at(cfg.schedule.auth_refresh).do(
        lambda: asyncio.create_task(token_manager.refresh())
    )

    # Execution agent startup at market open (09:15)
    schedule.every().day.at(cfg.schedule.market_open).do(
        lambda: asyncio.create_task(execution_agent.startup())
    )

    # Research agent at 15:45
    schedule.every().day.at(cfg.schedule.research_start).do(
        lambda: asyncio.create_task(research_agent.run())
    )

    # Execution poll every 30 min (market hours guarded)
    schedule.every(cfg.execution.poll_interval_minutes).minutes.do(
        lambda: asyncio.create_task(_execution_poll(execution_agent))
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
