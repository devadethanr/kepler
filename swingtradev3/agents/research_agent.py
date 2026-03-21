from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.data.corporate_actions import CorporateActionsStore
from swingtradev3.data.earnings_calendar import EarningsCalendar
from swingtradev3.data.nifty200_loader import Nifty200Loader
from swingtradev3.llm.tool_executor import ToolExecutor
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState, PendingApproval, ResearchDecision, StatsSnapshot, TradingMode
from swingtradev3.notifications.telegram_client import TelegramClient
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json
from swingtradev3.tools.fii_dii_data import FiiDiiDataTool
from swingtradev3.tools.fundamental_data import FundamentalDataTool
from swingtradev3.tools.market_data import MarketDataTool
from swingtradev3.tools.news_search import NewsSearchTool
from swingtradev3.tools.options_data import OptionsDataTool


def _current_skill_version() -> str:
    try:
        from git import Repo

        return Repo(Path(__file__).resolve().parents[2]).head.commit.hexsha[:7]
    except Exception:
        return "nogit"


class ResearchAgent:
    def __init__(
        self,
        market_tool: MarketDataTool | None = None,
        fundamental_tool: FundamentalDataTool | None = None,
        news_tool: NewsSearchTool | None = None,
        fii_dii_tool: FiiDiiDataTool | None = None,
        options_tool: OptionsDataTool | None = None,
        executor: ToolExecutor | None = None,
        telegram: TelegramClient | None = None,
        nifty_loader: Nifty200Loader | None = None,
        earnings_calendar: EarningsCalendar | None = None,
        corporate_actions: CorporateActionsStore | None = None,
    ) -> None:
        self.market_tool = market_tool or MarketDataTool()
        self.fundamental_tool = fundamental_tool or FundamentalDataTool()
        self.news_tool = news_tool or NewsSearchTool()
        self.fii_dii_tool = fii_dii_tool or FiiDiiDataTool()
        self.options_tool = options_tool or OptionsDataTool()
        self.executor = executor or ToolExecutor(mode=cfg.trading.mode.value)
        self.telegram = telegram or TelegramClient()
        self.nifty_loader = nifty_loader or Nifty200Loader()
        self.earnings_calendar = earnings_calendar or EarningsCalendar()
        self.corporate_actions = corporate_actions or CorporateActionsStore()
        self.log = get_logger("research")
        self._semaphore = asyncio.Semaphore(3)

    def _load_state(self) -> AccountState:
        return AccountState.model_validate(read_json(CONTEXT_DIR / "state.json", {}))

    def _load_stats(self) -> StatsSnapshot:
        return StatsSnapshot.model_validate(read_json(CONTEXT_DIR / "stats.json", {}))

    def _open_position_tickers(self, state: AccountState) -> set[str]:
        return {position.ticker for position in state.positions}

    def _passes_quick_filter(self, market_data: dict[str, Any], fundamentals: dict[str, Any]) -> bool:
        if cfg.research.quick_filter.below_200ema_disqualify and not market_data.get("above_200ema"):
            return False
        if (fundamentals.get("market_cap_cr") or 0) < cfg.research.quick_filter.min_market_cap_cr:
            return False
        if (market_data.get("volume", 0) or 0) < cfg.research.quick_filter.min_avg_volume:
            return False
        if (fundamentals.get("promoter_pledge_pct") or 0) > cfg.research.quick_filter.max_promoter_pledge_pct:
            return False
        return True

    def _rules_score(self, ticker: str, market_data: dict[str, Any], fundamentals: dict[str, Any]) -> ResearchDecision:
        score = 0.0
        if market_data.get("above_200ema"):
            score += 2.0
        if market_data.get("trend_strong"):
            score += 1.5
        if market_data.get("outperforming_index"):
            score += 2.0
        if market_data.get("accumulation_flag"):
            score += 1.0
        if (market_data.get("base_weeks") or 0) >= cfg.indicators.structure.base_consolidation_min_weeks:
            score += 1.0
        if (fundamentals.get("promoter_pledge_pct") or 0) < 20:
            score += 1.0
        if (market_data.get("proximity_to_52w_high_pct") or 100) <= cfg.indicators.structure.high_52w_proximity_alert_pct:
            score += 1.0
        atr_stop = market_data.get("stop_distance") or 0
        close = market_data.get("close") or 0
        return ResearchDecision(
            ticker=ticker,
            score=min(score, 10.0),
            setup_type="breakout" if market_data.get("proximity_to_52w_high_pct") else "pullback",
            entry_zone={"low": round(close * 0.995, 2), "high": round(close * 1.005, 2)},
            stop_price=round(close - atr_stop, 2),
            target_price=round(close + (atr_stop * cfg.risk.min_rr_ratio), 2),
            holding_days_expected=10,
            confidence_reasoning="Rule-based backtest score from trend, relative strength, volume, and structure.",
            risk_flags=[],
            sector=fundamentals.get("sector"),
            research_date=date.today(),
            skill_version=_current_skill_version(),
            current_price=close,
        )

    async def _analyze_one(
        self,
        ticker: str,
        state: AccountState,
        stats: StatsSnapshot,
        skill_version: str,
    ) -> ResearchDecision | None:
        async with self._semaphore:
            market_data = (
                await self.market_tool.get_eod_data_async(ticker)
                if cfg.trading.mode.value == "live"
                else self.market_tool.get_eod_data(ticker)
            )
            fundamentals = self.fundamental_tool.get_fundamentals(ticker)
            if not self._passes_quick_filter(market_data, fundamentals):
                return None
            stock_context = {
                **market_data,
                "fundamentals": fundamentals,
                "news": self.news_tool.search_news(f"{ticker} stock news India last 7 days"),
                "fii_dii": self.fii_dii_tool.get_fii_dii(),
            }
            if cfg.trading.mode == TradingMode.BACKTEST and not cfg.backtest.use_llm:
                decision = self._rules_score(ticker, market_data, fundamentals)
            else:
                stock_context["options"] = self.options_tool.get_options_data(ticker)
                decision = await self.executor.score_stock(
                    ticker=ticker,
                    stock_context=stock_context,
                    state=state,
                    stats=stats,
                    skill_version=skill_version,
                )
            if decision.score < cfg.research.min_score_threshold:
                return None
            return decision

    def _sector_capped(self, decisions: list[ResearchDecision], state: AccountState) -> list[ResearchDecision]:
        counts: dict[str, int] = {}
        for position in state.positions:
            if position.sector:
                counts[position.sector] = counts.get(position.sector, 0) + 1
        output: list[ResearchDecision] = []
        for decision in sorted(decisions, key=lambda item: item.score, reverse=True):
            sector = decision.sector or "Unknown"
            if counts.get(sector, 0) >= cfg.research.max_same_sector_positions:
                continue
            counts[sector] = counts.get(sector, 0) + 1
            output.append(decision)
        return output

    def _write_research_artifact(self, decision: ResearchDecision) -> None:
        day_dir = CONTEXT_DIR / "research" / date.today().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = day_dir / f"{decision.ticker}.json"
        write_json(artifact_path, decision.model_dump(mode="json"))

    def _write_pending_approvals(self, shortlist: list[ResearchDecision]) -> list[PendingApproval]:
        created_at = datetime.utcnow()
        approvals = [
            PendingApproval(
                ticker=item.ticker,
                score=item.score,
                setup_type=item.setup_type,
                entry_zone=item.entry_zone,
                stop_price=item.stop_price,
                target_price=item.target_price,
                holding_days_expected=item.holding_days_expected,
                confidence_reasoning=item.confidence_reasoning,
                risk_flags=item.risk_flags,
                sector=item.sector,
                created_at=created_at,
                expires_at=created_at.replace(microsecond=0)
                + __import__("datetime").timedelta(hours=cfg.execution.approval_timeout_hours),
                research_date=item.research_date,
                skill_version=item.skill_version,
            )
            for item in shortlist
        ]
        write_json(
            CONTEXT_DIR / "pending_approvals.json",
            [item.model_dump(mode="json") for item in approvals],
        )
        return approvals

    async def _send_briefing(self, shortlist: list[ResearchDecision]) -> None:
        lines = [
            f"{item.ticker}: score {item.score:.1f}, {item.setup_type}, entry {item.entry_zone.low}-{item.entry_zone.high}, "
            f"stop {item.stop_price}, target {item.target_price}"
            for item in shortlist
        ]
        if not lines:
            lines = ["No setups met the threshold today."]
        await self.telegram.send_approval_request(lines)

    async def run(self) -> list[ResearchDecision]:
        state = self._load_state()
        stats = self._load_stats()
        universe = [ticker for ticker in self.nifty_loader.load() if ticker not in self._open_position_tickers(state)]
        skill_version = _current_skill_version()
        results = await asyncio.gather(
            *[self._analyze_one(ticker, state, stats, skill_version) for ticker in universe]
        )
        decisions = [item for item in results if item is not None]
        for decision in decisions:
            self._write_research_artifact(decision)
        capped = self._sector_capped(decisions, state)
        capacity = max(cfg.trading.max_positions - len(state.positions), 0)
        shortlist = capped[: min(cfg.research.max_shortlist, capacity if capacity else cfg.research.max_shortlist)]
        self._write_pending_approvals(shortlist)
        await self._send_briefing(shortlist)
        self.log.info("Research run completed with {} shortlisted setups", len(shortlist))
        return shortlist
