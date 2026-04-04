from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from config import cfg
from data.kite_fetcher import KiteFetcher
from paths import PROJECT_ROOT


class BacktestDataFetcher:
    def __init__(self, fetcher: KiteFetcher | None = None) -> None:
        self.fetcher = fetcher or KiteFetcher()
        self.cache_dir = PROJECT_ROOT / cfg.backtest.cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def _cache_path(self, ticker: str) -> Path:
        return self.cache_dir / f"{ticker}.parquet"

    def fetch(self, ticker: str, force_refresh: bool = False) -> pd.DataFrame:
        cache_path = self._cache_path(ticker)

        if not force_refresh and cache_path.exists():
            df = pd.read_parquet(cache_path)
            df = df.sort_values("date")
            start_date = cfg.backtest.start_date
            end_date = cfg.backtest.end_date
            if start_date:
                df = df[df["date"] >= start_date]
            if end_date:
                df = df[df["date"] <= end_date]
            return df

        df = self.fetcher.fetch(ticker, interval="day")
        if not df.empty and cfg.backtest.cache_data:
            df.to_parquet(cache_path, index=False)
        return df

    def fetch_many(
        self, tickers: list[str], force_refresh: bool = False
    ) -> dict[str, pd.DataFrame]:
        return {ticker: self.fetch(ticker, force_refresh) for ticker in tickers}

    def clear_cache(self) -> None:
        for f in self.cache_dir.glob("*.parquet"):
            f.unlink()

    def get_date_range(self, ticker: str) -> tuple[str, str] | None:
        df = self.fetch(ticker)
        if df.empty:
            return None
        return (df["date"].min().isoformat(), df["date"].max().isoformat())
