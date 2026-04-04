"""
Macro Indicators Layer
======================
Tracks macro data: crude oil, USD/INR, US yields, GDP, CPI, RBI rates.
Pure data fetching — no analysis, no decisions.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from paths import CONTEXT_DIR
from storage import read_json, write_json


class MacroIndicatorsTool:
    """Fetches and caches macro indicators from free sources."""

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 4) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "macro_cache.json")
        self.ttl_hours = ttl_hours
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )

    def _cached(self) -> dict[str, Any] | None:
        payload = read_json(self.cache_path, {})
        fetched_at = payload.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = datetime.utcnow() - datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        if age > timedelta(hours=self.ttl_hours):
            return None
        return payload.get("data")

    def _store(self, payload: dict[str, Any]) -> dict[str, Any]:
        write_json(self.cache_path, {"fetched_at": datetime.utcnow().isoformat(), "data": payload})
        return payload

    def _fetch_yahoo(self, symbol: str) -> float | None:
        """Fetch current price from Yahoo Finance."""
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("chart", {}).get("result", [])
            if result:
                meta = result[0].get("meta", {})
                return meta.get("regularMarketPrice")
        except Exception:
            pass
        return None

    def get_macro_indicators(self) -> dict[str, Any]:
        """
        Fetch all macro indicators.

        Returns:
            {crude_usd, usd_inr, us_10y_yield, india_vix, date, source}
        """
        cached = self._cached()
        if cached is not None:
            return cached

        result: dict[str, Any] = {"date": date.today().isoformat(), "source": "yahoo_finance"}

        # Crude oil (WTI)
        crude = self._fetch_yahoo("CL=F")
        result["crude_usd"] = round(crude, 2) if crude else None

        # USD/INR
        usd_inr = self._fetch_yahoo("USDINR=X")
        result["usd_inr"] = round(usd_inr, 4) if usd_inr else None

        # US 10Y Treasury yield
        us_10y = self._fetch_yahoo("^TNX")
        result["us_10y_yield"] = round(us_10y, 3) if us_10y else None

        # India VIX (via Yahoo)
        vix = self._fetch_yahoo("^INDIAVIX")
        result["india_vix"] = round(vix, 2) if vix else None

        # S&P 500 (global market context)
        sp500 = self._fetch_yahoo("^GSPC")
        result["sp500"] = round(sp500, 2) if sp500 else None

        # Nasdaq
        nasdaq = self._fetch_yahoo("^IXIC")
        result["nasdaq"] = round(nasdaq, 2) if nasdaq else None

        return self._store(result)

    def get_crude_trend(self) -> str | None:
        """Determine crude oil trend (simplified)."""
        data = self.get_macro_indicators()
        crude = data.get("crude_usd")
        if crude is None:
            return None
        if crude > 85:
            return "high"  # Negative for paints, tyres, OMCs
        elif crude > 70:
            return "moderate"
        else:
            return "low"  # Positive for paints, tyres, OMCs

    def get_usd_inr_trend(self) -> str | None:
        """Determine USD/INR trend (simplified)."""
        data = self.get_macro_indicators()
        rate = data.get("usd_inr")
        if rate is None:
            return None
        if rate > 84:
            return "weakening_inr"  # Positive for IT, pharma
        elif rate < 82:
            return "strengthening_inr"  # Negative for IT, pharma
        else:
            return "stable"
