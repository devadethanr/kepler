from __future__ import annotations

import numpy as np
import pandas as pd


def ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    return df.copy()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    avg_loss = losses.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    line = fast_ema - slow_ema
    signal_line = ema(line, signal)
    hist = line - signal_line
    return line, signal_line, hist


def stochastic(df: pd.DataFrame, k_period: int, d_period: int) -> tuple[pd.Series, pd.Series]:
    low_min = df["low"].rolling(k_period, min_periods=k_period).min()
    high_max = df["high"].rolling(k_period, min_periods=k_period).max()
    k = 100 * (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan)
    d = k.rolling(d_period, min_periods=d_period).mean()
    return k, d


def roc(series: pd.Series, length: int) -> pd.Series:
    return (series / series.shift(length) - 1.0) * 100


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr_components = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    )
    return tr_components.max(axis=1)


def atr(df: pd.DataFrame, length: int) -> pd.Series:
    return true_range(df).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def bollinger_bands(series: pd.Series, length: int, std: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    basis = sma(series, length)
    dev = series.rolling(length, min_periods=length).std(ddof=0)
    upper = basis + dev * std
    lower = basis - dev * std
    return basis, upper, lower


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff().fillna(0.0))
    return (direction * df["volume"]).cumsum()


def mfi(df: pd.DataFrame, length: int) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    money_flow = typical_price * df["volume"]
    direction = typical_price.diff()
    positive = money_flow.where(direction > 0, 0.0)
    negative = money_flow.where(direction < 0, 0.0)
    pos_sum = positive.rolling(length, min_periods=length).sum()
    neg_sum = negative.rolling(length, min_periods=length).sum().replace(0, np.nan)
    ratio = pos_sum / neg_sum
    return 100 - (100 / (1 + ratio))


def adx(df: pd.DataFrame, length: int) -> pd.Series:
    up_move = df["high"].diff()
    down_move = -df["low"].diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    tr = true_range(df)
    atr_series = tr.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr_series.replace(0, np.nan))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / length, adjust=False).mean() / atr_series.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
