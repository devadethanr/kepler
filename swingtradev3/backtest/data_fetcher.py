from __future__ import annotations

from typing import Any

import pandas as pd

from swingtradev3.data.kite_fetcher import KiteFetcher


class BacktestDataFetcher:
    def __init__(self, fetcher: KiteFetcher | None = None) -> None:
        self.fetcher = fetcher or KiteFetcher()

    def fetch_many(self, tickers: list[str]) -> dict[str, pd.DataFrame]:
        return {ticker: self.fetcher.fetch(ticker, interval="day") for ticker in tickers}
