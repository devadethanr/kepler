from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.data.corporate_actions import CorporateActionsStore
from swingtradev3.data.earnings_calendar import EarningsCalendar
from swingtradev3.data.nifty50_loader import Nifty50Loader
from swingtradev3.data.nifty200_loader import Nifty200Loader
from swingtradev3.learning.lesson_generator import LessonGenerator
from swingtradev3.learning.stats_engine import StatsEngine
from swingtradev3.llm.tool_executor import ToolExecutor
from swingtradev3.logging_config import get_logger
from swingtradev3.models import AccountState, PendingApproval, ResearchDecision, StatsSnapshot, TradingMode
from swingtradev3.notifications.telegram_client import TelegramClient
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json
from swingtradev3.tools.market.fii_dii_data import FiiDiiDataTool
from swingtradev3.tools.market.fundamental_data import FundamentalDataTool
from swingtradev3.tools.market.market_data import MarketDataTool
from swingtradev3.tools.market.news_search import NewsSearchTool
from swingtradev3.tools.market.options_data import OptionsDataTool


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
        nifty50_loader: Nifty50Loader | None = None,
        earnings_calendar: EarningsCalendar | None = None,
        corporate_actions: CorporateActionsStore | None = None,
        stats_engine: StatsEngine | None = None,
        lesson_generator: LessonGenerator | None = None,
    ) -> None:
        self.market_tool = market_tool or MarketDataTool()
        self.fundamental_tool = fundamental_tool or FundamentalDataTool()
        self.news_tool = news_tool or NewsSearchTool()
        self.fii_dii_tool = fii_dii_tool or FiiDiiDataTool()
        self.options_tool = options_tool or OptionsDataTool()
        self.executor = executor or ToolExecutor(mode=cfg.trading.mode.value)
        self.telegram = telegram or TelegramClient()
        self.nifty_loader = nifty_loader or Nifty200Loader()
        self.nifty50_loader = nifty50_loader or Nifty50Loader()
        self.earnings_calendar = earnings_calendar or EarningsCalendar()
        self.corporate_actions = corporate_actions or CorporateActionsStore()
        self.stats_engine = stats_engine or StatsEngine()
        self.lesson_generator = lesson_generator or LessonGenerator()
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

    def _monthly_expiry(self, day: date) -> date:
        cursor = day.replace(day=28) + timedelta(days=4)
        cursor = cursor - timedelta(days=cursor.day)
        while cursor.weekday() != 3:
            cursor -= timedelta(days=1)
        return cursor

    def _is_near_fno_expiry(self, today: date | None = None) -> bool:
        today = today or date.today()
        expiry = self._monthly_expiry(today)
        if today > expiry:
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            expiry = self._monthly_expiry(next_month)

        trading_days = 0
        cursor = today
        while cursor <= expiry:
            if cursor.weekday() < 5:
                trading_days += 1
            cursor += timedelta(days=1)
        return 0 < trading_days <= cfg.execution.avoid_fno_expiry_days + 1

    def _fixed_event_block_reason(self, ticker: str, today: date | None = None) -> str | None:
        if self._is_near_fno_expiry(today=today):
            return "near_fno_expiry"

        actions = self.corporate_actions.upcoming(
            ticker,
            cfg.research.exclude_corporate_actions_within_days,
        )
        blocking = [action.action_type for action in actions if action.action_type in {"bonus", "split", "rights"}]
        if blocking:
            action_types = ",".join(sorted(set(blocking)))
            return f"upcoming_corporate_actions:{action_types}"
        return None

    def _event_risk_flags(self, ticker: str) -> list[str]:
        flags: list[str] = []
        for action in self.corporate_actions.upcoming(ticker, cfg.research.exclude_corporate_actions_within_days):
            flags.append(f"upcoming_{action.action_type}:{action.ex_date.isoformat()}")
        return flags

    def _apply_post_score_event_rules(
        self,
        decision: ResearchDecision,
        ticker: str,
        earnings_map: dict[str, date],
    ) -> str | None:
        earnings_date = earnings_map.get(ticker)
        if earnings_date is None or decision.setup_type == "earnings_play":
            return None

        delta = (earnings_date - date.today()).days
        if 0 <= delta <= decision.holding_days_expected:
            return f"earnings_within_holding_period:{earnings_date.isoformat()}"
        return None

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

    async def _build_stock_context(
        self,
        ticker: str,
        shared_fii_dii: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        market_data = (
            await self.market_tool.get_eod_data_async(ticker)
            if cfg.trading.mode.value == "live"
            else self.market_tool.get_eod_data(ticker)
        )
        fundamentals = self.fundamental_tool.get_fundamentals(ticker)
        stock_context: dict[str, Any] = {
            **market_data,
            "fundamentals": fundamentals,
            "news": self.news_tool.search_news(f"{ticker} stock news India last 7 days"),
            "fii_dii": shared_fii_dii,
        }
        if self.options_tool.is_eligible(ticker):
            stock_context["options"] = self.options_tool.get_options_data(ticker)
        return market_data, fundamentals, stock_context

    async def _analyze_one(
        self,
        ticker: str,
        state: AccountState,
        stats: StatsSnapshot,
        skill_version: str,
        earnings_map: dict[str, date],
        shared_fii_dii: dict[str, Any],
    ) -> ResearchDecision | None:
        async with self._semaphore:
            try:
                blocked_reason = self._fixed_event_block_reason(ticker)
                if blocked_reason is not None:
                    self.log.info("Skipping {} due to {}", ticker, blocked_reason)
                    self._write_research_artifact_payload(
                        ticker,
                        {
                            "status": "skipped",
                            "generated_at": datetime.utcnow().isoformat(),
                            "reason": blocked_reason,
                        },
                    )
                    return None

                market_data, fundamentals, stock_context = await self._build_stock_context(ticker, shared_fii_dii)
                if not self._passes_quick_filter(market_data, fundamentals):
                    self._write_research_artifact_payload(
                        ticker,
                        {
                            "status": "filtered_out",
                            "generated_at": datetime.utcnow().isoformat(),
                            "reason": "quick_filter",
                            "market_data": market_data,
                            "fundamentals": fundamentals,
                        },
                    )
                    return None

                if cfg.trading.mode == TradingMode.BACKTEST and not cfg.backtest.use_llm:
                    decision = self._rules_score(ticker, market_data, fundamentals)
                else:
                    decision = await self.executor.score_stock(
                        ticker=ticker,
                        stock_context=stock_context,
                        state=state,
                        stats=stats,
                        skill_version=skill_version,
                        allow_tool_calls=False,
                    )

                post_score_block = self._apply_post_score_event_rules(decision, ticker, earnings_map)
                if post_score_block is not None:
                    self.log.info("Skipping {} due to {}", ticker, post_score_block)
                    self._write_research_artifact_payload(
                        ticker,
                        {
                            "status": "skipped",
                            "generated_at": datetime.utcnow().isoformat(),
                            "reason": post_score_block,
                            "decision": decision.model_dump(mode="json"),
                        },
                    )
                    return None

                decision.risk_flags = [*decision.risk_flags, *self._event_risk_flags(ticker)]
                if decision.score < cfg.research.min_score_threshold:
                    self._write_research_artifact_payload(
                        ticker,
                        {
                            "status": "below_threshold",
                            "generated_at": datetime.utcnow().isoformat(),
                            "decision": decision.model_dump(mode="json"),
                        },
                    )
                    return None
                return decision
            except Exception as exc:
                self.log.exception("Research analysis failed for {}", ticker)
                self._write_research_artifact_payload(
                    ticker,
                    {
                        "status": "error",
                        "generated_at": datetime.utcnow().isoformat(),
                        "error": str(exc),
                    },
                )
                return None

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

    def _artifact_dir(self) -> Path:
        day_dir = CONTEXT_DIR / "research" / date.today().isoformat()
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir

    def _company_name(self, ticker: str) -> str:
        return self.nifty_loader.name_for(ticker)

    def _write_research_artifact_payload(self, ticker: str, payload: dict[str, Any]) -> None:
        artifact_path = self._artifact_dir() / f"{ticker}.json"
        write_json(artifact_path, payload)

    def _write_research_artifact(self, decision: ResearchDecision, *, status: str = "scored") -> None:
        self._write_research_artifact_payload(
            decision.ticker,
            {
                "status": status,
                "generated_at": datetime.utcnow().isoformat(),
                "decision": decision.model_dump(mode="json"),
            },
        )

    def _mark_shortlist_artifacts(self, shortlist: list[ResearchDecision]) -> None:
        for decision in shortlist:
            self._write_research_artifact(decision, status="shortlisted")

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

    def _briefing_line(self, item: ResearchDecision) -> str:
        thesis = item.confidence_reasoning.strip()
        flags = f" | flags: {', '.join(item.risk_flags)}" if item.risk_flags else ""
        return (
            f"{self._company_name(item.ticker)} ({item.ticker}) | score {item.score:.1f} | {item.setup_type} | "
            f"entry {item.entry_zone.low}-{item.entry_zone.high} | stop {item.stop_price} | "
            f"target {item.target_price} | hold {item.holding_days_expected}d | thesis: {thesis}{flags}"
        )

    def _current_month_trade_count(self, today: date | None = None) -> int:
        today = today or date.today()
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        count = 0
        for item in trades:
            closed_at = item.get("closed_at")
            if not closed_at:
                continue
            try:
                closed_date = datetime.fromisoformat(str(closed_at).replace("Z", "+00:00")).date()
            except ValueError:
                continue
            if closed_date.year == today.year and closed_date.month == today.month:
                count += 1
        return count

    def _is_monthly_analyst_due(self, today: date | None = None) -> bool:
        today = today or date.today()
        loop_cfg = cfg.research.analyst_loop
        if not loop_cfg.enabled or loop_cfg.cadence != "monthly":
            return False
        return today.weekday() == 6 and 1 <= today.day <= 7

    async def run_monthly_analyst_loop_if_due(self, today: date | None = None) -> str | None:
        today = today or date.today()
        if not self._is_monthly_analyst_due(today):
            return None

        trade_count = self._current_month_trade_count(today)
        if trade_count < cfg.research.analyst_loop.min_trades_required:
            self.log.info(
                "Skipping monthly analyst loop: trade_count={} min_required={}",
                trade_count,
                cfg.research.analyst_loop.min_trades_required,
            )
            return None

        self.stats_engine.calculate()
        lessons = await self.lesson_generator.generate()
        await self.telegram.send_text(
            "Monthly analyst loop completed. Review SKILL.md.staging for proposed changes."
        )
        return lessons

    async def _send_briefing(self, shortlist: list[ResearchDecision]) -> None:
        lines = [self._briefing_line(item) for item in shortlist]
        if not lines:
            lines = ["No setups met the threshold today."]
        await self.telegram.send_approval_request(lines)

    async def run(self) -> list[ResearchDecision]:
        state = self._load_state()
        stats = self._load_stats()
        universe = [ticker for ticker in self.nifty_loader.load() if ticker not in self._open_position_tickers(state)]
        skill_version = _current_skill_version()
        earnings_map = self.earnings_calendar.load()
        shared_fii_dii = self.fii_dii_tool.get_fii_dii()
        if cfg.research.async_scan:
            results = await asyncio.gather(
                *[
                    self._analyze_one(ticker, state, stats, skill_version, earnings_map, shared_fii_dii)
                    for ticker in universe
                ]
            )
        else:
            results = []
            for ticker in universe:
                results.append(await self._analyze_one(ticker, state, stats, skill_version, earnings_map, shared_fii_dii))
        decisions = [item for item in results if item is not None]
        for decision in decisions:
            self._write_research_artifact(decision)
        capped = self._sector_capped(decisions, state)
        capacity = max(cfg.trading.max_positions - len(state.positions), 0)
        shortlist = capped[: min(cfg.research.max_shortlist, capacity if capacity else cfg.research.max_shortlist)]
        self._mark_shortlist_artifacts(shortlist)
        self._write_pending_approvals(shortlist)
        await self._send_briefing(shortlist)
        self.log.info("Research run completed with {} shortlisted setups", len(shortlist))
        return shortlist
