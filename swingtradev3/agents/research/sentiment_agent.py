from __future__ import annotations

from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
import asyncio

from tools.market.news_search import NewsSearchTool
from tools.analysis.sentiment_analysis import SentimentAnalyzer


class SentimentAgent(BaseAgent):
    """
    News search + social sentiment agent.
    """
    def __init__(self, ticker: str) -> None:
        super().__init__(name=f"SentimentAgent_{ticker}")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        ticker = self.name.split("_")[-1]
        news_tool = NewsSearchTool()
        sentiment_analyzer = SentimentAnalyzer()
        
        try:
            news = await asyncio.to_thread(news_tool.search_news, f"{ticker} stock news today")
            data = await asyncio.to_thread(sentiment_analyzer.analyze_news_list, news.get("results", []))
        except Exception as e:
            data = {"error": str(e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][ticker] = {}

        ctx.session.state["stock_data"][ticker]["sentiment"] = data

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Sentiment analyzed for {ticker}")]
            ),
        )
