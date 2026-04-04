from __future__ import annotations

import pandas as pd

from data.indicators.common import ensure_ohlcv, macd, roc, rsi, stochastic


def calculate(df: pd.DataFrame, cfg) -> dict[str, float | bool | None]:
    candles = ensure_ohlcv(df)
    rsi_series = rsi(candles["close"], cfg.rsi_length)
    macd_line, signal_line, hist = macd(
        candles["close"], cfg.macd_fast, cfg.macd_slow, cfg.macd_signal
    )
    stoch_k, stoch_d = stochastic(candles, cfg.stoch_k, cfg.stoch_d)
    roc_series = roc(candles["close"], cfg.roc_length)
    crossover = bool(macd_line.iloc[-1] > signal_line.iloc[-1]) if len(candles) else False
    return {
        "rsi_14": float(rsi_series.iloc[-1]) if pd.notna(rsi_series.iloc[-1]) else None,
        "macd": float(macd_line.iloc[-1]) if pd.notna(macd_line.iloc[-1]) else None,
        "macd_signal": float(signal_line.iloc[-1]) if pd.notna(signal_line.iloc[-1]) else None,
        "macd_hist": float(hist.iloc[-1]) if pd.notna(hist.iloc[-1]) else None,
        "macd_crossover": crossover,
        "stoch_k": float(stoch_k.iloc[-1]) if pd.notna(stoch_k.iloc[-1]) else None,
        "stoch_d": float(stoch_d.iloc[-1]) if pd.notna(stoch_d.iloc[-1]) else None,
        "roc_10": float(roc_series.iloc[-1]) if pd.notna(roc_series.iloc[-1]) else None,
    }
