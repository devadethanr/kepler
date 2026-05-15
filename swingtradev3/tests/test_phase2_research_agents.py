"""Tests for Phase 2.3: ADK Research Agents"""
import pytest
from unittest.mock import patch

from agents.research.filter_agent import FilterAgent
from agents.research.pipeline import research_pipeline


class TestFilterAgent:
    def test_news_sweep_avoids_common_false_positive_tickers(self):
        agent = FilterAgent()

        class FakeNews:
            def sweep_market_news(self, query):
                return {
                    "results": [
                        {
                            "title": "Oil prices rise as BSE Sensex opens higher",
                            "content": "A generic market report mentions Ltd and oil but no stock setup.",
                            "url": "https://reuters.com/markets",
                        },
                        {
                            "title": "Oil India stock gains after new order",
                            "content": "Oil India shares were active on NSE.",
                            "url": "https://moneycontrol.com/oil-india",
                        },
                    ]
                }

            def normalize_headlines(self, headlines, max_age_hours=None):
                return headlines

        universe = [
            {"ticker": "OIL", "name": "Oil India Ltd."},
            {"ticker": "BSE", "name": "BSE Ltd."},
            {"ticker": "LT", "name": "Larsen & Toubro Ltd."},
        ]

        cfg_obj = type("Cfg", (), {"news_sweep_query": "q", "news_max_age_hours": 72})()
        assert agent._sweep_news(FakeNews(), cfg_obj, universe) == ["OIL"]

    def test_fii_filter_requires_explicit_tickers(self):
        agent = FilterAgent()
        assert agent._get_fii_affected_stocks({"fii_net_crore": 5000}, ["RELIANCE", "TCS"]) == []
        assert agent._get_fii_affected_stocks(
            {"tickers": ["reliance", "NOTREAL"]},
            ["RELIANCE", "TCS"],
        ) == ["RELIANCE"]

    def test_news_sweep_prefers_normalized_tickers(self):
        agent = FilterAgent()

        class FakeNews:
            def sweep_market_news(self, query):
                return {
                    "results": [
                        {
                            "title": "Generic market wrap",
                            "content": "No explicit company alias here",
                            "tickers": ["TCS", "NOTREAL"],
                        }
                    ]
                }

            def normalize_headlines(self, headlines, max_age_hours=None):
                return headlines

        universe = [
            {"ticker": "RELIANCE", "name": "Reliance Industries Ltd."},
            {"ticker": "TCS", "name": "Tata Consultancy Services Ltd."},
        ]
        cfg_obj = type("Cfg", (), {"news_sweep_query": "q", "news_max_age_hours": 72})()

        assert agent._sweep_news(FakeNews(), cfg_obj, universe) == ["TCS"]

    def test_news_sweep_does_not_match_ambiguous_first_company_word(self):
        agent = FilterAgent()

        class FakeNews:
            def sweep_market_news(self, query):
                return {
                    "results": [
                        {
                            "title": "Tata Steel announces capacity expansion",
                            "content": "Tata Steel shares were active after management commentary.",
                        },
                    ]
                }

            def normalize_headlines(self, headlines, max_age_hours=None):
                return headlines

        universe = [
            {"ticker": "TCS", "name": "Tata Consultancy Services Ltd."},
        ]
        cfg_obj = type("Cfg", (), {"news_sweep_query": "q", "news_max_age_hours": 72})()

        assert agent._sweep_news(FakeNews(), cfg_obj, universe) == []

    def test_news_sweep_matches_specific_multi_word_company_alias(self):
        agent = FilterAgent()

        class FakeNews:
            def sweep_market_news(self, query):
                return {
                    "results": [
                        {
                            "title": "Tata Consultancy Services wins cloud deal",
                            "content": "TCS signed a large IT services agreement.",
                        },
                    ]
                }

            def normalize_headlines(self, headlines, max_age_hours=None):
                return headlines

        universe = [
            {"ticker": "TCS", "name": "Tata Consultancy Services Ltd."},
        ]
        cfg_obj = type("Cfg", (), {"news_sweep_query": "q", "news_max_age_hours": 72})()

        assert agent._sweep_news(FakeNews(), cfg_obj, universe) == ["TCS"]

    def test_options_filter_ignores_unavailable_cache(self):
        agent = FilterAgent()

        class FakeOptions:
            def get_cached(self, ticker):
                return {"ticker": ticker, "pcr": 2.0, "source": "unavailable"}

        cfg_obj = type("Cfg", (), {"options_pcr_threshold": 1.2})()
        assert agent._detect_unusual_options(FakeOptions(), cfg_obj, ["RELIANCE"]) == []

    def test_options_filter_scans_full_universe_by_default(self):
        agent = FilterAgent()
        universe = [f"STOCK{i}" for i in range(60)]

        class FakeOptions:
            def __init__(self):
                self.seen = []

            def get_cached(self, ticker):
                self.seen.append(ticker)
                return {"ticker": ticker, "pcr": 1.3, "source": "cache"}

        options = FakeOptions()
        cfg_obj = type("Cfg", (), {"options_pcr_threshold": 1.2, "options_scan_limit": 0})()

        assert agent._detect_unusual_options(options, cfg_obj, universe) == universe
        assert options.seen == universe

    def test_options_filter_respects_configured_scan_limit(self):
        agent = FilterAgent()
        universe = [f"STOCK{i}" for i in range(60)]

        class FakeOptions:
            def get_cached(self, ticker):
                return {"ticker": ticker, "pcr": 1.3, "source": "cache"}

        cfg_obj = type("Cfg", (), {"options_pcr_threshold": 1.2, "options_scan_limit": 25})()

        assert agent._detect_unusual_options(FakeOptions(), cfg_obj, universe) == universe[:25]

    @pytest.mark.asyncio
    async def test_fast_filter_below_ema(self):
        """Stock below 200 EMA should be filtered out."""
        agent = FilterAgent()
        import pandas as pd
        import numpy as np
        from config import cfg
        from data.kite_fetcher import KiteFetcher

        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=250, freq="B")
        close = np.linspace(100, 90, 250)  # Declining trend
        candles = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(100000, 500000, 250),
        })
        
        kite_fetcher = KiteFetcher()
        
        with patch.object(kite_fetcher, "fetch_async", return_value=candles):
            passed, reason = await agent._fast_filter_async(kite_fetcher, cfg.research.filter, "TEST")
            assert passed is False
            assert "below_200ema" in reason

    @pytest.mark.asyncio
    async def test_fast_filter_above_ema(self):
        """Stock above 200 EMA with good volume should pass."""
        agent = FilterAgent()
        import pandas as pd
        import numpy as np
        from config import cfg
        from data.kite_fetcher import KiteFetcher

        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=250, freq="B")
        close = np.linspace(90, 120, 250)  # Rising trend
        volume = np.full(250, 500000)  # Consistent high volume
        candles = pd.DataFrame({
            "date": dates,
            "open": close,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": volume,
        })
        
        kite_fetcher = KiteFetcher()
        
        with patch.object(kite_fetcher, "fetch_async", return_value=candles):
            passed, reason = await agent._fast_filter_async(kite_fetcher, cfg.research.filter, "TEST")
            assert passed is True
            assert reason == "passed"


class TestResearchPipeline:
    def test_pipeline_init(self):
        """Test pipeline initializes correctly."""
        assert research_pipeline is not None
        assert len(research_pipeline.sub_agents) == 6
