from __future__ import annotations

import pandas as pd

from swingtradev3.data.indicators.common import ensure_ohlcv


def calculate(df: pd.DataFrame, cfg) -> dict[str, list[str]]:
    candles = ensure_ohlcv(df)
    patterns: list[str] = []
    latest = candles.iloc[-1]
    body = abs(latest["close"] - latest["open"])
    candle_range = latest["high"] - latest["low"]
    upper_wick = latest["high"] - max(latest["close"], latest["open"])
    lower_wick = min(latest["close"], latest["open"]) - latest["low"]

    if candle_range and body / candle_range <= 0.1 and "doji" in cfg.enabled:
        patterns.append("doji")
    if lower_wick > body * 2 and upper_wick < body and "hammer" in cfg.enabled:
        patterns.append("hammer")
    if len(candles) >= 2 and "engulfing" in cfg.enabled:
        prev = candles.iloc[-2]
        bullish = latest["close"] > latest["open"] and prev["close"] < prev["open"]
        engulfing = latest["close"] >= prev["open"] and latest["open"] <= prev["close"]
        if bullish and engulfing:
            patterns.append("bullish_engulfing")
    return {"detected_patterns": patterns}
