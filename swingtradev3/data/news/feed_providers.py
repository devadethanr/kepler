from __future__ import annotations

import hashlib
import time
from typing import Any

from data.news.constants import OFFICIAL_RSS_SOURCES, PUBLISHER_RSS_SOURCES


class NewsFeedProviderMixin:
    """RSS provider adapters for official exchange feeds and publisher feeds."""

    def _from_rss_sources(
        self,
        query: str,
        *,
        sources: tuple[dict[str, str], ...],
        source_name: str,
        max_results: int = 5,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            import feedparser
        except Exception as exc:
            self._record_provider(source_name, started, error=exc)
            return None

        results: list[dict[str, Any]] = []
        items_seen = 0
        first_error: Exception | None = None
        for source in sources:
            source_started = time.monotonic()
            provider = source["provider"]
            try:
                response = self._request_url(source["url"])
                parsed = feedparser.parse(response.content)
                entries = list(parsed.entries or [])
                items_seen += len(entries)
                emitted = 0
                for entry in entries:
                    title = str(entry.get("title") or "")
                    link = str(entry.get("link") or "").strip()
                    published_at = entry.get("published") or entry.get("updated")
                    source_id = str(
                        entry.get("id") or entry.get("guid") or link or ""
                    ).strip()
                    if not source_id or source_id == source["url"]:
                        seed = f"{source['url']}:{title}:{published_at}"
                        source_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
                    url = link or f"{source['url']}#news-{source_id}"
                    item = self._build_news_item(
                        provider=provider,
                        source_type=source["source_type"],
                        title=title,
                        url=url,
                        content=str(entry.get("summary") or entry.get("description") or ""),
                        summary=str(entry.get("summary") or entry.get("description") or ""),
                        published_at=published_at,
                        source_id=source_id,
                    )
                    if not item["title"] and not item["url"]:
                        continue
                    if not self._matches_query(query, item):
                        continue
                    results.append(item)
                    emitted += 1
                    if len(results) >= max_results:
                        break
                self._record_provider(
                    provider,
                    source_started,
                    items_seen=len(entries),
                    items_emitted=emitted,
                )
            except Exception as exc:
                first_error = first_error or exc
                self._record_provider(provider, source_started, error=exc)
            if len(results) >= max_results:
                break

        if not results:
            self._record_provider(source_name, started, items_seen=items_seen, error=first_error)
            return None
        self._record_provider(
            source_name,
            started,
            items_seen=items_seen,
            items_emitted=len(results),
        )
        return {"query": query, "results": results, "source": source_name}

    def _from_official_feeds(self, query: str, *, max_results: int = 5) -> dict[str, Any] | None:
        return self._from_rss_sources(
            query,
            sources=OFFICIAL_RSS_SOURCES,
            source_name="official_feeds",
            max_results=max_results,
        )

    def _from_publisher_feeds(self, query: str, *, max_results: int = 5) -> dict[str, Any] | None:
        return self._from_rss_sources(
            query,
            sources=PUBLISHER_RSS_SOURCES,
            source_name="publisher_feeds",
            max_results=max_results,
        )
