"""Indicator calculations."""

from __future__ import annotations

import pandas as pd

from data.indicators import momentum, patterns, relative_strength, structure, trend, volatility, volume


def calculate_all(
    candles: pd.DataFrame,
    cfg,
    benchmark_close: pd.Series | None = None,
    sector_close: pd.Series | None = None,
    rank: int | None = None,
) -> dict[str, object]:
    output: dict[str, object] = {}
    output.update(momentum.calculate(candles, cfg.momentum))
    output.update(trend.calculate(candles, cfg.trend))
    output.update(volatility.calculate(candles, cfg.volatility))
    output.update(volume.calculate(candles, cfg.volume))
    output.update(structure.calculate(candles, cfg.structure))
    output.update(
        relative_strength.calculate(candles, cfg.relative_strength, benchmark_close, sector_close, rank)
    )
    output.update(patterns.calculate(candles, cfg.patterns))
    return output
