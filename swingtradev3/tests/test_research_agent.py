from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

from swingtradev3.agents.research_agent import ResearchAgent
from swingtradev3.data.corporate_actions import CorporateActionsStore
from swingtradev3.data.earnings_calendar import EarningsCalendar
from swingtradev3.models import AccountState, CorporateAction, ResearchDecision, StatsSnapshot


class StubMarketTool:
    async def get_eod_data_async(self, ticker: str) -> dict[str, object]:
        return self.get_eod_data(ticker)

    def get_eod_data(self, ticker: str) -> dict[str, object]:
        return {
            "ticker": ticker,
            "close": 100.0,
            "volume": 10_000_000,
            "above_200ema": True,
            "trend_strong": True,
            "outperforming_index": True,
            "accumulation_flag": True,
            "base_weeks": 8,
            "stop_distance": 5.0,
            "proximity_to_52w_high_pct": 2.0,
        }


class StubFundamentalTool:
    def __init__(self, sector_map: dict[str, str] | None = None) -> None:
        self.sector_map = sector_map or {}

    def get_fundamentals(self, ticker: str) -> dict[str, object]:
        return {
            "market_cap_cr": 10_000.0,
            "promoter_pledge_pct": 0.0,
            "sector": self.sector_map.get(ticker, "Technology"),
        }


class StubNewsTool:
    def search_news(self, query: str) -> dict[str, object]:
        return {"query": query, "results": []}


class StubFiiDiiTool:
    def __init__(self) -> None:
        self.calls = 0

    def get_fii_dii(self) -> dict[str, object]:
        self.calls += 1
        return {"fii_net_crore": 0, "dii_net_crore": 0}


class StubOptionsTool:
    def __init__(self, eligible: set[str] | None = None) -> None:
        self.eligible = eligible or set()
        self.calls: list[str] = []

    def is_eligible(self, ticker: str) -> bool:
        return ticker in self.eligible

    def get_options_data(self, ticker: str) -> dict[str, object]:
        self.calls.append(ticker)
        return {"ticker": ticker}


class StubTelegram:
    def __init__(self) -> None:
        self.lines: list[str] = []

    async def send_approval_request(self, lines: list[str]) -> None:
        self.lines = lines
        return None

    async def send_text(self, text: str, level: object | None = None) -> None:
        self.lines = [text]
        return None


class StubUniverse:
    def __init__(self, tickers: list[str], name_map: dict[str, str] | None = None) -> None:
        self.tickers = tickers
        self.name_map = name_map or {}

    def load(self) -> list[str]:
        return self.tickers

    def name_for(self, ticker: str) -> str:
        return self.name_map.get(ticker, ticker)


class StubExecutor:
    def __init__(self, scores: dict[str, float], sectors: dict[str, str] | None = None) -> None:
        self.scores = scores
        self.sectors = sectors or {}

    async def score_stock(
        self,
        ticker: str,
        stock_context: dict[str, object],
        state: object,
        stats: object,
        skill_version: str,
        allow_tool_calls: bool = True,
    ) -> ResearchDecision:
        close = float(stock_context["close"])
        return ResearchDecision(
            ticker=ticker,
            score=self.scores[ticker],
            setup_type="breakout",
            entry_zone={"low": close * 0.99, "high": close * 1.01},
            stop_price=close - 5,
            target_price=close + 10,
            holding_days_expected=10,
            confidence_reasoning="stub",
            risk_flags=[],
            sector=self.sectors.get(ticker, "Technology"),
            research_date=date.today(),
            skill_version=skill_version,
            current_price=close,
        )


class StubStatsEngine:
    def __init__(self) -> None:
        self.called = False

    def calculate(self) -> StatsSnapshot:
        self.called = True
        return StatsSnapshot()


class StubLessonGenerator:
    def __init__(self, lessons: str = "lesson proposal") -> None:
        self.lessons = lessons
        self.called = False

    async def generate(self) -> str:
        self.called = True
        return self.lessons


class IsolatedResearchAgent(ResearchAgent):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._pending_payload: list[object] = []
        self._artifacts: dict[str, dict[str, object]] = {}

    def _load_state(self) -> AccountState:
        return AccountState()

    def _load_stats(self) -> StatsSnapshot:
        return StatsSnapshot()

    def _write_research_artifact_payload(self, ticker: str, payload: dict[str, object]) -> None:
        self._artifacts[ticker] = payload

    def _write_pending_approvals(self, shortlist: list[ResearchDecision]) -> list[object]:
        self._pending_payload = shortlist
        return shortlist


