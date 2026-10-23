"""Tests for Phase 2.4: Risk Enhancement"""

import pandas as pd
import numpy as np

from risk.correlation_checker import CorrelationChecker


class TestCorrelationChecker:
    @staticmethod
    def _candles(returns: pd.Series) -> pd.DataFrame:
        return pd.DataFrame({"close": 100 * (1 + returns).cumprod()})

    def test_single_position_no_risk(self):
        checker = CorrelationChecker()
        result = checker.check([{"ticker": "RELIANCE", "quantity": 10, "entry_price": 2850}])
        assert result["approved"] is True
        assert "Single position" in result["message"]

    def test_insufficient_data(self):
        checker = CorrelationChecker()
        result = checker.check(
            [
                {"ticker": "RELIANCE", "quantity": 10, "entry_price": 2850},
                {"ticker": "TCS", "quantity": 5, "entry_price": 3800},
            ]
        )
        # Without Kite session, returns None for correlation
        assert result["approved"] is True

    def test_correlation_with_mock_data(self):
        checker = CorrelationChecker()
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        returns_data = {
            "RELIANCE": pd.Series(np.random.randn(60) * 0.02, index=dates),
            "TCS": pd.Series(np.random.randn(60) * 0.015, index=dates),
            "HDFCBANK": pd.Series(np.random.randn(60) * 0.018, index=dates),
        }
        checker.fetcher.fetch = lambda ticker, interval: self._candles(returns_data[ticker])
        result = checker.check(
            [
                {"ticker": "RELIANCE", "quantity": 10, "entry_price": 2850},
                {"ticker": "TCS", "quantity": 5, "entry_price": 3800},
                {"ticker": "HDFCBANK", "quantity": 8, "entry_price": 1650},
            ],
        )
        assert result["approved"] is True
        assert result["data_points"] >= 20
        assert result["max_correlation"] is not None

    def test_new_ticker_rejected_on_high_correlation(self):
        """If new ticker would exceed correlation threshold, should be rejected."""
        checker = CorrelationChecker(max_correlation=0.3)
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        # Create highly correlated returns
        base = np.random.randn(60) * 0.02
        returns_data = {
            "RELIANCE": pd.Series(base, index=dates),
            "TCS": pd.Series(base * 0.9 + np.random.randn(60) * 0.001, index=dates),
        }
        checker.fetcher.fetch = lambda ticker, interval: self._candles(returns_data[ticker])
        result = checker.check(
            [{"ticker": "RELIANCE", "quantity": 10, "entry_price": 2850}],
            new_ticker="TCS",
        )
        assert result["approved"] is False
        assert result["max_correlation"] > checker.max_correlation
        assert result["max_correlation_pair"] == ("RELIANCE", "TCS")
