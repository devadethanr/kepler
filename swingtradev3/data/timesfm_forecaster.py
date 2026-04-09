"""
TimesFM Forecaster
===================
Google Research TimesFM 2.5 — 200M parameter time-series foundation model.
Runs locally, free, Apache 2.0 license.

Pure computation — no LLM, no decisions.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from paths import CONTEXT_DIR
from storage import read_json, write_json

# TimesFM model loaded lazily — stays loaded after first call
_TIMESFM_MODEL = None


def _get_timesfm_model():
    """Lazy-load TimesFM 2.5 model (only when first called). Stays loaded."""
    global _TIMESFM_MODEL
    if _TIMESFM_MODEL is None:
        from timesfm import ForecastConfig, TimesFM_2p5_200M_torch
        _TIMESFM_MODEL = TimesFM_2p5_200M_torch.from_pretrained(
            "google/timesfm-2.5-200m-pytorch"
        )
        # Compile for fast decoding
        _TIMESFM_MODEL.compile(ForecastConfig(max_horizon=128, max_context=512, use_continuous_quantile_head=True))
    return _TIMESFM_MODEL


class TimesFMForecaster:
    """Forecast future values using Google TimesFM 2.5."""

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 4) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "timesfm_cache.json")
        self.ttl_hours = ttl_hours

    def _cached(self, ticker: str, horizon: int) -> dict[str, Any] | None:
        cache = read_json(self.cache_path, {})
        key = f"{ticker}_{horizon}"
        item = cache.get(key)
        if not item:
            return None
        fetched_at = item.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = datetime.utcnow() - datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        if age > timedelta(hours=self.ttl_hours):
            return None
        return item.get("data")

    def _store(self, ticker: str, horizon: int, data: dict[str, Any]) -> dict[str, Any]:
        cache = read_json(self.cache_path, {})
        key = f"{ticker}_{horizon}"
        cache[key] = {"fetched_at": datetime.utcnow().isoformat(), "data": data}
        write_json(self.cache_path, cache)
        return data

    def forecast(
        self,
        ticker: str,
        historical_close: pd.Series,
        horizon: int = 20,
    ) -> dict[str, Any]:
        """
        Forecast future prices using TimesFM.

        Args:
            ticker: Stock symbol
            historical_close: Historical close prices (pandas Series)
            horizon: Number of days to forecast

        Returns:
            {ticker, forecast_mean, forecast_lower_10, forecast_upper_90,
             last_known_price, forecast_direction, forecast_pct_change, horizon, source}
        """
        cached = self._cached(ticker, horizon)
        if cached is not None:
            return cached

        if len(historical_close) < 32:
            return {
                "ticker": ticker,
                "forecast_mean": [],
                "forecast_lower_10": [],
                "forecast_upper_90": [],
                "last_known_price": float(historical_close.iloc[-1]),
                "forecast_direction": "unknown",
                "forecast_pct_change": 0.0,
                "horizon": horizon,
                "source": "insufficient_data",
                "message": f"Need at least 32 data points, got {len(historical_close)}",
            }

        model = _get_timesfm_model()

        # Prepare input: numpy array
        input_data = historical_close.values.astype(np.float64)
        context_len = 512
        if len(input_data) > context_len:
            input_data = input_data[-context_len:]

        # Forecast: returns (mean_forecast, quantile_forecast)
        # mean_forecast shape: (batch, horizon)
        # quantile_forecast shape: (batch, horizon, n_quantiles)
        mean_forecast, quantile_forecast = model.forecast(
            horizon=horizon,
            inputs=[input_data],
        )

        last_price = float(historical_close.iloc[-1])
        forecasts_mean = mean_forecast[0].tolist()  # (horizon,)

        # Extract quantile forecasts (10th and 90th percentile)
        n_quantiles = quantile_forecast.shape[-1]
        lower_idx = max(0, int(n_quantiles * 0.1))
        upper_idx = min(n_quantiles - 1, int(n_quantiles * 0.9))

        forecasts_lower = quantile_forecast[0, :, lower_idx].tolist()
        forecasts_upper = quantile_forecast[0, :, upper_idx].tolist()

        # Direction and pct change
        if forecasts_mean:
            pct_change = ((forecasts_mean[-1] - last_price) / last_price) * 100
            if pct_change > 2:
                direction = "up"
            elif pct_change < -2:
                direction = "down"
            else:
                direction = "flat"
        else:
            pct_change = 0.0
            direction = "unknown"

        result = {
            "ticker": ticker,
            "forecast_mean": [round(x, 2) for x in forecasts_mean],
            "forecast_lower_10": [round(x, 2) for x in forecasts_lower],
            "forecast_upper_90": [round(x, 2) for x in forecasts_upper],
            "last_known_price": round(last_price, 2),
            "forecast_direction": direction,
            "forecast_pct_change": round(pct_change, 2),
            "horizon": horizon,
            "source": "timesfm",
            "as_of": datetime.utcnow().isoformat(),
        }

        return self._store(ticker, horizon, result)

    def forecast_price_range(
        self,
        ticker: str,
        historical_close: pd.Series,
        horizon: int = 20,
    ) -> dict[str, float]:
        """Get forecasted price range for entry zone calculation."""
        forecast = self.forecast(ticker, historical_close, horizon)

        if forecast["source"] == "insufficient_data":
            return {}

        mean_forecast = forecast["forecast_mean"]
        if not mean_forecast:
            return {}

        last_price = forecast["last_known_price"]
        entry_zone = mean_forecast[:min(3, len(mean_forecast))]
        entry_low = min(entry_zone) if entry_zone else last_price
        entry_high = max(entry_zone) if entry_zone else last_price
        lower_bound = min(forecast["forecast_lower_10"]) if forecast["forecast_lower_10"] else last_price * 0.95
        target = max(forecast["forecast_upper_90"]) if forecast["forecast_upper_90"] else last_price * 1.05

        return {
            "entry_low": round(entry_low, 2),
            "entry_high": round(entry_high, 2),
            "expected_target": round(target, 2),
            "stop_suggestion": round(lower_bound, 2),
            "forecast_direction": forecast["forecast_direction"],
            "forecast_pct_change": forecast["forecast_pct_change"],
        }
