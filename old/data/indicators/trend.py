from __future__ import annotations

import pandas as pd

from swingtradev3.data.indicators.common import adx, atr, ema, ensure_ohlcv


def _supertrend_direction(df: pd.DataFrame, length: int, multiplier: float) -> tuple[int | None, bool]:
    candles = ensure_ohlcv(df)
    atr_series = atr(candles, length)
    hl2 = (candles["high"] + candles["low"]) / 2
    upper = hl2 + multiplier * atr_series
    lower = hl2 - multiplier * atr_series
    direction = pd.Series(index=candles.index, dtype=float)
    for idx in range(len(candles)):
        if idx == 0 or pd.isna(atr_series.iloc[idx]):
            direction.iloc[idx] = 1
            continue
        prev = int(direction.iloc[idx - 1])
        if candles["close"].iloc[idx] > upper.iloc[idx - 1]:
            direction.iloc[idx] = 1
        elif candles["close"].iloc[idx] < lower.iloc[idx - 1]:
            direction.iloc[idx] = -1
        else:
            direction.iloc[idx] = prev
    flipped = bool(len(direction) > 1 and direction.iloc[-1] != direction.iloc[-2])
    return int(direction.iloc[-1]) if len(direction) else None, flipped


def calculate(df: pd.DataFrame, cfg) -> dict[str, float | bool | int | None]:
    candles = ensure_ohlcv(df)
    ema_fast = ema(candles["close"], cfg.ema_fast)
    ema_mid = ema(candles["close"], cfg.ema_mid)
    ema_slow = ema(candles["close"], cfg.ema_slow)
    adx_series = adx(candles, cfg.adx_length)
    direction, flipped = _supertrend_direction(
        candles, cfg.supertrend_length, cfg.supertrend_multiplier
    )
    last_close = candles["close"].iloc[-1]
    last_ema200 = ema_slow.iloc[-1]
    return {
        "ema_21": float(ema_fast.iloc[-1]) if pd.notna(ema_fast.iloc[-1]) else None,
        "ema_50": float(ema_mid.iloc[-1]) if pd.notna(ema_mid.iloc[-1]) else None,
        "ema_200": float(last_ema200) if pd.notna(last_ema200) else None,
        "above_200ema": bool(last_close > last_ema200) if pd.notna(last_ema200) else None,
        "price_vs_ema200_pct": float(((last_close / last_ema200) - 1) * 100)
        if pd.notna(last_ema200) and last_ema200
        else None,
        "adx": float(adx_series.iloc[-1]) if pd.notna(adx_series.iloc[-1]) else None,
        "trend_strong": bool(
            pd.notna(adx_series.iloc[-1]) and adx_series.iloc[-1] >= cfg.adx_trend_threshold
        ),
        "supertrend_direction": direction,
        "supertrend_flipped": flipped,
    }
