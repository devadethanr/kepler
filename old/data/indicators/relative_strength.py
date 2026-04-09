from __future__ import annotations

import pandas as pd

from swingtradev3.data.indicators.common import ensure_ohlcv


def _return_pct(series: pd.Series, periods: int) -> float | None:
    if len(series) <= periods:
        return None
    prev = series.iloc[-periods - 1]
    if not prev:
        return None
    return float((series.iloc[-1] / prev - 1.0) * 100)


def calculate(
    df: pd.DataFrame,
    cfg,
    benchmark_close: pd.Series | None = None,
    sector_close: pd.Series | None = None,
    rank: int | None = None,
) -> dict[str, float | bool | int | None]:
    candles = ensure_ohlcv(df)
    close = candles["close"]
    periods = cfg.periods
    values: dict[str, float | bool | int | None] = {}
    outperforming = True
    for period in periods:
        stock_ret = _return_pct(close, period)
        benchmark_ret = _return_pct(benchmark_close, period) if benchmark_close is not None else None
        key = f"rs_vs_nifty_{period}d"
        values[key] = (stock_ret - benchmark_ret) if stock_ret is not None and benchmark_ret is not None else None
        if values[key] is not None and values[key] < 0:
            outperforming = False
    values["rs_vs_sector"] = (
        _return_pct(close, periods[0]) - _return_pct(sector_close, periods[0])
        if sector_close is not None and _return_pct(close, periods[0]) is not None and _return_pct(sector_close, periods[0]) is not None
        else None
    )
    values["rs_rank_nifty200"] = rank
    values["outperforming_index"] = outperforming
    return values
