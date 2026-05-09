from __future__ import annotations

from pathlib import Path

from config import cfg
from data.news import NewsAggregator
from paths import CONTEXT_DIR


class NewsSearchTool:
    def __init__(
        self,
        cache_path: Path | None = None,
        ttl_hours: int | None = None,
        ttl_minutes: int | None = None,
    ) -> None:
        self.cache_path = cache_path or (CONTEXT_DIR / "news_cache.json")
        self.aggregator = NewsAggregator(
            cache_path=self.cache_path,
            ttl_hours=ttl_hours,
            ttl_minutes=ttl_minutes,
        )

    def search_news(self, query: str) -> dict[str, object]:
        payload = self.aggregator.search_news(
            query,
            time_range="week",
            exclude_domains=cfg.research.filter.excluded_news_domains,
        )
        payload["results"] = self.aggregator.normalize_headlines(payload.get("results", []))
        return payload
