from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from tools.market.market_data import MarketDataTool


class MarketDataAgent(BaseAgent):
    """
    Fetches and analyzes OHLCV and indicators for a given stock.
    """
    def __init__(self, ticker: str, name: str | None = None) -> None:
        super().__init__(name=name or f"MarketDataAgent_{ticker}")
        self.ticker = ticker
        self.tool = MarketDataTool()

    async def _run_async_impl(self, ctx) -> Event:
        # Fetch EOD data asynchronously
        try:
            data = await self.tool.get_eod_data_async(self.ticker)
        except Exception as e:
            # Fallback
            try:
                data = self.tool.get_eod_data(self.ticker)
            except Exception as inner_e:
                data = {"error": str(inner_e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if self.ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][self.ticker] = {}

        ctx.session.state["stock_data"][self.ticker]["technical"] = data

        return Event(
            author=self.name,
            content={"ticker": self.ticker, "technical": data},
        )
