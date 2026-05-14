from __future__ import annotations

import os
import time
from typing import Any


class NewsSearchProviderMixin:
    """Search API provider adapters."""

    def _from_tavily(
        self,
        query: str,
        *,
        max_results: int = 5,
        time_range: str | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            self._record_provider("tavily", started, error="TAVILY_API_KEY not configured")
            return None
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            request: dict[str, Any] = {
                "query": query,
                "topic": "news",
                "search_depth": "basic",
                "max_results": max_results,
            }
            if time_range:
                request["time_range"] = time_range
            if include_domains:
                request["include_domains"] = include_domains
            if exclude_domains:
                request["exclude_domains"] = exclude_domains
            response = client.search(
                **request,
            )
        except Exception as exc:
            self._record_provider("tavily", started, error=exc)
            return None

        results = []
        for item in response.get("results", []):
            results.append(
                self._build_news_item(
                    provider="tavily",
                    source_type="search_api",
                    title=str(item.get("title") or ""),
                    url=str(item.get("url") or ""),
                    content=item.get("content"),
                    summary=item.get("content"),
                    published_at=item.get("published_date") or item.get("published_at"),
                    confidence=self._as_float(item.get("score"), 0.7),
                )
            )
        self._record_provider(
            "tavily",
            started,
            items_seen=len(response.get("results", [])),
            items_emitted=len(results),
        )
        return {"query": query, "results": results, "source": "tavily"}

    def _from_ddgs(self, query: str, *, max_results: int = 5) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            from duckduckgo_search import DDGS

            ddgs = DDGS()
            try:
                items = ddgs.news(query, timelimit="w", max_results=max_results)
            except Exception:
                items = ddgs.text(query, max_results=max_results)
        except Exception as exc:
            self._record_provider("ddgs", started, error=exc)
            return None

        results = []
        for item in items or []:
            results.append(
                self._build_news_item(
                    provider="ddgs",
                    source_type="search_api",
                    title=str(item.get("title") or ""),
                    url=str(item.get("href") or item.get("url") or ""),
                    content=item.get("body") or item.get("snippet"),
                    summary=item.get("body") or item.get("snippet"),
                    published_at=item.get("date"),
                    confidence=0.65,
                )
            )
        self._record_provider("ddgs", started, items_seen=len(results), items_emitted=len(results))
        return {"query": query, "results": results, "source": "ddgs"}
