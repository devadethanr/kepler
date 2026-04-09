"""Tests for Phase 2.2: Signal Engine"""
import pytest
from datetime import datetime

from tools.analysis.sentiment_analysis import SentimentAnalyzer
from tools.analysis.regime_detection import detect_regime
from tools.analysis.correlation_check import check_correlation
from tools.analysis.entry_timing import check_entry_timing


class TestSentimentAnalyzer:
    def test_analyze_sentiment_positive(self):
        sa = SentimentAnalyzer()
        result = sa.analyze_sentiment("RIL wins major contract, analysts upgrade target price")
        assert "sentiment_score" in result
        assert "sentiment_label" in result
        assert result["sentiment_label"] in ["bullish", "neutral", "bearish"]
        assert "catalyst_type" in result
        assert "contract" in result["catalyst_type"]

    def test_analyze_sentiment_negative(self):
        sa = SentimentAnalyzer()
        result = sa.analyze_sentiment("SEBI imposes penalty on company for disclosure violations")
        assert result["sentiment_label"] in ["bearish", "neutral"]
        assert "regulatory" in result["catalyst_type"]

    def test_analyze_news_list(self):
        sa = SentimentAnalyzer()
        news = [
            {"title": "Company reports strong earnings", "content": "Revenue up 20%"},
            {"title": "Analysts upgrade stock to buy", "content": "Target raised"},
        ]
        result = sa.analyze_news_list(news)
        assert "sentiment_score" in result
        assert "article_count" in result
        assert result["article_count"] == 2


class TestRegimeDetection:
    def test_detect_regime(self):
        result = detect_regime()
        assert "regime" in result
        assert result["regime"] in ["bull", "bear", "choppy", "transition"]
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0


class TestCorrelationCheck:
    def test_check_correlation_insufficient_data(self):
        result = check_correlation(["RELIANCE"])
        assert result["warning"] is False
        assert "Need at least 2 positions" in result["message"]

    def test_check_correlation_with_mock_data(self):
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        returns_data = {
            "RELIANCE": pd.Series(np.random.randn(60) * 0.02, index=dates),
            "TCS": pd.Series(np.random.randn(60) * 0.015, index=dates),
        }
        result = check_correlation(["RELIANCE", "TCS"], returns_data=returns_data)
        assert result["max_correlation"] is not None
        assert result["max_correlation_pair"] == ("RELIANCE", "TCS")
        assert result["portfolio_var_95"] is not None


class TestEntryTiming:
    def test_entry_timing_open_noise(self):
        result = check_entry_timing(
            "RELIANCE",
            current_time=datetime(2026, 4, 5, 9, 20),
        )
        assert result["optimal"] is False
        assert "open" in result["reason"].lower()
        assert result["wait_minutes"] is not None

    def test_entry_timing_optimal(self):
        result = check_entry_timing(
            "RELIANCE",
            current_time=datetime(2026, 4, 5, 10, 30),
        )
        assert result["optimal"] is True

    def test_entry_timing_late_day(self):
        result = check_entry_timing(
            "RELIANCE",
            current_time=datetime(2026, 4, 5, 15, 10),
        )
        assert result["optimal"] is False
        assert "square-off" in result["reason"].lower()

    def test_entry_timing_fno_ban(self):
        result = check_entry_timing(
            "RELIANCE",
            current_time=datetime(2026, 4, 5, 10, 30),
            in_fno_ban=True,
        )
        assert result["optimal"] is False
        assert "fno_ban" in result["risk_factors"]

    def test_entry_timing_earnings(self):
        result = check_entry_timing(
            "RELIANCE",
            current_time=datetime(2026, 4, 5, 10, 30),
            earnings_within_days=1,
        )
        assert result["optimal"] is False
        assert "earnings" in str(result["risk_factors"]).lower()
