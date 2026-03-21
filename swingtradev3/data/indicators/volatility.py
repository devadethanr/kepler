from __future__ import annotations

import pandas as pd

from swingtradev3.data.indicators.common import atr, bollinger_bands, ensure_ohlcv


def calculate(df: pd.DataFrame, cfg) -> dict[str, float | bool | None]:
    candles = ensure_ohlcv(df)
    atr_series = atr(candles, cfg.atr_length)
    basis, upper, lower = bollinger_bands(candles["close"], cfg.bb_length, cfg.bb_std)
    close = candles["close"].iloc[-1]
    width = upper.iloc[-1] - lower.iloc[-1]
    return {
        "atr_14": float(atr_series.iloc[-1]) if pd.notna(atr_series.iloc[-1]) else None,
        "atr_pct": float((atr_series.iloc[-1] / close) * 100)
        if pd.notna(atr_series.iloc[-1]) and close
        else None,
        "stop_distance": float(atr_series.iloc[-1] * cfg.atr_stop_multiplier)
        if pd.notna(atr_series.iloc[-1])
        else None,
        "bb_upper": float(upper.iloc[-1]) if pd.notna(upper.iloc[-1]) else None,
        "bb_lower": float(lower.iloc[-1]) if pd.notna(lower.iloc[-1]) else None,
        "bb_pct": float((close - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1]))
        if pd.notna(upper.iloc[-1]) and pd.notna(lower.iloc[-1]) and upper.iloc[-1] != lower.iloc[-1]
        else None,
        "bb_bandwidth": float(width / basis.iloc[-1])
        if pd.notna(width) and pd.notna(basis.iloc[-1]) and basis.iloc[-1]
        else None,
        "bb_squeeze": bool(
            pd.notna(width)
            and pd.notna(basis.iloc[-1])
            and basis.iloc[-1]
            and (width / basis.iloc[-1]) <= cfg.bb_squeeze_threshold
        ),
    }
