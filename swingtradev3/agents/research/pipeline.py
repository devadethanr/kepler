from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from google.adk.agents import SequentialAgent, BaseAgent
from google.adk.events import Event

from agents.research.regime_agent import RegimeAgent
from agents.research.filter_agent import FilterAgent
from agents.research.scanner import BatchScannerAgent
from agents.research.scorer_agent import ScorerAgent

from paths import CONTEXT_DIR
from storage import write_json


class ResultsSaverAgent(BaseAgent):
    """
    Saves the final research results to context files.
    """
    def __init__(self, name: str = "ResultsSaverAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> Event:
        scan_date = date.today().isoformat()
        regime = ctx.session.state.get("regime", {})
        qualified_stocks = ctx.session.state.get("qualified_stocks", [])
        shortlist = ctx.session.state.get("shortlist", [])
        stock_data = ctx.session.state.get("stock_data", {})
        scan_results = ctx.session.state.get("scan_results", [])

        result = {
            "scan_date": scan_date,
            "regime": regime,
            "total_screened": 200,
            "qualified_count": len(qualified_stocks),
            "shortlist": shortlist,
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        # Save to context
        research_dir = CONTEXT_DIR / "research" / scan_date
        research_dir.mkdir(parents=True, exist_ok=True)
        write_json(research_dir / "scan_result.json", result)

        # Save individual stock analyses
        for stock in scan_results:
            ticker = stock["ticker"]
            stock_info = {
                "ticker": ticker,
                "score": stock.get("score"),
                "setup_type": stock.get("setup_type"),
                "entry_zone": stock.get("entry_zone"),
                "stop_price": stock.get("stop_price"),
                "target_price": stock.get("target_price"),
                "reasoning": stock.get("reasoning"),
                "bull_case": stock.get("bull_case"),
                "bear_case": stock.get("bear_case"),
                "signals": stock.get("signals", {}),
                "technical": stock_data.get(ticker, {}).get("technical", {}),
                "fundamentals": stock_data.get(ticker, {}).get("fundamentals", {}),
                "sentiment": stock_data.get(ticker, {}).get("sentiment", {}),
                "options": stock_data.get(ticker, {}).get("options", {}),
                "timesfm": stock_data.get(ticker, {}).get("timesfm", {}),
            }
            write_json(research_dir / f"{ticker}.json", stock_info)

        return Event(
            author=self.name,
            content={"message": f"Saved {len(scan_results)} analyses to {research_dir}"},
        )


research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[
        RegimeAgent(),
        FilterAgent(),
        BatchScannerAgent(),
        ScorerAgent(),
        ResultsSaverAgent(),
    ],
    description="Complete research pipeline: regime → filter → scan → score → save",
)
