from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from auth.kite.client import fetch_historical_data, has_kite_session
from config import cfg
from integrations.kite.mcp_client import KiteMCPClient
from paths import PROJECT_ROOT
from health_manager import update_service_status


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
            if has_kite_session():
                try:
                    candles = fetch_historical_data(
                        ticker, cfg.trading.exchange, interval
                    )
                    if not candles:
                        raise RuntimeError(
                            f"Kite returned no historical candles for {ticker}"
                        )
                    df = pd.DataFrame(candles)
                    if "date" in df.columns:
                        df["date"] = pd.to_datetime(df["date"])
                    update_service_status("kite_api", True)
                    return df
                except Exception:
                    pass
            try:
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
                    raise RuntimeError(
                        f"Kite MCP returned no historical candles for {ticker}"
                    )
                df = pd.DataFrame(candles)
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                update_service_status("kite_api", True)
                return df
            except Exception as e:
                update_service_status("kite_api", False, str(e))
                raise e
        if self.kite_client is None:
            raise RuntimeError(
                f"No cached candles for {ticker} and no Kite client configured"
            )
        raise NotImplementedError(
            "Direct Kite client fetching is not implemented; use the self-hosted MCP server"
        )

    def fetch(self, ticker: str, interval: str = "day") -> pd.DataFrame:
        cache_path = self._cache_path(ticker, interval)
        if cache_path.exists():
            return pd.read_parquet(cache_path)
        # Use direct Kite in both live and paper modes if session exists
        if cfg.trading.mode.value in ("live", "paper") and has_kite_session():
            try:
                candles = fetch_historical_data(ticker, cfg.trading.exchange, interval)
                if not candles:
                    raise RuntimeError(
                        f"Kite returned no historical candles for {ticker}"
                    )
                df = pd.DataFrame(candles)
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                update_service_status("kite_api", True)
                return df
            except Exception as exc:
                update_service_status("kite_api", False, str(exc))
                raise RuntimeError(
                    f"Direct Kite historical access failed for {ticker}; use fetch_async() for MCP fallback"
                ) from exc
        if self.kite_client is None:
            raise RuntimeError(
                f"No cached candles for {ticker} and no Kite client configured"
            )
        raise NotImplementedError("Use fetch_async() for live MCP-backed data access")
