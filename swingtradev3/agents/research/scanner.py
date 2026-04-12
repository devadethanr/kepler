from __future__ import annotations

from typing import AsyncGenerator
from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from agents.research.market_data_agent import MarketDataAgent
from agents.research.fundamentals_agent import FundamentalsAgent
from agents.research.sentiment_agent import SentimentAgent
from agents.research.options_agent import OptionsAgent
from agents.research.timesfm_agent import TimesfmAgent

class BatchScannerAgent(BaseAgent):
    """
    Dynamically creates ParallelAgent for qualified stocks.
    Splits into batches (e.g., 10) and runs each batch.
    """
    def __init__(self, name: str = "BatchScannerAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        qualified = ctx.session.state.get("qualified_stocks", [])
        batch_size = cfg.research.filter.batch_size
        
        for i in range(0, len(qualified), batch_size):
            batch = qualified[i:i+batch_size]
            sub_agents = [
                self._create_stock_analyzer(s["ticker"])
                for s in batch
            ]
            
            parallel_scanner = ParallelAgent(
                name=f"ScannerBatch_{i//batch_size}",
                sub_agents=sub_agents,
            )
            
            async for event in parallel_scanner.run_async(ctx):
                # Optionally yield events from sub-agents
                yield event
                
        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Deep analysis completed for {len(qualified)} stocks.")]
            ),
        )

    def _create_stock_analyzer(self, ticker: str) -> SequentialAgent:
        """Create a SequentialAgent for deep analysis of one stock."""
        return SequentialAgent(
            name=f"Analyze_{ticker}",
            sub_agents=[
                MarketDataAgent(ticker),
                FundamentalsAgent(ticker),
                SentimentAgent(ticker),
                OptionsAgent(ticker),
                TimesfmAgent(ticker),
            ],
            description=f"Deep analysis of {ticker}",
        )
