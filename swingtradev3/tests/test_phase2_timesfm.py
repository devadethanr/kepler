"""Tests for TimesFM Forecaster"""
import pytest
import pandas as pd
import numpy as np

from data.timesfm_forecaster import TimesFMForecaster


class TestTimesFMForecaster:
    def test_forecast_insufficient_data(self):
        """Should return insufficient_data for too few points."""
        forecaster = TimesFMForecaster()
        short_series = pd.Series([100, 101, 102], name="close")
        result = forecaster.forecast("TEST", short_series, horizon=5)
        assert result["source"] == "insufficient_data"
        assert result["last_known_price"] == 102.0

    def test_forecast_with_mock_data(self):
        """Should produce forecasts with sufficient mock data."""
        forecaster = TimesFMForecaster()
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        close = pd.Series(np.cumsum(np.random.randn(100) * 2) + 100, index=dates)

        try:
            result = forecaster.forecast("TEST", close, horizon=10)
        except Exception as e:
            if "401" in str(e) or "Repository" in str(e):
                pytest.skip("HuggingFace authentication required for TimesFM model download")
            raise
        assert result["ticker"] == "TEST"
        assert len(result["forecast_mean"]) == 10
        assert len(result["forecast_lower_10"]) == 10
        assert len(result["forecast_upper_90"]) == 10
        assert result["forecast_direction"] in ["up", "down", "flat"]
        assert result["source"] == "timesfm"
        assert "last_known_price" in result
        assert "forecast_pct_change" in result

    def test_forecast_price_range(self):
        """Should return entry zone, stop, target."""
        forecaster = TimesFMForecaster()
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        close = pd.Series(np.cumsum(np.random.randn(100) * 2) + 100, index=dates)

        result = forecaster.forecast_price_range("TEST", close, horizon=10)
        assert "entry_low" in result
        assert "entry_high" in result
        assert "expected_target" in result
        assert "stop_suggestion" in result
        assert "forecast_direction" in result
        assert result["entry_low"] <= result["entry_high"]

    def test_cached_forecast(self):
        """Second call should return cached result."""
        forecaster = TimesFMForecaster()
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=100, freq="B")
        close = pd.Series(np.cumsum(np.random.randn(100) * 2) + 100, index=dates)

        result1 = forecaster.forecast("CACHED_TEST", close, horizon=5)
        result2 = forecaster.forecast("CACHED_TEST", close, horizon=5)
        assert result1["forecast_mean"] == result2["forecast_mean"]

    def test_forecast_with_live_kite_data(self):
        """Should produce forecasts with real Kite data."""
        from data.kite_fetcher import KiteFetcher
        from auth.kite.client import has_kite_session

        if not has_kite_session():
            pytest.skip("No active Kite session")

        forecaster = TimesFMForecaster()
        fetcher = KiteFetcher()
        try:
            candles = fetcher.fetch("RELIANCE", interval="day")
        except RuntimeError as e:
            pytest.skip(f"Live Kite fetch failed: {e}")

        if candles is None or len(candles) < 32:
            pytest.skip("Insufficient Kite data")

        result = forecaster.forecast("RELIANCE", candles["close"], horizon=20)
        assert result["ticker"] == "RELIANCE"
        assert len(result["forecast_mean"]) == 20
        assert result["source"] == "timesfm"
        assert result["last_known_price"] > 0
        print(f"\n  RELIANCE forecast: direction={result['forecast_direction']}, "
              f"pct_change={result['forecast_pct_change']}%")

    def test_forecast_price_range_with_live_kite_data(self):
        """Should return entry zone with real Kite data."""
        from data.kite_fetcher import KiteFetcher
        from auth.kite.client import has_kite_session

        if not has_kite_session():
            pytest.skip("No active Kite session")

        forecaster = TimesFMForecaster()
        fetcher = KiteFetcher()
        try:
            candles = fetcher.fetch("TCS", interval="day")
        except RuntimeError as e:
            pytest.skip(f"Live Kite fetch failed: {e}")

        if candles is None or len(candles) < 32:
            pytest.skip("Insufficient Kite data")

        result = forecaster.forecast_price_range("TCS", candles["close"], horizon=20)
        assert "entry_low" in result
        assert "entry_high" in result
        assert result["entry_low"] > 0
        assert result["entry_high"] > 0
        print(f"\n  TCS entry zone: {result['entry_low']}-{result['entry_high']}, "
              f"target={result['expected_target']}, stop={result['stop_suggestion']}")
