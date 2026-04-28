from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
import asyncio

from tools.market.options_data import OptionsDataTool


class OptionsAgent(BaseAgent):
    """
    Options chain analysis agent.
    """
    def __init__(self, ticker: str) -> None:
        super().__init__(name=f"OptionsAgent_{ticker}")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        ticker = self.name.split("_")[-1]
        tool = OptionsDataTool()
        
        try:
            data = await asyncio.to_thread(tool.get_options_data, ticker)
        except Exception as e:
            data = {"error": str(e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][ticker] = {}

        ctx.session.state["stock_data"][ticker]["options"] = data

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Options data analyzed for {ticker}")]
            ),
        )
