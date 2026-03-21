from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from swingtradev3.config import cfg
from swingtradev3.paths import PROJECT_ROOT


@dataclass
class KiteFetcher:
    kite_client: Any | None = None

    def _cache_path(self, ticker: str, interval: str) -> Path:
        return PROJECT_ROOT / cfg.backtest.cache_dir / f"{ticker}_{interval}.parquet"

    def fetch(self, ticker: str, interval: str = "day") -> pd.DataFrame:
        cache_path = self._cache_path(ticker, interval)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        if self.kite_client is None:
            raise RuntimeError(f"No cached candles for {ticker} and no Kite client configured")
        raise NotImplementedError("Live Kite fetching should be implemented with real credentials")
