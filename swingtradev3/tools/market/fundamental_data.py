from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from swingtradev3.models import FundamentalsSnapshot
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class FundamentalDataTool:
    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "fundamentals_cache.json")

    def _load_cache(self) -> dict[str, Any]:
        return read_json(self.cache_path, {})

    def _write_cache(self, payload: dict[str, Any]) -> None:
        write_json(self.cache_path, payload)

    def _from_yfinance(self, ticker: str) -> FundamentalsSnapshot | None:
        try:
            import yfinance as yf

            info = yf.Ticker(f"{ticker}.NS").info
            return FundamentalsSnapshot(
                ticker=ticker,
                pe_ratio=info.get("trailingPE"),
                eps_growth_3yr_pct=info.get("earningsQuarterlyGrowth"),
                debt_equity=info.get("debtToEquity"),
                market_cap_cr=(info.get("marketCap") or 0) / 10_000_000 if info.get("marketCap") else None,
                dividend_yield=(info.get("dividendYield") or 0) * 100 if info.get("dividendYield") else None,
                sector=info.get("sector"),
                industry=info.get("industry"),
                source="yfinance",
                as_of=date.today(),
            )
        except Exception:
            return None

    def _from_nse(self, ticker: str) -> dict[str, Any]:
        data: dict[str, Any] = {}
        try:
            from nsepython import nse_eq

            eq = nse_eq(ticker)
            data["promoter_holding_pct"] = eq.get("shareholdingPattern", {}).get("promoter")
            data["promoter_pledge_pct"] = eq.get("securityWiseDP", {}).get("pledgedPercentage")
        except Exception:
            pass
        return data

    def get_fundamentals(self, ticker: str) -> dict[str, Any]:
        cache = self._load_cache()
        base = self._from_yfinance(ticker)
        if base is None:
            cached = cache.get(ticker)
            if cached:
                cached["is_stale"] = True
                return cached
            return FundamentalsSnapshot(ticker=ticker, is_stale=True, source="cache").model_dump(mode="json")

        nse_fields = self._from_nse(ticker)
        merged = base.model_copy(update=nse_fields)
        cache[ticker] = merged.model_dump(mode="json")
        self._write_cache(cache)
        return merged.model_dump(mode="json")
