"""KnowledgeGraphAgent — Memgraph-only context graph maintenance after research."""
from __future__ import annotations

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from context_graph.repository import ContextGraphRepository, GraphUnavailableError


class KnowledgeGraphAgent(BaseAgent):
    """
    ADK Agent: Keeps stock and sector nodes warm in the context graph.
    ResultsSaverAgent writes the full research run; this agent performs a
    lightweight Memgraph pass and never writes retired markdown/wiki files.
    """

    def __init__(self, name: str = "KnowledgeGraphAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        scan_results = ctx.session.state.get("scan_results", [])
        shortlist = ctx.session.state.get("shortlist", [])

        if not scan_results:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text="No scan results to update knowledge graph.")]
                ),
            )
            return

        shortlisted_tickers = {str(s.get("ticker")).upper() for s in shortlist if s.get("ticker")}
        sectors_to_update: set[str] = set()
        updated_count = 0
        graph: ContextGraphRepository | None = None
        try:
            graph = ContextGraphRepository()
            for stock in scan_results:
                ticker = str(stock.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                payload = dict(stock)
                payload["shortlisted"] = ticker in shortlisted_tickers
                sector = stock.get("sector")
                if sector:
                    sectors_to_update.add(str(sector))
                graph.upsert_stock(
                    ticker,
                    sector=str(sector) if sector else None,
                    payload=payload,
                    source="knowledge_graph_agent",
                )
                updated_count += 1
        except GraphUnavailableError:
            updated_count = 0
        finally:
            if graph is not None:
                graph.close()

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(
                    text=(
                        f"Context graph checked: {updated_count} stocks, "
                        f"{len(sectors_to_update)} sectors."
                    )
                )]
            ),
        )
