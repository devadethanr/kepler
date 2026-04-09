from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import re
from typing import Any

import requests

from swingtradev3.models import FundamentalsSnapshot
from swingtradev3.paths import CONTEXT_DIR
from swingtradev3.storage import read_json, write_json


class FundamentalDataTool:
    CACHE_MAX_AGE_DAYS = 7

    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "fundamentals_cache.json")

    def _load_cache(self) -> dict[str, Any]:
        return read_json(self.cache_path, {})

    def _write_cache(self, payload: dict[str, Any]) -> None:
        write_json(self.cache_path, payload)

    def _cached_snapshot(self, ticker: str) -> FundamentalsSnapshot | None:
        cached = self._load_cache().get(ticker)
        if not cached:
            return None
        snapshot = FundamentalsSnapshot.model_validate(cached)
        if snapshot.as_of is None:
            return snapshot
        age = (date.today() - snapshot.as_of).days
        if age <= self.CACHE_MAX_AGE_DAYS:
            return snapshot
        return snapshot.model_copy(update={"is_stale": True})

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
        try:
            from nsetools import Nse

            quote = Nse().get_quote(ticker)
            company_name = quote.get("companyName")
            if company_name:
                data["industry"] = data.get("industry") or company_name
        except Exception:
            pass
        return data

    @staticmethod
    def _extract_number(markdown: str, label: str) -> float | None:
        pattern = re.compile(rf"{re.escape(label)}\s*\n+([\d,]+(?:\.\d+)?)", re.IGNORECASE)
        match = pattern.search(markdown)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", ""))
        except ValueError:
            return None

    def _from_firecrawl(self, ticker: str) -> dict[str, Any]:
        api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
        if not api_key:
            return {}
        try:
            response = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "url": f"https://www.screener.in/company/{ticker}/consolidated/",
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            markdown = (payload.get("data") or {}).get("markdown") or ""
        except Exception:
            return {}

        return {
            "market_cap_cr": self._extract_number(markdown, "Market Cap"),
            "pe_ratio": self._extract_number(markdown, "Stock P/E"),
            "dividend_yield": self._extract_number(markdown, "Dividend Yield"),
            "promoter_holding_pct": self._extract_number(markdown, "Promoter holding"),
            "promoter_pledge_pct": self._extract_number(markdown, "Pledged percentage"),
        }

    def get_fundamentals(self, ticker: str) -> dict[str, Any]:
        cached = self._cached_snapshot(ticker)
        if cached is not None and not cached.is_stale:
            return cached.model_dump(mode="json")

        cache = self._load_cache()
        base = self._from_yfinance(ticker)
        if base is None:
            if cached:
                return cached.model_copy(update={"is_stale": True}).model_dump(mode="json")
            return FundamentalsSnapshot(ticker=ticker, is_stale=True, source="cache").model_dump(mode="json")

        nse_fields = self._from_nse(ticker)
        firecrawl_fields = self._from_firecrawl(ticker)
        merged = base.model_copy(update={**nse_fields, **{k: v for k, v in firecrawl_fields.items() if v is not None}})
        cache[ticker] = merged.model_dump(mode="json")
        self._write_cache(cache)
        return merged.model_dump(mode="json")
