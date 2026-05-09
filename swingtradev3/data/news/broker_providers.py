from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from data.news.constants import REQUEST_TIMEOUT_SECONDS
from data.news.parsers import parse_bse_announcements, parse_upstox_news


class NewsBrokerProviderMixin:
    """Broker and exchange API provider adapters."""

    def _item_from_parsed(
        self,
        row: dict[str, Any],
        *,
        provider: str,
        source_type: str,
        default_url: str = "",
        confidence: float | None = None,
    ) -> dict[str, Any]:
        return self._build_news_item(
            provider=provider,
            source_type=source_type,
            title=str(row.get("title") or row.get("heading") or ""),
            url=str(row.get("url") or row.get("article_link") or default_url or ""),
            content=row.get("content") or row.get("content_text"),
            summary=row.get("summary"),
            published_at=row.get("published_at"),
            source_id=str(row.get("source_id") or row.get("id") or ""),
            content_markdown=row.get("content_markdown"),
            confidence=confidence,
            tickers=[str(ticker).upper() for ticker in row.get("tickers", [])],
            isins=[str(isin).upper() for isin in row.get("isins", [])],
            company_names=list(row.get("company_names") or []),
            category=row.get("category"),
        )

    def _from_bse_announcements(self, query: str, *, max_results: int = 5) -> dict[str, Any] | None:
        started = time.monotonic()
        today = self._now_ist().strftime("%Y%m%d")
        url = (
            "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
            f"?strCat=-1&strPrevDate={today}&strScrip=&strSearch=P&strToDate={today}&strType=C"
        )
        try:
            response = self._request_url(url)
            rows = parse_bse_announcements(response.json())
            items = [
                self._item_from_parsed(
                    row,
                    provider="bse_announcements",
                    source_type="official_filing",
                )
                for row in rows
            ]
            items = [item for item in items if self._matches_query(query, item)]
            self._record_provider(
                "bse_announcements",
                started,
                items_seen=len(rows),
                items_emitted=len(items),
            )
            return {"query": query, "results": items[:max_results], "source": "bse_announcements"}
        except Exception as exc:
            self._record_provider("bse_announcements", started, error=exc)
            return None

    @staticmethod
    def _upstox_token() -> str:
        return (
            os.getenv("UPSTOX_ACCESS_TOKEN", "")
            or os.getenv("UPSTOX_API_ACCESS_TOKEN", "")
            or os.getenv("UPSTOX_TOKEN", "")
        ).strip()

    @staticmethod
    def _upstox_instrument_key_for(ticker: str) -> str | None:
        mapping_raw = os.getenv("UPSTOX_INSTRUMENT_KEYS_JSON", "").strip()
        if mapping_raw:
            try:
                mapping = json.loads(mapping_raw)
            except json.JSONDecodeError:
                mapping = {}
            if isinstance(mapping, dict):
                value = mapping.get(ticker.upper())
                if value:
                    return str(value)
        env_key = f"UPSTOX_INSTRUMENT_KEY_{ticker.upper().replace('-', '_')}"
        value = os.getenv(env_key, "").strip()
        return value or None

    def _from_upstox_news(
        self,
        query: str,
        *,
        ticker: str | None = None,
        category: str = "instrument_keys",
        max_results: int = 10,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        token = self._upstox_token()
        if not token:
            self._record_provider(
                "upstox_news",
                started,
                error="UPSTOX_ACCESS_TOKEN not configured",
            )
            return None
        params: dict[str, Any] = {"category": category, "page_number": 1, "page_size": max_results}
        if category == "instrument_keys":
            if not ticker:
                self._record_provider("upstox_news", started, error="ticker required")
                return None
            instrument_key = self._upstox_instrument_key_for(ticker)
            if not instrument_key:
                self._record_provider(
                    "upstox_news",
                    started,
                    error=f"instrument key not configured for {ticker.upper()}",
                )
                return None
            params["instrument_keys"] = instrument_key
        try:
            response = requests.get(
                "https://api.upstox.com/v2/news",
                params=params,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            rows = parse_upstox_news(response.json())
            items = [
                self._item_from_parsed(row, provider="upstox_news", source_type="broker_api")
                for row in rows
            ]
            if ticker:
                for item in items:
                    item["tickers"] = sorted(set([*item.get("tickers", []), ticker.upper()]))
            items = [item for item in items if self._matches_query(query, item)]
            self._record_provider(
                "upstox_news",
                started,
                items_seen=len(rows),
                items_emitted=len(items),
            )
            return {"query": query, "results": items[:max_results], "source": "upstox_news"}
        except Exception as exc:
            self._record_provider("upstox_news", started, error=exc)
            return None
