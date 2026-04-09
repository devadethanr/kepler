"""Tests for Phase 2.1: Data Layer"""
import pytest
from datetime import date

from data.market_regime import MarketRegimeDetector
from data.institutional_flows import InstitutionalFlowsTool
from data.options_analyzer import OptionsAnalyzer
from data.macro_indicators import MacroIndicatorsTool
from data.news_aggregator import NewsAggregator
from data.nifty200_loader import Nifty200Loader


class TestMarketRegimeDetector:
    def test_detect_regime_with_defaults(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime()
        assert "regime" in result
        assert result["regime"] in ["bull", "bear", "choppy", "transition"]
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0
        assert "volatility_state" in result
        assert result["volatility_state"] in ["low", "normal", "high"]

    def test_detect_regime_bullish_signals(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime(
            vix=10.0,
            fii_net=2000.0,
            dii_net=1000.0,
            advance_decline_ratio=2.5,
        )
        assert result["regime"] in ["bull", "transition"]
        assert result["volatility_state"] == "low"

    def test_detect_regime_bearish_signals(self):
        detector = MarketRegimeDetector()
        result = detector.detect_regime(
            vix=30.0,
            fii_net=-3000.0,
            dii_net=-1000.0,
            advance_decline_ratio=0.2,
        )
        assert result["regime"] in ["bear", "choppy"]
        assert result["volatility_state"] == "high"

    def test_cached_regime(self):
        detector = MarketRegimeDetector()
        result1 = detector.detect_regime()
        result2 = detector.get_regime()
        assert result1["regime"] == result2["regime"]


class TestInstitutionalFlowsTool:
    def test_get_fii_dii(self):
        tool = InstitutionalFlowsTool()
        result = tool.get_fii_dii()
        assert "date" in result
        assert "fii_net_crore" in result or result.get("source") in ["not_configured", "cache"]

    def test_get_all(self):
        tool = InstitutionalFlowsTool()
        result = tool.get_all()
        assert "date" in result
        assert "fii_dii" in result


class TestOptionsAnalyzer:
    def test_analyze_options_bullish_pcr(self):
        analyzer = OptionsAnalyzer()
        result = analyzer.analyze_options(
            ticker="RELIANCE",
            pcr=1.4,
            iv=25.0,
            max_pain=2800.0,
            india_vix=15.0,
        )
        assert result["ticker"] == "RELIANCE"
        assert result["pcr"] == 1.4
        assert result["pcr_signal"] == "bullish"
        assert result["vix_regime"] in ["normal", "low"]  # 15.0 is borderline

    def test_analyze_options_bearish_pcr(self):
        analyzer = OptionsAnalyzer()
        result = analyzer.analyze_options(
            ticker="TCS",
            pcr=0.5,
            iv=30.0,
            india_vix=28.0,
        )
        assert result["pcr_signal"] == "bearish"
        assert result["vix_regime"] == "high"

    def test_analyze_options_unusual_activity(self):
        analyzer = OptionsAnalyzer()
        oi_data = [
            {"strike": 2800, "ce_oi": 1000, "pe_oi": 1500, "ce_change": -200, "pe_change": 100},
            {"strike": 2900, "ce_oi": 800, "pe_oi": 1200, "ce_change": -150, "pe_change": 50},
        ]
        result = analyzer.analyze_options(
            ticker="RELIANCE",
            pcr=1.2,
            oi_data=oi_data,
        )
        assert result["unusual_activity"] == "call_unwinding"


class TestMacroIndicatorsTool:
    def test_get_macro_indicators(self):
        tool = MacroIndicatorsTool()
        result = tool.get_macro_indicators()
        assert "date" in result
        assert "crude_usd" in result
        assert "usd_inr" in result
        assert "india_vix" in result

    def test_get_crude_trend(self):
        tool = MacroIndicatorsTool()
        result = tool.get_macro_indicators()
        trend = tool.get_crude_trend()
        assert trend in ["high", "moderate", "low", None]


class TestNewsAggregator:
    def test_search_news_tavily(self):
        aggregator = NewsAggregator()
        result = aggregator.search_news("RELIANCE stock news today")
        assert "query" in result
        assert "results" in result
        assert "source" in result

    def test_sweep_market_news(self):
        aggregator = NewsAggregator()
        result = aggregator.sweep_market_news()
        assert "results" in result


class TestNifty200Loader:
    def test_load_universe(self):
        loader = Nifty200Loader()
        tickers = loader.load()
        assert len(tickers) == 200
        assert "RELIANCE" in tickers
        assert "TCS" in tickers

    def test_name_for(self):
        loader = Nifty200Loader()
        name = loader.name_for("RELIANCE")
        assert isinstance(name, str)
        assert len(name) > 0
