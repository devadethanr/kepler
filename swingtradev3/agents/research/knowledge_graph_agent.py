"""
KnowledgeGraphAgent — Updates the Karpathy-style Markdown Wiki after each scan.

Runs as the last step in the research pipeline:
  RegimeAgent → FilterAgent → ScannerAgent → ScorerAgent → ResultsSaverAgent → KnowledgeGraphAgent

For each scored stock, this agent:
1. Upserts the stock wiki note (appends scan history row)
2. Updates the sector note
3. Rebuilds _index.json and _graph.json
"""
from __future__ import annotations

from datetime import date
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from knowledge.wiki_renderer import (
    upsert_stock_note,
    upsert_sector_note,
)


class KnowledgeGraphAgent(BaseAgent):
    """
    ADK Agent: Updates the Knowledge Graph wiki after a research scan.
    Reads scan_results from session state and writes to context/knowledge/wiki/.
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

        # Build shortlisted ticker set for quick lookup
        shortlisted_tickers = {s.get("ticker") for s in shortlist if s.get("ticker")}
        sectors_to_update: set[str] = set()
        updated_count = 0

        for stock in scan_results:
            ticker = stock.get("ticker")
            if not ticker:
                continue

            score = stock.get("score", 0.0)
            setup_type = stock.get("setup_type", "unknown")
            sector = stock.get("sector")
            is_shortlisted = ticker in shortlisted_tickers

            try:
                upsert_stock_note(
                    ticker=ticker,
                    score=score,
                    setup_type=setup_type,
                    shortlisted=is_shortlisted,
                    sector=sector,
                )
                updated_count += 1

                if sector:
                    sectors_to_update.add(sector)
            except Exception as e:
                print(f"KG: Failed to update {ticker}: {e}")

        # Update sector notes
        for sector in sectors_to_update:
            try:
                upsert_sector_note(sector)
            except Exception as e:
                print(f"KG: Failed to update sector {sector}: {e}")

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(
                    text=f"Knowledge graph updated: {updated_count} stocks, {len(sectors_to_update)} sectors."
                )]
            ),
        )
