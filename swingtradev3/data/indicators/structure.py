from __future__ import annotations

import pandas as pd

from data.indicators.common import ensure_ohlcv


def _base_weeks(df: pd.DataFrame) -> int:
    weekly = df.resample("W-FRI", on="date").agg({"high": "max", "low": "min", "close": "last"})
    weekly = weekly.dropna()
    if weekly.empty:
        return 0
    count = 0
    for idx in range(len(weekly) - 1, -1, -1):
        window = weekly.iloc[max(0, idx - 3) : idx + 1]
        if window.empty:
            continue
        width = (window["high"].max() - window["low"].min()) / window["close"].iloc[-1]
        if width <= 0.12:
            count += 1
        else:
            break
    return count


def calculate(df: pd.DataFrame, cfg) -> dict[str, float | int | None]:
    candles = ensure_ohlcv(df)
    if "date" not in candles.columns:
        candles = candles.reset_index(names="date")
    weekly = candles.resample("W-FRI", on="date").agg({"high": "max", "low": "min", "close": "last"})
    weekly = weekly.dropna()
    last_week = weekly.iloc[-1] if not weekly.empty else None
    pivot = (last_week["high"] + last_week["low"] + last_week["close"]) / 3 if last_week is not None else None
    support = candles["low"].rolling(cfg.sr_lookback_periods, min_periods=1).min().iloc[-1]
    resistance = candles["high"].rolling(cfg.sr_lookback_periods, min_periods=1).max().iloc[-1]
    high_52w = candles["high"].rolling(252, min_periods=1).max().iloc[-1]
    low_52w = candles["low"].rolling(252, min_periods=1).min().iloc[-1]
    close = candles["close"].iloc[-1]
    return {
        "weekly_r1": float((2 * pivot) - last_week["low"]) if pivot is not None else None,
        "weekly_r2": float(pivot + (last_week["high"] - last_week["low"])) if pivot is not None else None,
        "weekly_s1": float((2 * pivot) - last_week["high"]) if pivot is not None else None,
        "weekly_s2": float(pivot - (last_week["high"] - last_week["low"])) if pivot is not None else None,
        "support": float(support),
        "resistance": float(resistance),
        "high_52w": float(high_52w),
        "low_52w": float(low_52w),
        "proximity_to_52w_high_pct": float(((high_52w - close) / high_52w) * 100) if high_52w else None,
        "base_weeks": _base_weeks(candles),
    }
