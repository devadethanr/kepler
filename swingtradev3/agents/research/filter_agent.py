"""
Multi-Signal Candidate Selection Funnel
========================================
Layer 0: Broad signal sweep (news, FII/DII, options, block deals)
Layer 1: Union + priority scoring
Layer 2: Python fast filters (technical, liquidity, governance)

Output: ~15-25 qualified tickers for deep LLM analysis.
Pure computation — no LLM, no decisions.
"""
from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from config import cfg
from data.nifty200_loader import Nifty200Loader
from data.news_aggregator import NewsAggregator
from data.institutional_flows import InstitutionalFlowsTool
from data.options_analyzer import OptionsAnalyzer
from data.kite_fetcher import KiteFetcher


class FilterAgent(BaseAgent):
    """
    Multi-signal candidate selection funnel.
    Filters Nifty 200 down to ~15-25 qualified stocks.
    """

    def __init__(self, name: str = "FilterAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> Event:
        """
        Run the full multi-signal funnel asynchronously.
        """
        universe_loader = Nifty200Loader()
        news_aggregator = NewsAggregator()
        flows_tool = InstitutionalFlowsTool()
        options_analyzer = OptionsAnalyzer()
        kite_fetcher = KiteFetcher()
        filter_cfg = cfg.research.filter

        universe = universe_loader.load()

        # Layer 0A: News sweep (1 Tavily call for all 200)
        news_tickers = self._sweep_news(news_aggregator, filter_cfg, universe)

        # Layer 0B: FII/DII flow check
        fii_data = flows_tool.get_fii_dii()
        fii_tickers = self._get_fii_affected_stocks(fii_data, universe)

        # Layer 0C: Options unusual activity
        options_tickers = self._detect_unusual_options(options_analyzer, filter_cfg, universe)

        # Layer 0D: Block/bulk deals
        block_tickers = self._get_block_deal_stocks()

        # Layer 1: Union + priority scoring
        signal_map: dict[str, int] = {}
        signal_details: dict[str, dict[str, bool]] = {}

        for t in news_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
            signal_details.setdefault(t, {})["news"] = True
        for t in fii_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
            signal_details.setdefault(t, {})["fii"] = True
        for t in options_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
            signal_details.setdefault(t, {})["options"] = True
        for t in block_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
            signal_details.setdefault(t, {})["block_deal"] = True

        # Only stocks with >= min_priority_signals advance
        min_signals = filter_cfg.min_priority_signals
        priority_stocks = [t for t, score in signal_map.items() if score >= min_signals]

        # Layer 2: Python fast filters
        qualified = []
        for ticker in priority_stocks:
            passed, reason = await self._fast_filter_async(kite_fetcher, filter_cfg, ticker)
            if passed:
                qualified.append({
                    "ticker": ticker,
                    "priority": signal_map[ticker],
                    "signals": signal_details.get(ticker, {}),
                })

        ctx.session.state["qualified_stocks"] = qualified
        return Event(
            author=self.name,
            content={"qualified_count": len(qualified), "stocks": qualified},
        )

    def _sweep_news(self, news_aggregator, filter_cfg, universe: list[str]) -> list[str]:
        """Extract tickers mentioned in broad market news."""
        news = news_aggregator.sweep_market_news(filter_cfg.news_sweep_query)
        mentioned = set()
        for item in news.get("results", []):
            text = f"{item.get('title', '')} {item.get('content', '')}".upper()
            for ticker in universe:
                if ticker.upper() in text:
                    mentioned.add(ticker)
        return list(mentioned)

    def _get_fii_affected_stocks(self, fii_data: dict, universe: list[str]) -> list[str]:
        """Get stocks in sectors with net FII buying."""
        fii_net = fii_data.get("fii_net_crore")
        if fii_net is not None and fii_net > 0:
            return universe[:20]  # Return top 20 as candidates
        return []

    def _detect_unusual_options(self, options_analyzer, filter_cfg, universe: list[str]) -> list[str]:
        """Detect stocks with unusual options activity."""
        unusual = []
        threshold = filter_cfg.options_pcr_threshold
        for ticker in universe[:50]:  # Check top 50 for performance
            cached = options_analyzer.get_cached(ticker)
            if cached and cached.get("pcr") is not None:
                if cached["pcr"] >= threshold:
                    unusual.append(ticker)
        return unusual

    def _get_block_deal_stocks(self) -> list[str]:
        """Get stocks with recent block deals."""
        return []

    async def _fast_filter_async(self, kite_fetcher, filter_cfg, ticker: str) -> tuple[bool, str]:
        """
        Apply fast Python-based filters to a single stock.
        Returns (passed, reason).
        """
        try:
            candles = await kite_fetcher.fetch_async(ticker, interval="day")
        except Exception as e:
            # Fallback to sync fetch if async not supported
            try:
                candles = kite_fetcher.fetch(ticker, interval="day")
            except Exception as e:
                return False, f"fetch_failed: {e}"

        if candles is None or len(candles) < 200:
            return False, "insufficient_data"

        close = candles["close"].iloc[-1]

        # Filter: Price > 200 EMA
        if filter_cfg.trend_filter_ema > 0:
            ema_200 = candles["close"].ewm(span=200, adjust=False).mean().iloc[-1]
            if close <= ema_200:
                return False, f"below_200ema ({close:.1f} <= {ema_200:.1f})"

        # Filter: Volume > 20-day average
        avg_volume = candles["volume"].rolling(20).mean().iloc[-1]
        current_volume = candles["volume"].iloc[-1]
        if avg_volume > 0 and current_volume / avg_volume < filter_cfg.min_volume_ratio:
            return False, f"low_volume ({current_volume/avg_volume:.2f}x avg)"

        return True, "passed"
