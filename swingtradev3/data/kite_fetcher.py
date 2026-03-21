from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from swingtradev3.config import cfg
from swingtradev3.mcp_client import KiteMCPClient
from swingtradev3.paths import PROJECT_ROOT


@dataclass
class KiteFetcher:
    kite_client: Any | None = None
    mcp_client: KiteMCPClient | None = None

    def _cache_path(self, ticker: str, interval: str) -> Path:
        return PROJECT_ROOT / cfg.backtest.cache_dir / f"{ticker}_{interval}.parquet"

    async def fetch_async(self, ticker: str, interval: str = "day") -> pd.DataFrame:
        cache_path = self._cache_path(ticker, interval)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        if cfg.trading.mode.value == "live":
            client = self.mcp_client or KiteMCPClient()
            result = await client.call_tool(
                "get_historical_data",
                {
                    "tradingsymbol": ticker,
                    "exchange": cfg.trading.exchange,
                    "interval": interval,
                },
            )
            candles = result.get("candles") or result.get("data") or []
            if not candles:
                raise RuntimeError(f"Kite MCP returned no historical candles for {ticker}")
            df = pd.DataFrame(candles)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            return df
        if self.kite_client is None:
            raise RuntimeError(f"No cached candles for {ticker} and no Kite client configured")
        raise NotImplementedError("Direct Kite client fetching is not implemented; use the self-hosted MCP server")

    def fetch(self, ticker: str, interval: str = "day") -> pd.DataFrame:
        cache_path = self._cache_path(ticker, interval)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        if self.kite_client is None:
            raise RuntimeError(f"No cached candles for {ticker} and no Kite client configured")
        raise NotImplementedError("Use fetch_async() for live MCP-backed data access")
