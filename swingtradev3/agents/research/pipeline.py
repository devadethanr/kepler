from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, AsyncGenerator

from google.adk.agents import SequentialAgent, BaseAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from agents.research.regime_agent import RegimeAgent
from agents.research.filter_agent import FilterAgent
from agents.research.scanner import BatchScannerAgent
from agents.research.scorer_agent import ScorerAgent
from agents.research.knowledge_graph_agent import KnowledgeGraphAgent

from paths import CONTEXT_DIR
from storage import write_json


class ResultsSaverAgent(BaseAgent):
    """
    Saves the final research results to context files.
    """
    def __init__(self, name: str = "ResultsSaverAgent") -> None:
        super().__init__(name=name)

    def _build_pending_approvals(
        self,
        *,
        shortlist: list[dict[str, Any]],
        scan_date: str,
        analyzed_at: datetime,
    ) -> list[dict[str, Any]]:
        expires_at = analyzed_at + timedelta(hours=cfg.execution.approval_timeout_hours)
        payload: list[dict[str, Any]] = []
        for item in shortlist:
            ticker = str(item.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            payload.append(
                {
                    "ticker": ticker,
                    "score": item.get("score"),
                    "setup_type": item.get("setup_type"),
                    "entry_zone": item.get("entry_zone"),
                    "stop_price": item.get("stop_price"),
                    "target_price": item.get("target_price"),
                    "holding_days_expected": item.get("holding_days_expected"),
                    "confidence_reasoning": item.get("confidence_reasoning"),
                    "risk_flags": item.get("risk_flags", []),
                    "sector": item.get("sector"),
                    "created_at": analyzed_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "research_date": item.get("research_date") or scan_date,
                    "skill_version": item.get("skill_version"),
                }
            )
        return payload

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        scan_date = date.today().isoformat()
        regime = ctx.session.state.get("regime", {})
        qualified_stocks = ctx.session.state.get("qualified_stocks", [])
        shortlist = ctx.session.state.get("shortlist", [])
        stock_data = ctx.session.state.get("stock_data", {})
        scan_results = ctx.session.state.get("scan_results", [])

        analyzed_at = datetime.now()
        result = {
            "scan_date": scan_date,
            "regime": regime,
            "total_screened": 200,
            "qualified_count": len(qualified_stocks),
            "shortlist": shortlist,
            "analyzed_at": analyzed_at.isoformat(),
        }

        # Save to context
        research_dir = CONTEXT_DIR / "research" / scan_date
        research_dir.mkdir(parents=True, exist_ok=True)
        write_json(research_dir / "scan_result.json", result)
        write_json(
            CONTEXT_DIR / "pending_approvals.json",
            self._build_pending_approvals(
                shortlist=shortlist,
                scan_date=scan_date,
                analyzed_at=analyzed_at,
            ),
        )

        # Save individual stock analyses
        for stock in scan_results:
            ticker = stock.get("ticker")
            if not ticker:
                continue
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

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Research results saved to {research_dir}")]
            ),
        )


research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[
        RegimeAgent(),
        FilterAgent(),
        BatchScannerAgent(),
        ScorerAgent(),
        ResultsSaverAgent(),
        KnowledgeGraphAgent(),
    ],
    description="Complete research pipeline: regime → filter → scan → score → save → knowledge graph",
)
