from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from paths import CONTEXT_DIR
from storage import read_json, write_json


class NewsSearchTool:
    def __init__(self, cache_path: Path | None = None, ttl_hours: int = 6) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "news_cache.json")
        self.ttl_hours = ttl_hours

    def _load_cache(self) -> dict[str, Any]:
        return read_json(self.cache_path, {})

    def _write_cache(self, payload: dict[str, Any]) -> None:
        write_json(self.cache_path, payload)

    def _cached(self, query: str) -> dict[str, object] | None:
        cache = self._load_cache()
        item = cache.get(query)
        if not item:
            return None
        fetched_at = item.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = datetime.utcnow() - datetime.fromisoformat(str(fetched_at))
        except ValueError:
            return None
        if age > timedelta(hours=self.ttl_hours):
            return None
        return item.get("payload")

    def _store(self, query: str, payload: dict[str, object]) -> dict[str, object]:
        cache = self._load_cache()
        cache[query] = {"fetched_at": datetime.utcnow().isoformat(), "payload": payload}
        self._write_cache(cache)
        return payload

    def _from_tavily(self, query: str) -> dict[str, object] | None:
        api_key = os.getenv("TAVILY_API_KEY", "").strip()
        if not api_key:
            return None
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                topic="news",
                search_depth="basic",
                max_results=5,
            )
        except Exception:
            return None

        results = []
        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": item.get("content"),
                    "score": item.get("score"),
                    "published_at": item.get("published_date") or item.get("published_at"),
                }
            )
        return {"query": query, "results": results, "source": "tavily"}

    def _from_ddgs(self, query: str) -> dict[str, object] | None:
        try:
            from duckduckgo_search import DDGS

            items = DDGS().text(query, max_results=5)
        except Exception:
            return None

        results = []
        for item in items or []:
            results.append(
                {
                    "title": item.get("title"),
                    "url": item.get("href") or item.get("url"),
                    "content": item.get("body") or item.get("snippet"),
                    "published_at": item.get("date"),
                }
            )
        return {"query": query, "results": results, "source": "ddgs"}

    def search_news(self, query: str) -> dict[str, object]:
        cached = self._cached(query)
        if cached is not None:
            return cached

        payload = self._from_tavily(query)
        if payload is None:
            payload = self._from_ddgs(query)
        if payload is None:
            return {"query": query, "results": [], "source": "not_configured"}
        return self._store(query, payload)