def _build_agent(
    *,
    tickers: list[str],
    scores: dict[str, float],
    temp_dir: Path,
    earnings: dict[str, date] | None = None,
    corporate_actions: list[CorporateAction] | None = None,
    sectors: dict[str, str] | None = None,
    names: dict[str, str] | None = None,
    option_eligible: set[str] | None = None,
) -> IsolatedResearchAgent:
    earnings_store = EarningsCalendar(cache_path=temp_dir / "earnings_calendar.json")
    earnings_store.store(earnings or {})
    corporate_store = CorporateActionsStore(cache_path=temp_dir / "corporate_actions.json")
    corporate_store.store(corporate_actions or [])
    agent = IsolatedResearchAgent(
        market_tool=StubMarketTool(),
        fundamental_tool=StubFundamentalTool(sector_map=sectors),
        news_tool=StubNewsTool(),
        fii_dii_tool=StubFiiDiiTool(),
        options_tool=StubOptionsTool(eligible=option_eligible),
        executor=StubExecutor(scores=scores, sectors=sectors),
        telegram=StubTelegram(),
        nifty_loader=StubUniverse(tickers, name_map=names),
        earnings_calendar=earnings_store,
        corporate_actions=corporate_store,
    )
    agent._is_near_fno_expiry = lambda today=None: False  # type: ignore[method-assign]
    return agent


def test_research_agent_skips_upcoming_earnings(tmp_path: Path) -> None:
    agent = _build_agent(
        tickers=["INFY"],
        scores={"INFY": 9.0},
        temp_dir=tmp_path,
        earnings={"INFY": date.today() + timedelta(days=5)},
    )

    shortlist = asyncio.run(agent.run())

    assert shortlist == []
    assert agent._artifacts["INFY"]["status"] == "skipped"
    assert "earnings_within_holding_period" in str(agent._artifacts["INFY"]["reason"])


def test_research_agent_skips_upcoming_corporate_actions(tmp_path: Path) -> None:
    agent = _build_agent(
        tickers=["SBIN"],
        scores={"SBIN": 9.0},
        temp_dir=tmp_path,
        corporate_actions=[
            CorporateAction(
                ticker="SBIN",
                action_type="split",
                ex_date=date.today() + timedelta(days=2),
                value=4.0,
            )
        ],
    )

    shortlist = asyncio.run(agent.run())

    assert shortlist == []
    assert agent._artifacts["SBIN"]["status"] == "skipped"
    assert "upcoming_corporate_actions:split" == agent._artifacts["SBIN"]["reason"]


def test_research_agent_flags_dividend_in_shortlist_and_briefing(tmp_path: Path) -> None:
    telegram = StubTelegram()
    earnings_store = EarningsCalendar(cache_path=tmp_path / "earnings_calendar.json")
    earnings_store.store({})
    corporate_store = CorporateActionsStore(cache_path=tmp_path / "corporate_actions.json")
    corporate_store.store(
        [
            CorporateAction(
                ticker="SBIN",
                action_type="dividend",
                ex_date=date.today() + timedelta(days=2),
                value=4.0,
            )
        ]
    )
    agent = IsolatedResearchAgent(
        market_tool=StubMarketTool(),
        fundamental_tool=StubFundamentalTool(),
        news_tool=StubNewsTool(),
        fii_dii_tool=StubFiiDiiTool(),
        options_tool=StubOptionsTool(),
        executor=StubExecutor(scores={"SBIN": 9.0}),
        telegram=telegram,
        nifty_loader=StubUniverse(["SBIN"]),
        earnings_calendar=earnings_store,
        corporate_actions=corporate_store,
    )
    agent._is_near_fno_expiry = lambda today=None: False  # type: ignore[method-assign]

    shortlist = asyncio.run(agent.run())

    assert [item.ticker for item in shortlist] == ["SBIN"]
    assert shortlist[0].risk_flags == [f"upcoming_dividend:{(date.today() + timedelta(days=2)).isoformat()}"]
    assert "hold 10d" in telegram.lines[0]
    assert "thesis: stub" in telegram.lines[0]
    assert "flags: upcoming_dividend:" in telegram.lines[0]


def test_research_agent_briefing_uses_company_name(tmp_path: Path) -> None:
    agent = _build_agent(
        tickers=["INFY"],
        scores={"INFY": 9.0},
        temp_dir=tmp_path,
        names={"INFY": "Infosys Ltd"},
    )

    shortlist = asyncio.run(agent.run())

    assert [item.ticker for item in shortlist] == ["INFY"]
    assert "Infosys Ltd (INFY)" in agent.telegram.lines[0]


