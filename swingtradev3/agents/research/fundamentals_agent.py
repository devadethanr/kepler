from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from tools.market.fundamental_data import FundamentalDataTool


class FundamentalsAgent(BaseAgent):
    """
    Fetches fundamental analysis for a given stock.
    """
    def __init__(self, ticker: str, name: str | None = None) -> None:
        super().__init__(name=name or f"FundamentalsAgent_{ticker}")
        self.ticker = ticker
        self.tool = FundamentalDataTool()

    async def _run_async_impl(self, ctx) -> Event:
        try:
            data = self.tool.get_fundamentals(self.ticker)
        except Exception as e:
            data = {"error": str(e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if self.ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][self.ticker] = {}

        ctx.session.state["stock_data"][self.ticker]["fundamentals"] = data

        return Event(
            author=self.name,
            content={"ticker": self.ticker, "fundamentals": data},
        )
