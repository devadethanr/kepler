"""
Market Regime Detection
=======================
Classifies market state using:
  - Nifty 50 trend (above/below 200 EMA, ADX strength)
  - India VIX level
  - FII/DII flow direction
  - Market breadth (advance/decline ratio)
  - Market momentum (Nifty ROC)

Output: {regime, confidence, volatility_state}
Pure computation — no LLM, no decisions.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json


class MarketRegimeDetector:
    """Detects market regime from Nifty 50, VIX, and FII/DII flows."""

    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 4) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "regime_cache.json")
        self.ttl_hours = ttl_hours

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

    def detect_regime(
        self,
        nifty_close: pd.Series | None = None,
        vix: float | None = None,
        fii_net: float | None = None,
        dii_net: float | None = None,
        advance_decline_ratio: float | None = None,
    ) -> dict[str, Any]:
        """
        Detect market regime based on multiple signals.

        Args:
            nifty_close: Nifty 50 close price series (for EMA/ROC calculation)
            vix: Current India VIX value
            fii_net: FII net flow in crores
            dii_net: DII net flow in crores
            advance_decline_ratio: Market breadth ratio

        Returns:
            {regime, confidence, volatility_state, details}
        """
        scores: dict[str, float] = {}

        # Signal 1: Nifty trend (weight: 0.35)
        trend_score = 0.0
        trend_details: dict[str, Any] = {}
        if nifty_close is not None and len(nifty_close) >= 200:
            ema_200 = nifty_close.ewm(span=200, adjust=False).mean().iloc[-1]
            ema_50 = nifty_close.ewm(span=50, adjust=False).mean().iloc[-1]
            current = nifty_close.iloc[-1]

            if current > ema_200:
                trend_score += 0.5
            if current > ema_50:
                trend_score += 0.3
            if ema_50 > ema_200:
                trend_score += 0.2

            # ROC 20d
            if len(nifty_close) >= 20:
                roc_20 = (current / nifty_close.iloc[-20] - 1) * 100
                trend_details["roc_20d"] = round(roc_20, 2)
                if roc_20 > 0:
                    trend_score += 0.1

            trend_details["above_200ema"] = bool(current > ema_200)
            trend_details["above_50ema"] = bool(current > ema_50)
            trend_details["ema_50_above_200"] = bool(ema_50 > ema_200)
            trend_details["current"] = round(float(current), 2)
            trend_details["ema_200"] = round(float(ema_200), 2)

        scores["trend"] = min(trend_score, 1.0)

        # Signal 2: VIX (weight: 0.20)
        vix_score = 0.5  # neutral default
        if vix is not None:
            if vix < 12:
                vix_score = 0.8  # low fear = bullish
            elif vix < 18:
                vix_score = 0.5  # normal
            elif vix < 25:
                vix_score = 0.3  # elevated fear
            else:
                vix_score = 0.1  # high fear = bearish

        scores["vix"] = vix_score

        # Signal 3: FII/DII flows (weight: 0.25)
        flow_score = 0.5  # neutral default
        if fii_net is not None:
            if fii_net > 1000:
                flow_score += 0.25
            elif fii_net > 0:
                flow_score += 0.1
            elif fii_net > -1000:
                flow_score -= 0.1
            else:
                flow_score -= 0.25

        if dii_net is not None:
            if dii_net > 1000:
                flow_score += 0.1
            elif dii_net < -1000:
                flow_score -= 0.1

        flow_score = max(0.0, min(1.0, flow_score))
        scores["flows"] = flow_score

        # Signal 4: Market breadth (weight: 0.20)
        breadth_score = 0.5  # neutral default
        if advance_decline_ratio is not None:
            if advance_decline_ratio > 2.0:
                breadth_score = 0.9
            elif advance_decline_ratio > 1.0:
                breadth_score = 0.7
            elif advance_decline_ratio > 0.5:
                breadth_score = 0.4
            else:
                breadth_score = 0.2

        scores["breadth"] = breadth_score

        # Weighted composite
        weights = {"trend": 0.35, "vix": 0.20, "flows": 0.25, "breadth": 0.20}
        composite = sum(scores[k] * weights[k] for k in weights)

        # Classify regime
        if composite >= 0.65:
            regime = "bull"
            confidence = round(composite, 2)
        elif composite >= 0.45:
            regime = "transition"
            confidence = round(1.0 - abs(composite - 0.55) * 2, 2)
        elif composite >= 0.35:
            regime = "choppy"
            confidence = round(0.6, 2)
        else:
            regime = "bear"
            confidence = round(1.0 - composite, 2)

        # Volatility state
        if vix is not None:
            if vix < 12:
                volatility_state = "low"
            elif vix < 20:
                volatility_state = "normal"
            else:
                volatility_state = "high"
        else:
            volatility_state = "normal"

        result = {
            "regime": regime,
            "confidence": confidence,
            "volatility_state": volatility_state,
            "composite_score": round(composite, 3),
            "signal_scores": {k: round(v, 3) for k, v in scores.items()},
            "trend_details": trend_details,
            "vix": vix,
            "fii_net_crore": fii_net,
            "dii_net_crore": dii_net,
            "advance_decline_ratio": advance_decline_ratio,
        }

        return self._store(result)

    def get_regime(self) -> dict[str, Any]:
        """Get cached regime or detect with defaults."""
        cached = self._cached()
        if cached is not None:
            return cached
        return self.detect_regime()
