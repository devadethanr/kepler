from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

from data.timesfm_forecaster import TimesFMForecaster
from data.kite_fetcher import KiteFetcher


class TimesfmAgent(BaseAgent):
    """
    TimesFM forecast integration agent.
    """
    def __init__(self, ticker: str) -> None:
        super().__init__(name=f"TimesfmAgent_{ticker}")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        ticker = self.name.split("_")[-1]
        tool = TimesFMForecaster()
        kite_fetcher = KiteFetcher()
        
        data = {}
        try:
            candles = await kite_fetcher.fetch_async(ticker, interval="day")
            if candles is not None and not candles.empty:
                data = tool.forecast_price_range(ticker, candles["close"], horizon=20)
            else:
                data = {"error": "insufficient_data"}
        except Exception as e:
            try:
                candles = kite_fetcher.fetch(ticker, interval="day")
                if candles is not None and not candles.empty:
                    data = tool.forecast_price_range(ticker, candles["close"], horizon=20)
                else:
                    data = {"error": "insufficient_data"}
            except Exception as inner_e:
                data = {"error": str(inner_e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][ticker] = {}

        ctx.session.state["stock_data"][ticker]["timesfm"] = data

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"TimesFM forecast generated for {ticker}")]
            ),
        )
