from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from urllib.parse import quote_plus

import requests

from data.news.parsers import parse_source_specific_html


class NewsCrawlerProviderMixin:
    """Static-page and browser crawler provider adapters."""

    def _from_static_url(
        self,
        url: str,
        *,
        query: str,
        provider: str,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            response = self._request_url(url)
            html = response.text
            parsed_rows = parse_source_specific_html(provider, html, str(response.url or url))
            parsed_items = [
                self._item_from_parsed(
                    row,
                    provider=provider,
                    source_type="crawler",
                    default_url=str(response.url or url),
                    confidence=0.66,
                )
                for row in parsed_rows
            ]
            parsed_items = [item for item in parsed_items if self._matches_query(query, item)]
            if parsed_items:
                self._record_provider(
                    provider,
                    started,
                    items_seen=len(parsed_rows),
                    items_emitted=len(parsed_items),
                )
                return parsed_items[0]
            title = self._html_title(html) or url
            text = self._strip_html(html)
            if len(text) < 120:
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            item = self._build_news_item(
                provider=provider,
                source_type="crawler",
                title=title,
                url=str(response.url or url),
                content=text[:5000],
                summary=text[:500],
                confidence=0.6,
            )
            if not self._matches_query(query, item):
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            self._record_provider(provider, started, items_seen=1, items_emitted=1)
            return item
        except Exception as exc:
            self._record_provider(provider, started, error=exc)
            return None

    def _from_trafilatura_url(
        self,
        url: str,
        *,
        query: str,
        provider: str,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            import trafilatura

            response = self._request_url(url)
            html = response.text
            text = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                output_format="txt",
                url=str(response.url or url),
            )
            if not text:
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            metadata = trafilatura.extract_metadata(html, default_url=str(response.url or url))
            title = getattr(metadata, "title", None) or self._html_title(html) or url
            published_at = getattr(metadata, "date", None)
            item = self._build_news_item(
                provider=provider,
                source_type="crawler",
                title=title,
                url=str(response.url or url),
                content=text,
                summary=text[:500],
                published_at=published_at,
                confidence=0.68,
            )
            if not self._matches_query(query, item):
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            self._record_provider(provider, started, items_seen=1, items_emitted=1)
            return item
        except Exception as exc:
            self._record_provider(provider, started, error=exc)
            return None

    @staticmethod
    def _markdown_text(markdown: Any) -> str:
        if not markdown:
            return ""
        for attr in ("fit_markdown", "raw_markdown", "markdown_with_citations"):
            value = getattr(markdown, attr, None)
            if value:
                return str(value)
        return str(markdown)

    def _from_crawl4ai_url(
        self,
        url: str,
        *,
        query: str,
        provider: str,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        try:
            asyncio.get_running_loop()
            self._record_provider(provider, started, error="running event loop; crawl4ai skipped")
            return None
        except RuntimeError:
            pass

        async def crawl() -> dict[str, Any] | None:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

            browser_config = BrowserConfig(headless=True)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=20_000,
                excluded_tags=["nav", "footer", "script", "style"],
            )
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
            if not getattr(result, "success", True):
                raise RuntimeError(getattr(result, "error_message", "crawl4ai failed"))
            markdown = self._markdown_text(getattr(result, "markdown", None))
            html = getattr(result, "cleaned_html", None) or getattr(result, "html", None) or ""
            text = markdown or self._strip_html(html)
            if not text:
                return None
            title = self._html_title(html) or url
            redirected_url = getattr(result, "redirected_url", None) or url
            item = self._build_news_item(
                provider=provider,
                source_type="crawler",
                title=title,
                url=str(redirected_url),
                content=self._strip_html(text)[:5000],
                summary=self._strip_html(text)[:500],
                content_markdown=markdown,
                confidence=0.72,
            )
            return item if self._matches_query(query, item) else None

        try:
            item = asyncio.run(crawl())
            self._record_provider(
                provider,
                started,
                items_seen=1,
                items_emitted=1 if item else 0,
            )
            return item
        except Exception as exc:
            self._record_provider(provider, started, error=exc)
            return None

    def _from_firecrawl_url(
        self,
        url: str,
        *,
        query: str,
        provider: str,
    ) -> dict[str, Any] | None:
        started = time.monotonic()
        api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
        if not api_key:
            self._record_provider(provider, started, error="FIRECRAWL_API_KEY not configured")
            return None
        try:
            response = requests.post(
                "https://api.firecrawl.dev/v1/scrape",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "url": url,
                    "formats": ["markdown"],
                    "onlyMainContent": True,
                },
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or {}
            markdown = str(data.get("markdown") or "")
            metadata = data.get("metadata") or {}
            text = self._strip_html(markdown)
            if not text:
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            item = self._build_news_item(
                provider=provider,
                source_type="crawler",
                title=str(metadata.get("title") or url),
                url=str(metadata.get("sourceURL") or metadata.get("url") or url),
                content=text[:5000],
                summary=text[:500],
                content_markdown=markdown,
                confidence=0.7,
            )
            if not self._matches_query(query, item):
                self._record_provider(provider, started, items_seen=1, items_emitted=0)
                return None
            self._record_provider(provider, started, items_seen=1, items_emitted=1)
            return item
        except Exception as exc:
            self._record_provider(provider, started, error=exc)
            return None

    def _from_static_target_items(
        self,
        url: str,
        *,
        query: str,
        provider: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        started = time.monotonic()
        try:
            response = self._request_url(url)
            rows = parse_source_specific_html(provider, response.text, str(response.url or url))
            items = [
                self._item_from_parsed(
                    row,
                    provider=provider,
                    source_type="crawler",
                    default_url=str(response.url or url),
                    confidence=0.66,
                )
                for row in rows
            ]
            items = [item for item in items if self._matches_query(query, item)]
            self._record_provider(
                provider,
                started,
                items_seen=len(rows),
                items_emitted=len(items),
            )
            return items[:max_results]
        except Exception as exc:
            self._record_provider(provider, started, error=exc)
            return []

    def _crawl_url_with_priority(
        self,
        url: str,
        *,
        query: str,
        provider: str,
    ) -> dict[str, Any] | None:
        for extractor in (
            self._from_static_url,
            self._from_trafilatura_url,
            self._from_crawl4ai_url,
            self._from_firecrawl_url,
        ):
            item = extractor(url, query=query, provider=provider)
            if item:
                return item
        return None

    def _from_crawler_targets(
        self,
        query: str,
        targets: list[dict[str, str]],
        *,
        max_results: int = 5,
    ) -> dict[str, Any] | None:
        results = []
        for target in targets:
            if target["provider"].endswith("_rss"):
                payload = self._from_rss_sources(
                    query,
                    sources=(
                        {
                            "provider": target["provider"],
                            "source_type": "publisher_rss",
                            "url": target["url"],
                        },
                    ),
                    source_name=target["provider"],
                    max_results=max_results - len(results),
                )
                if payload and payload.get("results"):
                    results.extend(payload["results"])
                if len(results) >= max_results:
                    break
                continue
            target_items = self._from_static_target_items(
                target["url"],
                query=query,
                provider=target["provider"],
                max_results=max_results - len(results),
            )
            if target_items:
                results.extend(target_items)
                if len(results) >= max_results:
                    break
                continue
            item = self._crawl_url_with_priority(
                target["url"],
                query=query,
                provider=target["provider"],
            )
            if item:
                results.append(item)
            if len(results) >= max_results:
                break
        if not results:
            return None
        return {"query": query, "results": results, "source": "crawler_targets"}

    def _stock_crawler_targets(
        self,
        ticker: str,
        company_name: str | None = None,
    ) -> list[dict[str, str]]:
        company = (company_name or ticker).strip()
        slug = self._slugify(company)
        topic = quote_plus(f"{company} {ticker} stock India")
        return [
            {
                "provider": "google_news_rss",
                "url": f"https://news.google.com/rss/search?q={topic}&hl=en-IN&gl=IN&ceid=IN:en",
            },
            {"provider": "groww_crawler", "url": f"https://groww.in/stocks/{slug}"},
            {
                "provider": "moneycontrol_tag_crawler",
                "url": f"https://www.moneycontrol.com/news/tags/-{slug}.html",
            },
            {"provider": "screener_crawler", "url": f"https://www.screener.in/company/{ticker}/"},
            {
                "provider": "tradingview_crawler",
                "url": f"https://in.tradingview.com/symbols/NSE-{ticker}/news/",
            },
        ]