def test_research_agent_applies_sector_cap(tmp_path: Path) -> None:
    agent = _build_agent(
        tickers=["INFY", "TCS", "RELIANCE"],
        scores={"INFY": 9.3, "TCS": 9.1, "RELIANCE": 9.0},
        temp_dir=tmp_path,
        sectors={"INFY": "Technology", "TCS": "Technology", "RELIANCE": "Energy"},
    )

    shortlist = asyncio.run(agent.run())

    tickers = [item.ticker for item in shortlist]

    assert "RELIANCE" in tickers
    assert len([item for item in shortlist if item.sector == "Technology"]) <= 2


def test_research_agent_blocks_near_fno_expiry(tmp_path: Path) -> None:
    agent = _build_agent(
        tickers=["INFY"],
        scores={"INFY": 9.0},
        temp_dir=tmp_path,
    )
    agent._is_near_fno_expiry = lambda today=None: True  # type: ignore[method-assign]

    shortlist = asyncio.run(agent.run())

    assert shortlist == []
    assert agent._artifacts["INFY"]["reason"] == "near_fno_expiry"


def test_research_agent_only_adds_options_context_for_nifty50_names(tmp_path: Path) -> None:
    options_tool = StubOptionsTool(eligible={"INFY"})
    fii_dii_tool = StubFiiDiiTool()
    agent = IsolatedResearchAgent(
        market_tool=StubMarketTool(),
        fundamental_tool=StubFundamentalTool(),
        news_tool=StubNewsTool(),
        fii_dii_tool=fii_dii_tool,
        options_tool=options_tool,
        executor=StubExecutor(scores={"INFY": 9.0, "SBIN": 9.0}),
        telegram=StubTelegram(),
        nifty_loader=StubUniverse(["INFY", "SBIN"]),
        earnings_calendar=EarningsCalendar(cache_path=tmp_path / "earnings_calendar.json"),
        corporate_actions=CorporateActionsStore(cache_path=tmp_path / "corporate_actions.json"),
    )
    agent._is_near_fno_expiry = lambda today=None: False  # type: ignore[method-assign]

    shortlist = asyncio.run(agent.run())

    assert [item.ticker for item in shortlist] == ["INFY", "SBIN"]
    assert options_tool.calls == ["INFY"]
    assert fii_dii_tool.calls == 1


def test_monthly_analyst_loop_runs_only_when_due_and_trade_count_is_met(tmp_path: Path) -> None:
    stats_engine = StubStatsEngine()
    lesson_generator = StubLessonGenerator("proposed lesson")
    telegram = StubTelegram()
    agent = IsolatedResearchAgent(
        market_tool=StubMarketTool(),
        fundamental_tool=StubFundamentalTool(),
        news_tool=StubNewsTool(),
        fii_dii_tool=StubFiiDiiTool(),
        options_tool=StubOptionsTool(),
        executor=StubExecutor(scores={}),
        telegram=telegram,
        nifty_loader=StubUniverse([]),
        earnings_calendar=EarningsCalendar(cache_path=tmp_path / "earnings_calendar.json"),
        corporate_actions=CorporateActionsStore(cache_path=tmp_path / "corporate_actions.json"),
        stats_engine=stats_engine,
        lesson_generator=lesson_generator,
    )
    agent._is_near_fno_expiry = lambda today=None: False  # type: ignore[method-assign]
    agent._current_month_trade_count = lambda today=None: 8  # type: ignore[method-assign]

    lessons = asyncio.run(agent.run_monthly_analyst_loop_if_due(date(2026, 3, 1)))

    assert lessons == "proposed lesson"
    assert stats_engine.called is True
    assert lesson_generator.called is True
    assert "Monthly analyst loop completed" in telegram.lines[0]


def test_monthly_analyst_loop_skips_when_not_due(tmp_path: Path) -> None:
    stats_engine = StubStatsEngine()
    lesson_generator = StubLessonGenerator("proposed lesson")
    agent = IsolatedResearchAgent(
        market_tool=StubMarketTool(),
        fundamental_tool=StubFundamentalTool(),
        news_tool=StubNewsTool(),
        fii_dii_tool=StubFiiDiiTool(),
        options_tool=StubOptionsTool(),
        executor=StubExecutor(scores={}),
        telegram=StubTelegram(),
        nifty_loader=StubUniverse([]),
        earnings_calendar=EarningsCalendar(cache_path=tmp_path / "earnings_calendar.json"),
        corporate_actions=CorporateActionsStore(cache_path=tmp_path / "corporate_actions.json"),
        stats_engine=stats_engine,
        lesson_generator=lesson_generator,
    )
    agent._is_near_fno_expiry = lambda today=None: False  # type: ignore[method-assign]

    lessons = asyncio.run(agent.run_monthly_analyst_loop_if_due(date(2026, 3, 2)))

    assert lessons is None
    assert stats_engine.called is False
    assert lesson_generator.called is False
