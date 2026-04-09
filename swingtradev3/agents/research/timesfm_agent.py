from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from data.timesfm_forecaster import TimesFMForecaster
from data.kite_fetcher import KiteFetcher


class TimesfmAgent(BaseAgent):
    """
    TimesFM forecast integration agent.
    """
    def __init__(self, ticker: str, name: str | None = None) -> None:
        super().__init__(name=name or f"TimesfmAgent_{ticker}")
        self.ticker = ticker
        self.tool = TimesFMForecaster()
        self.kite_fetcher = KiteFetcher()

    async def _run_async_impl(self, ctx) -> Event:
        data = {}
        try:
            candles = await self.kite_fetcher.fetch_async(self.ticker, interval="day")
            if candles is not None and not candles.empty:
                data = self.tool.forecast_price_range(self.ticker, candles["close"], horizon=20)
            else:
                data = {"error": "insufficient_data"}
        except Exception as e:
            # Fallback
            try:
                candles = self.kite_fetcher.fetch(self.ticker, interval="day")
                if candles is not None and not candles.empty:
                    data = self.tool.forecast_price_range(self.ticker, candles["close"], horizon=20)
                else:
                    data = {"error": "insufficient_data"}
            except Exception as inner_e:
                data = {"error": str(inner_e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if self.ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][self.ticker] = {}

        ctx.session.state["stock_data"][self.ticker]["timesfm"] = data

        return Event(
            author=self.name,
            content={"ticker": self.ticker, "timesfm": data},
        )
