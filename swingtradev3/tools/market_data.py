from __future__ import annotations

import pandas as pd

from swingtradev3.config import cfg
from swingtradev3.data.indicators import calculate_all
from swingtradev3.data.kite_fetcher import KiteFetcher


class MarketDataTool:
    def __init__(self, fetcher: KiteFetcher | None = None) -> None:
        self.fetcher = fetcher or KiteFetcher()

    async def get_eod_data_async(
        self,
        ticker: str,
        benchmark_close: pd.Series | None = None,
        sector_close: pd.Series | None = None,
        rank: int | None = None,
    ) -> dict[str, object]:
        candles = await self.fetcher.fetch_async(ticker, interval="day")
        indicators = calculate_all(candles, cfg.indicators, benchmark_close, sector_close, rank)
        latest = candles.iloc[-1].to_dict()
        latest["ticker"] = ticker
        latest["change_pct"] = (
            float((candles["close"].iloc[-1] / candles["close"].iloc[-2] - 1) * 100)
            if len(candles) > 1
            else 0.0
        )
        latest.update(indicators)
        return latest

    def get_eod_data(
        self,
        ticker: str,
        benchmark_close: pd.Series | None = None,
        sector_close: pd.Series | None = None,
        rank: int | None = None,
    ) -> dict[str, object]:
        candles = self.fetcher.fetch(ticker, interval="day")
        indicators = calculate_all(candles, cfg.indicators, benchmark_close, sector_close, rank)
        latest = candles.iloc[-1].to_dict()
        latest["ticker"] = ticker
        latest["change_pct"] = float((candles["close"].iloc[-1] / candles["close"].iloc[-2] - 1) * 100) if len(candles) > 1 else 0.0
        latest.update(indicators)
        return latest
