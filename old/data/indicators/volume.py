from __future__ import annotations

import pandas as pd

from swingtradev3.data.indicators.common import ensure_ohlcv, mfi, obv


def calculate(df: pd.DataFrame, cfg) -> dict[str, float | bool | None]:
    candles = ensure_ohlcv(df)
    obv_series = obv(candles)
    obv_trend = None
    if len(obv_series) >= 5:
        obv_trend = bool(obv_series.iloc[-1] > obv_series.iloc[-5])
    avg_volume = candles["volume"].rolling(cfg.volume_avg_periods, min_periods=1).mean()
    volume_ratio = candles["volume"].iloc[-1] / avg_volume.iloc[-1] if avg_volume.iloc[-1] else None
    accumulation_flag = bool(
        volume_ratio is not None
        and volume_ratio >= cfg.volume_spike_multiplier
        and candles["close"].iloc[-1] > candles["close"].iloc[-2]
    ) if len(candles) >= 2 else False
    mfi_series = mfi(candles, cfg.mfi_length)
    return {
        "obv": float(obv_series.iloc[-1]),
        "obv_trend": obv_trend,
        "volume_ratio": float(volume_ratio) if volume_ratio is not None else None,
        "accumulation_flag": accumulation_flag,
        "mfi": float(mfi_series.iloc[-1]) if pd.notna(mfi_series.iloc[-1]) else None,
    }
