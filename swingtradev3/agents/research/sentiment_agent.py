from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from tools.market.news_search import NewsSearchTool
from tools.analysis.sentiment_analysis import SentimentAnalyzer


class SentimentAgent(BaseAgent):
    """
    News search + social sentiment agent.
    """
    def __init__(self, ticker: str, name: str | None = None) -> None:
        super().__init__(name=name or f"SentimentAgent_{ticker}")
        self.ticker = ticker
        self.news_tool = NewsSearchTool()
        self.sentiment_analyzer = SentimentAnalyzer()

    async def _run_async_impl(self, ctx) -> Event:
        try:
            news = self.news_tool.search_news(f"{self.ticker} stock news today")
            data = self.sentiment_analyzer.analyze_news_list(news.get("results", []))
        except Exception as e:
            data = {"error": str(e)}

        if "stock_data" not in ctx.session.state:
            ctx.session.state["stock_data"] = {}
        if self.ticker not in ctx.session.state["stock_data"]:
            ctx.session.state["stock_data"][self.ticker] = {}

        ctx.session.state["stock_data"][self.ticker]["sentiment"] = data

        return Event(
            author=self.name,
            content={"ticker": self.ticker, "sentiment": data},
        )
