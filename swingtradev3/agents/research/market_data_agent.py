from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
import asyncio

from tools.market.market_data import MarketDataTool


class MarketDataAgent(BaseAgent):
    """
    Fetches and analyzes OHLCV and indicators for a given stock.
    """
    def __init__(self, ticker: str) -> None:
        super().__init__(name=f"MarketDataAgent_{ticker}")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        ticker = self.name.split("_")[-1]
        tool = MarketDataTool()
        
        try:
            data = await tool.get_eod_data_async(ticker)
        except Exception as e:
            try:
                data = await asyncio.to_thread(tool.get_eod_data, ticker)
            except Exception as inner_e:
                data = {"error": str(inner_e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][ticker] = {}

        ctx.session.state["stock_data"][ticker]["technical"] = data

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Market data fetched for {ticker}")]
            ),
        )
