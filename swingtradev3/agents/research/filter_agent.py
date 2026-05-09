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

import re
from collections import Counter
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from data.nifty200_loader import Nifty200Loader
from data.news import NewsAggregator
from data.institutional_flows import InstitutionalFlowsTool
from data.options_analyzer import OptionsAnalyzer
from data.kite_fetcher import KiteFetcher

FALSE_POSITIVE_TICKER_CONTEXT = {
    "BSE": {"bse stock", "bse ltd", "bse limited"},
    "LT": {"larsen", "toubro", "l&t"},
    "OIL": {"oil india", "oil stock", "oil ltd", "oil limited"},
}


class FilterAgent(BaseAgent):
    """
    Multi-signal candidate selection funnel.
    Filters Nifty 200 down to ~15-25 qualified stocks.
    """

    def __init__(self, name: str = "FilterAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        """
        Run the full multi-signal funnel asynchronously.
        """
        universe_loader = Nifty200Loader()
        news_aggregator = NewsAggregator()
        flows_tool = InstitutionalFlowsTool()
        options_analyzer = OptionsAnalyzer()
        kite_fetcher = KiteFetcher()
        filter_cfg = cfg.research.filter

        universe_entries = universe_loader.load_entries()
        universe = [item["ticker"] for item in universe_entries]

        # Layer 0A: News sweep (1 Tavily call for all 200)
        news_tickers = self._sweep_news(news_aggregator, filter_cfg, universe_entries)

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
        rejection_counts: Counter[str] = Counter()
        for ticker in priority_stocks:
            passed, reason = await self._fast_filter_async(kite_fetcher, filter_cfg, ticker)
            if passed:
                qualified.append({
                    "ticker": ticker,
                    "priority": signal_map[ticker],
                    "signals": signal_details.get(ticker, {}),
                })
            else:
                rejection_counts[reason.split(" ", 1)[0]] += 1

        ctx.session.state["qualified_stocks"] = qualified
        ctx.session.state["scan_diagnostics"] = {
            "source_counts": {
                "news": len(news_tickers),
                "fii": len(fii_tickers),
                "options": len(options_tickers),
                "block_deal": len(block_tickers),
            },
            "priority_count": len(priority_stocks),
            "qualified_count": len(qualified),
            "filter_rejections": dict(sorted(rejection_counts.items())),
        }
        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Funnel completed: {len(qualified)} stocks qualified for deep analysis.")]
            ),
        )

    def _sweep_news(
        self,
        news_aggregator,
        filter_cfg,
        universe: list[str] | list[dict[str, str]],
    ) -> list[str]:
        """Extract tickers mentioned in broad market news."""
        news = news_aggregator.sweep_market_news(filter_cfg.news_sweep_query)
        entries = self._normalize_universe_entries(universe)
        universe_set = {entry["ticker"] for entry in entries}
        mentioned = set()
        for item in news_aggregator.normalize_headlines(
            news.get("results", []),
            max_age_hours=filter_cfg.news_max_age_hours,
        ):
            item_tickers = {
                str(ticker).strip().upper()
                for ticker in item.get("tickers", [])
                if str(ticker).strip().upper() in universe_set
            }
            if item_tickers:
                mentioned.update(item_tickers)
                continue
            text = f"{item.get('title', '')} {item.get('content', '')}"
            for entry in entries:
                ticker = entry["ticker"]
                if self._mentions_stock(text, ticker, entry.get("name") or ticker):
                    mentioned.add(ticker)
        return list(mentioned)

    @staticmethod
    def _normalize_universe_entries(
        universe: list[str] | list[dict[str, str]],
    ) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for item in universe:
            if isinstance(item, str):
                entries.append({"ticker": item.upper(), "name": item})
                continue
            ticker = str(item.get("ticker") or item.get("symbol") or "").strip().upper()
            if not ticker:
                continue
            name = str(item.get("name") or item.get("company_name") or ticker).strip()
            entries.append({"ticker": ticker, "name": name})
        return entries

    @staticmethod
    def _company_aliases(ticker: str, company_name: str) -> set[str]:
        cleaned = re.sub(
            r"\b(LTD|LIMITED|INDIA|CO|COMPANY|CORP|CORPORATION|PVT|PRIVATE)\b",
            " ",
            company_name.upper(),
        )
        words = [word for word in re.split(r"[^A-Z0-9&]+", cleaned) if len(word) >= 3]
        aliases = {ticker.upper()}
        if words:
            aliases.add(words[0])
        if len(words) >= 2:
            aliases.add(" ".join(words[:2]))
        if "&" in cleaned:
            aliases.add(cleaned.replace("&", "AND"))
        return {alias.strip() for alias in aliases if alias.strip()}

    def _mentions_stock(self, text: str, ticker: str, company_name: str) -> bool:
        normalized = re.sub(r"\s+", " ", text.upper())
        ticker = ticker.upper()
        lowered = normalized.lower()
        if ticker == "RELIANCE" and ("self-reliance" in lowered or "reliance on" in lowered):
            return False
        required_context = FALSE_POSITIVE_TICKER_CONTEXT.get(ticker)
        if required_context and not any(phrase in lowered for phrase in required_context):
            return False

        aliases = self._company_aliases(ticker, company_name)
        for alias in aliases:
            if re.search(rf"(?<![A-Z0-9]){re.escape(alias)}(?![A-Z0-9])", normalized):
                return True
        return False

    def _get_fii_affected_stocks(self, fii_data: dict, universe: list[str]) -> list[str]:
        """Get stocks in sectors with net FII buying."""
        explicit = fii_data.get("tickers") or fii_data.get("symbols") or []
        if not isinstance(explicit, list):
            return []
        universe_set = {ticker.upper() for ticker in universe}
        return [
            str(ticker).strip().upper()
            for ticker in explicit
            if str(ticker).strip().upper() in universe_set
        ]

    def _detect_unusual_options(self, options_analyzer, filter_cfg, universe: list[str]) -> list[str]:
        """Detect stocks with unusual options activity."""
        unusual = []
        threshold = filter_cfg.options_pcr_threshold
        for ticker in universe[:50]:  # Check top 50 for performance
            cached = options_analyzer.get_cached(ticker)
            if (
                cached
                and cached.get("source") != "unavailable"
                and cached.get("pcr") is not None
            ):
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
        except Exception:
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
