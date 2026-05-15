from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, AsyncGenerator
from zoneinfo import ZoneInfo

from google.adk.agents import SequentialAgent, BaseAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from context_graph.repository import ContextGraphRepository, GraphUnavailableError
from data.nifty200_loader import Nifty200Loader
from memory.db import session_scope
from memory.projections import project_all_managed_files
from memory.repository import MemoryRepository
from agents.research.regime_agent import RegimeAgent
from agents.research.filter_agent import FilterAgent
from agents.research.scanner import BatchScannerAgent
from agents.research.scorer_agent import ScorerAgent
from agents.research.knowledge_graph_agent import KnowledgeGraphAgent

IST = ZoneInfo("Asia/Kolkata")


class ResultsSaverAgent(BaseAgent):
    """
    Saves final research results to Memgraph and Postgres-backed approvals.
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
        universe = {ticker.upper() for ticker in Nifty200Loader().load()}
        payload: list[dict[str, Any]] = []
        for item in shortlist:
            ticker = str(item.get("ticker") or "").strip().upper()
            if not ticker or ticker not in universe:
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
                    "approved": None,
                    "execution_requested": False,
                    "execution_request_id": None,
                    "status": "pending",
                    "created_at": analyzed_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "research_date": item.get("research_date") or scan_date,
                    "skill_version": item.get("skill_version"),
                }
            )
        return payload

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, Any]:
        analyzed_at = datetime.now(IST)
        scan_date = analyzed_at.date().isoformat()
        regime = ctx.session.state.get("regime", {})
        qualified_stocks = ctx.session.state.get("qualified_stocks", [])
        shortlist = ctx.session.state.get("shortlist", [])
        stock_data = ctx.session.state.get("stock_data", {})
        scan_results = ctx.session.state.get("scan_results", [])
        diagnostics = ctx.session.state.get("scan_diagnostics", {})
        total_screened = int(
            diagnostics.get("total_screened")
            or diagnostics.get("screened_count")
            or len(scan_results)
            or len(qualified_stocks)
        )
        run_id = f"research:{scan_date}"

        # Phase 11: Write scan results to Memgraph context graph
        graph_repo: ContextGraphRepository | None = None
        try:
            graph_repo = ContextGraphRepository()
            graph_repo.upsert_research_run(
                run_id=run_id,
                scan_date=scan_date,
                analyzed_at=analyzed_at,
                regime=regime,
                diagnostics=diagnostics or {},
                qualified_count=len(qualified_stocks),
                total_screened=total_screened,
                shortlist=shortlist,
                scan_results=scan_results,
                stock_data=stock_data,
            )
        except GraphUnavailableError:
            pass
        finally:
            if graph_repo is not None:
                graph_repo.close()

        pending_approvals = self._build_pending_approvals(
            shortlist=shortlist,
            scan_date=scan_date,
            analyzed_at=analyzed_at,
        )
        try:
            with session_scope() as session:
                MemoryRepository(session).replace_pending_approvals(
                    pending_approvals,
                    source="research_pipeline",
                )
            project_all_managed_files()
        except Exception as exc:
            print(f"Research approval persistence failed: {exc}")

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text="Research results saved to context graph and approvals.")]
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
