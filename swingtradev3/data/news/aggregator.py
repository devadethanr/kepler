from __future__ import annotations

from typing import Any

from config import cfg
from data.news.constants import PUBLISHER_PAGE_TARGETS
from data.news.core import NewsCoreMixin
from data.news.providers import NewsProviderMixin


class NewsAggregator(NewsProviderMixin, NewsCoreMixin):
    """Public news aggregation facade."""

    def search_news(
        self,
        query: str,
        *,
        max_results: int = 5,
        time_range: str | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        """Search news with official feeds first, then search fallbacks."""
        key = cache_key or query
        cached = self._cached(key)
        if cached is not None:
            return cached

        payloads: list[dict[str, Any]] = []
        for provider in (
            lambda: self._from_official_feeds(query, max_results=max_results),
            lambda: self._from_bse_announcements(query, max_results=max_results),
            lambda: self._from_publisher_feeds(query, max_results=max_results),
            lambda: self._from_crawler_targets(
                query,
                list(PUBLISHER_PAGE_TARGETS),
                max_results=max_results,
            ),
            lambda: self._from_tavily(
                query,
                max_results=max_results,
                time_range=time_range,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
            ),
            lambda: self._from_ddgs(query, max_results=max_results),
        ):
            payload = provider()
            if payload and payload.get("results"):
                payloads.append(payload)
            result_count = sum(len(item.get("results", [])) for item in payloads)
            if result_count >= max_results:
                break

        merged = self._merge_payloads(query, payloads, max_results=max_results)
        return self._store(key, merged)

    def sweep_market_news(
        self,
        query: str = "Indian stock market today Nifty 200 news",
    ) -> dict[str, Any]:
        """
        Sweep broad market news to extract mentioned tickers.
        Used in Layer 0 of the multi-signal funnel.
        """
        return self.search_news(
            query,
            max_results=int(cfg.research.filter.news_sweep_max_results),
            time_range="week",
            exclude_domains=cfg.research.filter.excluded_news_domains,
        )

    def search_stock_news(self, ticker: str, company_name: str | None = None) -> dict[str, Any]:
        ticker = ticker.upper()
        company_name = company_name or self._company_name_for(ticker)
        max_results = int(cfg.research.filter.stock_news_max_results)
        cache_key = f"{ticker} stock news current"
        cached = self._cached(cache_key)
        if cached is not None:
            cached_results = self.normalize_headlines(
                self._filter_stock_relevant_results(
                    ticker,
                    cached.get("results", []),
                    company_name=company_name,
                )
            )
            if cached_results:
                cached = dict(cached)
                cached["results"] = cached_results
                return cached

        query = self.build_stock_news_query(ticker, company_name)
        trusted = cfg.research.filter.trusted_news_domains
        excluded = cfg.research.filter.excluded_news_domains
        payloads: list[dict[str, Any]] = []
        upstox_payload = self._from_upstox_news(
            query,
            ticker=ticker,
            category="instrument_keys",
            max_results=max_results,
        )
        upstox_payload = self._filter_stock_payload(
            ticker,
            upstox_payload,
            company_name=company_name,
        )
        if upstox_payload and upstox_payload.get("results"):
            payloads.append(upstox_payload)

        search_payload = self.search_news(
            query,
            max_results=max_results,
            time_range="week",
            include_domains=trusted or None,
            exclude_domains=excluded,
            cache_key=f"{ticker} stock news search",
        )
        search_payload = self._filter_stock_payload(
            ticker,
            search_payload,
            company_name=company_name,
        )
        if search_payload and search_payload.get("results"):
            payloads.append(search_payload)
        if (not search_payload or not search_payload.get("results")) and trusted:
            fallback_payload = self.search_news(
                query,
                max_results=max_results,
                time_range="week",
                exclude_domains=excluded,
                cache_key=f"{ticker} stock news search fallback",
            )
            fallback_payload = self._filter_stock_payload(
                ticker,
                fallback_payload,
                company_name=company_name,
            )
            if fallback_payload and fallback_payload.get("results"):
                payloads.append(fallback_payload)

        result_count = sum(len(payload.get("results", [])) for payload in payloads)
        if result_count < max_results:
            crawler_payload = self._from_crawler_targets(
                query,
                self._stock_crawler_targets(ticker, company_name),
                max_results=max_results - result_count,
            )
            crawler_payload = self._filter_stock_payload(
                ticker,
                crawler_payload,
                company_name=company_name,
            )
            if crawler_payload and crawler_payload.get("results"):
                payloads.append(crawler_payload)

        payload = self._merge_payloads(query, payloads, max_results=max_results)
        payload["results"] = self.normalize_headlines(
            self._filter_stock_relevant_results(
                ticker,
                payload.get("results", []),
                company_name=company_name,
            )
        )
        payload["provider_health"] = self.provider_health
        return self._store(cache_key, payload)

    def dashboard_payload(self, *, limit: int = 100) -> dict[str, Any]:
        items = list(reversed(self._load_news_items()))[:limit]
        provider_health = self._load_provider_health()
        try:
            from memory.db import session_scope
            from memory.repository import MemoryRepository

            with session_scope() as session:
                repo = MemoryRepository(session)
                db_items = repo.list_news_items(limit=limit)
                db_health = repo.list_news_provider_health()
            if db_items:
                items = db_items
            if db_health:
                provider_health = db_health
        except Exception:
            pass
        source_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        for item in items:
            provider = str(item.get("provider") or item.get("source") or "unknown")
            source_type = str(item.get("source_type") or "unknown")
            category = str(item.get("category") or "unknown")
            source_counts[provider] = source_counts.get(provider, 0) + 1
            type_counts[source_type] = type_counts.get(source_type, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1
        return {
            "items": items,
            "provider_health": provider_health,
            "source_counts": dict(sorted(source_counts.items())),
            "source_type_counts": dict(sorted(type_counts.items())),
            "category_counts": dict(sorted(category_counts.items())),
            "item_count": len(items),
            "last_updated_at_ist": self._now_ist().isoformat(),
        }
