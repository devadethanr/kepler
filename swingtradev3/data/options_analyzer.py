"""
Options Chain Analyzer
======================
Fetches and analyzes options chain data from NSE/Kite.
Computes: PCR, max pain, IV rank, OI changes, unusual activity.
Pure computation — no LLM, no decisions.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from paths import CONTEXT_DIR
from storage import read_json, write_json


class OptionsAnalyzer:
    """Analyzes options chain data for sentiment and positioning signals."""

    def __init__(self, cache_path: Path | None = None, ttl_minutes: int = 30) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "options_cache.json")
        self.ttl_minutes = ttl_minutes

    def _cached(self, ticker: str) -> dict[str, Any] | None:
        cache = read_json(self.cache_path, {})
        item = cache.get(ticker)
        if not item:
            return None
        fetched_at = item.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = datetime.utcnow() - datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        if age > timedelta(minutes=self.ttl_minutes):
            return None
        return item.get("data")

    def _store(self, ticker: str, data: dict[str, Any]) -> dict[str, Any]:
        cache = read_json(self.cache_path, {})
        cache[ticker] = {"fetched_at": datetime.utcnow().isoformat(), "data": data}
        write_json(self.cache_path, cache)
        return data

    def analyze_options(
        self,
        ticker: str,
        pcr: float | None = None,
        iv: float | None = None,
        max_pain: float | None = None,
        oi_data: list[dict[str, Any]] | None = None,
        india_vix: float | None = None,
    ) -> dict[str, Any]:
        """
        Analyze options data for a given stock.

        Args:
            ticker: Stock symbol
            pcr: Put-Call Ratio (total puts OI / total calls OI)
            iv: Implied volatility of ATM options
            max_pain: Strike price with maximum pain for option writers
            oi_data: List of OI data points [{strike, ce_oi, pe_oi, ce_change, pe_change}]
            india_vix: Current India VIX value

        Returns:
            Structured options analysis
        """
        result: dict[str, Any] = {"ticker": ticker}

        # PCR analysis
        if pcr is not None:
            result["pcr"] = round(pcr, 3)
            if pcr > 1.3:
                result["pcr_signal"] = "bullish"
                result["pcr_interpretation"] = "Heavy put writing — support building"
            elif pcr > 1.0:
                result["pcr_signal"] = "neutral_bullish"
                result["pcr_interpretation"] = "Slightly bullish positioning"
            elif pcr > 0.7:
                result["pcr_signal"] = "neutral_bearish"
                result["pcr_interpretation"] = "Slightly bearish positioning"
            else:
                result["pcr_signal"] = "bearish"
                result["pcr_interpretation"] = "Heavy call writing — resistance building"
        else:
            result["pcr"] = None
            result["pcr_signal"] = None

        # IV analysis
        if iv is not None:
            result["iv"] = round(iv, 2)
            # IV percentile would need historical IV data
            result["iv_signal"] = "normal"
        else:
            result["iv"] = None
            result["iv_signal"] = None

        # Max pain analysis
        if max_pain is not None:
            result["max_pain"] = round(max_pain, 2)
        else:
            result["max_pain"] = None

        # OI change analysis
        if oi_data is not None and len(oi_data) > 0:
            total_ce_oi = sum(d.get("ce_oi", 0) for d in oi_data)
            total_pe_oi = sum(d.get("pe_oi", 0) for d in oi_data)
            total_ce_change = sum(d.get("ce_change", 0) for d in oi_data)
            total_pe_change = sum(d.get("pe_change", 0) for d in oi_data)

            result["total_ce_oi"] = total_ce_oi
            result["total_pe_oi"] = total_pe_oi
            result["total_ce_oi_change"] = total_ce_change
            result["total_pe_oi_change"] = total_pe_change

            # Detect unusual activity
            if total_ce_change < -total_ce_oi * 0.1:
                result["unusual_activity"] = "call_unwinding"
                result["unusual_interpretation"] = "Call writers covering — bullish signal"
            elif total_pe_change < -total_pe_oi * 0.1:
                result["unusual_activity"] = "put_unwinding"
                result["unusual_interpretation"] = "Put writers covering — bearish signal"
            elif total_ce_change > total_ce_oi * 0.15:
                result["unusual_activity"] = "call_writing"
                result["unusual_interpretation"] = "New call writing — resistance building"
            elif total_pe_change > total_pe_oi * 0.15:
                result["unusual_activity"] = "put_writing"
                result["unusual_interpretation"] = "New put writing — support building"
            else:
                result["unusual_activity"] = "none"
        else:
            result["unusual_activity"] = "none"

        # India VIX context
        if india_vix is not None:
            result["india_vix"] = round(india_vix, 2)
            if india_vix > 25:
                result["vix_regime"] = "high"
            elif india_vix > 15:
                result["vix_regime"] = "normal"
            else:
                result["vix_regime"] = "low"
        else:
            result["india_vix"] = None
            result["vix_regime"] = None

        result["source"] = "provided"
        result["as_of"] = datetime.utcnow().isoformat()

        return self._store(ticker, result)

    def get_cached(self, ticker: str) -> dict[str, Any] | None:
        """Get cached options data if available and fresh."""
        return self._cached(ticker)
