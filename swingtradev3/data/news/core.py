from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from config import cfg
from data.news.constants import (
    ALERT_HISTORY_PATH,
    CONTEXT_DIR,
    GENERIC_NEWS_TERMS,
    IST_ZONE,
    NEWS_AUDIT_MAX_ITEMS,
    NEWS_ITEMS_PATH,
    NEWS_PROVIDER_HEALTH_PATH,
    REQUEST_TIMEOUT_SECONDS,
    SOURCE_TYPE_CONFIDENCE,
)
from data.news.parsers import extract_tickers_from_text, infer_category
from data.nifty200_loader import Nifty200Loader
from storage import read_json, write_json
from time_utils import parse_datetime_utc, utc_now


class NewsCoreMixin:
    """Shared cache, persistence, normalization, and item-building helpers."""

    def __init__(
        self,
        cache_path: Path | None = None,
        ttl_hours: int | None = None,
        ttl_minutes: int | None = None,
        items_path: Path | None = None,
        provider_health_path: Path | None = None,
    ) -> None:
        self.persist_files = any(
            path is not None for path in (cache_path, items_path, provider_health_path)
        )
        self.cache_path = cache_path or (CONTEXT_DIR / "news_cache.json")
        base_dir = self.cache_path.parent
        self.items_path = items_path or (
            NEWS_ITEMS_PATH if cache_path is None else base_dir / "news_items.json"
        )
        self.provider_health_path = provider_health_path or (
            NEWS_PROVIDER_HEALTH_PATH
            if cache_path is None
            else base_dir / "news_provider_health.json"
        )
        self.alert_history_path = ALERT_HISTORY_PATH if cache_path is None else base_dir / "news_alert_history.json"
        if ttl_minutes is None:
            ttl_minutes = int(cfg.data.news_cache_ttl_minutes)
        if ttl_hours is not None:
            ttl_minutes = ttl_hours * 60
        self.ttl_minutes = ttl_minutes
        self.provider_health: dict[str, dict[str, Any]] = self._load_provider_health()
        self._universe_entries: list[dict[str, str]] | None = None
        self._memory_cache: dict[str, Any] = {}
        self._memory_items: list[dict[str, Any]] = []
        self._alert_history: dict[str, str] = {}
        self.persist_postgres = not self.persist_files

    @staticmethod
    def _now_ist() -> datetime:
        return datetime.now(IST_ZONE)

    def _load_provider_health(self) -> dict[str, dict[str, Any]]:
        if not self.persist_files:
            return {}
        try:
            payload = read_json(self.provider_health_path, {})
        except (OSError, TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_provider_health(self) -> None:
        if not self.persist_files:
            return
        write_json(self.provider_health_path, self.provider_health)

    def _load_news_items(self) -> list[dict[str, Any]]:
        if not self.persist_files:
            return list(self._memory_items)
        try:
            payload = read_json(self.items_path, [])
        except (OSError, TypeError, ValueError):
            return []
        return payload if isinstance(payload, list) else []

    def _write_news_items(self, items: list[dict[str, Any]]) -> None:
        if not self.persist_files:
            self._memory_items = items[-NEWS_AUDIT_MAX_ITEMS:]
            return
        write_json(self.items_path, items[-NEWS_AUDIT_MAX_ITEMS:])

    def _persist_results(self, results: list[dict[str, Any]]) -> None:
        if not results:
            self._write_provider_health()
            self._persist_postgres([])
            return
        existing = self._load_news_items()
        by_key = {self._result_key(item): item for item in existing if self._result_key(item)}
        for item in results:
            key = self._result_key(item)
            if key:
                by_key[key] = item
        ordered = sorted(
            by_key.values(),
            key=lambda item: str(
                item.get("published_at_ist")
                or item.get("published_at_utc")
                or item.get("fetched_at_ist")
                or ""
            ),
        )
        self._write_news_items(ordered)
        self._write_provider_health()
        self._persist_postgres(results)
        self._persist_context_graph(results)

    def _persist_postgres(self, results: list[dict[str, Any]]) -> None:
        if not self.persist_postgres:
            return
        try:
            from memory.db import session_scope
            from memory.repository import MemoryRepository

            with session_scope() as session:
                repo = MemoryRepository(session)
                if results:
                    repo.upsert_news_items(results, source="news_aggregator")
                repo.upsert_news_provider_health(self.provider_health)
        except Exception:
            return

    def _persist_context_graph(self, results: list[dict[str, Any]]) -> None:
        if not self.persist_postgres or not results:
            return
        graph = None
        try:
            from context_graph.repository import ContextGraphRepository

            graph = ContextGraphRepository()
            graph.upsert_news_items(results, source="news_aggregator")
        except Exception:
            return
        finally:
            if graph is not None:
                graph.close()

    def _universe(self) -> list[dict[str, str]]:
        if self._universe_entries is None:
            try:
                self._universe_entries = Nifty200Loader().load_entries()
            except Exception:
                self._universe_entries = []
        return self._universe_entries

    def _record_provider(
        self,
        provider: str,
        started_at: float,
        *,
        items_seen: int = 0,
        items_emitted: int = 0,
        error: Exception | str | None = None,
    ) -> None:
        health = self.provider_health.setdefault(
            provider,
            {
                "provider": provider,
                "enabled": True,
                "last_success_at_ist": None,
                "last_failure_at_ist": None,
                "last_error": None,
                "items_seen": 0,
                "items_emitted": 0,
                "dedupe_drops": 0,
                "empty_extractions": 0,
                "latency_ms": 0,
            },
        )
        now = self._now_ist().isoformat()
        if error is None:
            health["last_success_at_ist"] = now
            health["last_error"] = None
        else:
            health["last_failure_at_ist"] = now
            health["last_error"] = str(error)
        health["items_seen"] = int(health.get("items_seen") or 0) + items_seen
        health["items_emitted"] = int(health.get("items_emitted") or 0) + items_emitted
        if items_seen > 0 and items_emitted == 0:
            health["empty_extractions"] = int(health.get("empty_extractions") or 0) + 1
        health["latency_ms"] = int((time.monotonic() - started_at) * 1000)

    @staticmethod
    def _raw_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _as_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _build_news_item(
        self,
        *,
        provider: str,
        source_type: str,
        title: str,
        url: str,
        content: str | None = None,
        summary: str | None = None,
        published_at: Any = None,
        source_id: str | None = None,
        content_markdown: str | None = None,
        confidence: float | None = None,
        tickers: list[str] | None = None,
        isins: list[str] | None = None,
        company_names: list[str] | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        published = self._parse_published_at(published_at)
        published_utc = published.isoformat() if published else None
        published_ist = published.astimezone(IST_ZONE).isoformat() if published else None
        source_url = url.strip()
        text = content or summary
        inferred_category = category or infer_category(title, summary, content)
        explicit_tickers = sorted({str(ticker).upper() for ticker in (tickers or []) if ticker})
        company_list = [name for name in (company_names or []) if name]
        extracted_tickers = extract_tickers_from_text(
            f"{title} {summary or ''} {content or ''} {' '.join(company_list)}",
            self._universe(),
        )
        structured_source = source_type in {"official_filing", "regulator", "broker_api"}
        verified_tickers = explicit_tickers or (extracted_tickers if structured_source else [])
        mentioned_tickers = sorted(
            {
                str(ticker).upper()
                for ticker in [*extracted_tickers, *explicit_tickers]
                if ticker and str(ticker).upper() not in verified_tickers
            }
        )
        all_tickers = sorted({*verified_tickers, *mentioned_tickers})
        mapping_reason = (
            "provider_verified_ticker"
            if explicit_tickers
            else "structured_company_match"
            if verified_tickers
            else "text_mention"
            if mentioned_tickers
            else "none"
        )
        item = {
            "provider": provider,
            "source": provider,
            "source_type": source_type,
            "source_id": source_id or source_url or title,
            "source_url": source_url,
            "canonical_url": source_url,
            "title": title.strip(),
            "summary": (summary or content or "").strip() or None,
            "content": text,
            "content_text": text,
            "content_markdown": content_markdown,
            "published_at": published_at,
            "published_at_utc": published_utc,
            "published_at_ist": published_ist,
            "fetched_at_ist": self._now_ist().isoformat(),
            "url": source_url,
            "domain": self.domain_for({"url": source_url}),
            "tickers": all_tickers,
            "verified_tickers": verified_tickers,
            "mentioned_tickers": mentioned_tickers,
            "ticker_match_type": "verified" if verified_tickers else "mentioned",
            "mapping_reason": mapping_reason,
            "mapping_confidence": confidence
            if confidence is not None
            else SOURCE_TYPE_CONFIDENCE.get(source_type, 0.6),
            "isins": sorted({str(isin).upper() for isin in (isins or []) if isin}),
            "company_names": company_list,
            "category": inferred_category,
            "confidence": (
                confidence
                if confidence is not None
                else SOURCE_TYPE_CONFIDENCE.get(source_type, 0.6)
            ),
        }
        item["raw_hash"] = self._raw_hash(item)
        return item

    @staticmethod
    def _item_text(item: dict[str, Any]) -> str:
        return " ".join(
            str(item.get(field) or "")
            for field in ("title", "summary", "content", "content_text", "content_markdown")
        )

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        terms = []
        for token in re.findall(r"[A-Za-z0-9]+", query.lower()):
            if len(token) < 3 or token in GENERIC_NEWS_TERMS:
                continue
            terms.append(token)
        return terms

    def _matches_query(self, query: str, item: dict[str, Any]) -> bool:
        terms = self._query_terms(query)
        if not terms:
            return True
        text = self._item_text(item).lower()
        return any(term in text for term in terms)

    @staticmethod
    def _normalize_match_text(value: Any) -> str:
        return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()

    def _company_name_for(self, ticker: str) -> str | None:
        try:
            name = Nifty200Loader().name_for(ticker.upper())
        except Exception:
            return None
        return name if name and name.upper() != ticker.upper() else None

    def _stock_aliases(self, ticker: str, company_name: str | None = None) -> list[str]:
        ticker = ticker.upper().strip()
        aliases = {ticker}
        company = self._normalize_match_text(company_name or self._company_name_for(ticker) or "")
        words = [
            word
            for word in company.split()
            if word
            not in {
                "LTD",
                "LIMITED",
                "CO",
                "COMPANY",
                "CORP",
                "CORPORATION",
                "PVT",
                "PRIVATE",
            }
        ]
        if words:
            aliases.add(" ".join(words))
        if len(words) >= 2:
            aliases.add(" ".join(words[:2]))
        if len(words) <= 2 and words and len(words[0]) >= 4:
            aliases.add(words[0])
        return sorted(alias for alias in aliases if len(alias) >= 2)

    def _item_mentions_stock(
        self,
        ticker: str,
        item: dict[str, Any],
        *,
        company_name: str | None = None,
    ) -> bool:
        ticker = ticker.upper().strip()
        item_tickers = item.get("tickers") or []
        if isinstance(item_tickers, str):
            item_tickers = [item_tickers]
        for value in [*item_tickers, item.get("ticker"), item.get("symbol")]:
            if str(value or "").upper().strip() == ticker:
                return True

        company_names = item.get("company_names") or []
        if isinstance(company_names, str):
            company_names = [company_names]
        text = self._normalize_match_text(
            " ".join(
                [
                    self._item_text(item),
                    str(item.get("url") or ""),
                    str(item.get("canonical_url") or ""),
                    str(item.get("source_id") or ""),
                    " ".join(str(name) for name in company_names),
                ]
            )
        )
        if not text:
            return False
        for alias in self._stock_aliases(ticker, company_name):
            normalized_alias = self._normalize_match_text(alias)
            if not normalized_alias:
                continue
            if re.search(rf"(?<![A-Z0-9]){re.escape(normalized_alias)}(?![A-Z0-9])", text):
                return True
        return False

    def _filter_stock_relevant_results(
        self,
        ticker: str,
        results: list[dict[str, Any]],
        *,
        company_name: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            item
            for item in results
            if isinstance(item, dict)
            and self._item_mentions_stock(ticker, item, company_name=company_name)
        ]

    def _filter_stock_payload(
        self,
        ticker: str,
        payload: dict[str, Any] | None,
        *,
        company_name: str | None = None,
    ) -> dict[str, Any] | None:
        if not payload or not payload.get("results"):
            return None
        filtered = self._filter_stock_relevant_results(
            ticker,
            list(payload.get("results", [])),
            company_name=company_name,
        )
        if not filtered:
            return None
        kept = dict(payload)
        kept["results"] = filtered
        return kept

    @staticmethod
    def _result_key(item: dict[str, Any]) -> str:
        url = str(item.get("canonical_url") or item.get("url") or "").strip().lower()
        title = re.sub(r"\s+", " ", str(item.get("title") or "").strip().lower())
        return url or title

    def _dedupe_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped = []
        seen = set()
        drops = 0
        for item in results:
            key = self._result_key(item)
            if not key:
                continue
            if key in seen:
                drops += 1
                continue
            seen.add(key)
            deduped.append(item)
        if drops:
            self.provider_health.setdefault(
                "dedupe",
                {
                    "provider": "dedupe",
                    "enabled": True,
                    "last_success_at_ist": self._now_ist().isoformat(),
                    "last_failure_at_ist": None,
                    "last_error": None,
                    "items_seen": 0,
                    "items_emitted": 0,
                    "dedupe_drops": 0,
                    "empty_extractions": 0,
                    "latency_ms": 0,
                },
            )["dedupe_drops"] = drops
        return deduped

    def _merge_payloads(
        self,
        query: str,
        payloads: list[dict[str, Any]],
        *,
        max_results: int,
    ) -> dict[str, Any]:
        sources = []
        results = []
        for payload in payloads:
            if not payload or not payload.get("results"):
                continue
            source = str(payload.get("source") or "")
            if source:
                sources.append(source)
            results.extend(payload.get("results", []))

        deduped = self._dedupe_results(results)[:max_results]
        self._persist_results(deduped)
        source = (
            sources[0]
            if len(sources) == 1
            else ("multi_source" if sources else "not_configured")
        )
        return {
            "query": query,
            "results": deduped,
            "source": source,
            "sources": sources,
            "provider_health": self.provider_health,
        }

    @staticmethod
    def _slugify(value: str) -> str:
        text = value.lower()
        text = re.sub(r"\b(ltd|limited|india|nse|bse)\b", " ", text)
        text = re.sub(r"[^a-z0-9]+", "-", text)
        return text.strip("-")

    def _load_cache(self) -> dict[str, Any]:
        if not self.persist_files:
            return dict(self._memory_cache)
        try:
            payload = read_json(self.cache_path, {})
        except (OSError, TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_cache(self, payload: dict[str, Any]) -> None:
        if not self.persist_files:
            self._memory_cache = dict(payload)
            return
        write_json(self.cache_path, payload)

    def _cached(self, query: str) -> dict[str, Any] | None:
        cache = self._load_cache()
        item = cache.get(query)
        if not item:
            return None
        fetched_at = item.get("fetched_at")
        if not fetched_at:
            return None
        try:
            age = utc_now() - parse_datetime_utc(fetched_at)
        except ValueError:
            return None
        if age > timedelta(minutes=self.ttl_minutes):
            return None
        return item.get("payload")

    def _store(self, query: str, payload: dict[str, Any]) -> dict[str, Any]:
        cache = self._load_cache()
        cache[query] = {"fetched_at": utc_now().isoformat(), "payload": payload}
        self._write_cache(cache)
        return payload

    @staticmethod
    def _request_url(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> requests.Response:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response

    @staticmethod
    def _strip_html(html: str) -> str:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg"]):
                tag.decompose()
            return re.sub(r"\s+", " ", soup.get_text(" ")).strip()
        except Exception:
            text = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _html_title(html: str) -> str | None:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        return re.sub(r"\s+", " ", match.group(1)).strip()
    @staticmethod
    def domain_for(item: dict[str, Any]) -> str:
        url = str(item.get("url") or "")
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host

    @staticmethod
    def _parse_published_at(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, (int, float)):
            raw = float(value)
            if raw > 10_000_000_000:
                raw = raw / 1000
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
            for fmt in (
                "%d-%b-%Y %H:%M:%S",
                "%d-%b-%Y %H:%M",
                "%d %b %Y %H:%M:%S",
                "%d %b %Y %H:%M",
            ):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if parsed is None:
                try:
                    from email.utils import parsedate_to_datetime

                    parsed = parsedate_to_datetime(text)
                except (TypeError, ValueError):
                    return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=IST_ZONE).astimezone(timezone.utc)
        return parsed.astimezone(timezone.utc)

    def normalize_headlines(
        self,
        headlines: list[dict[str, Any]],
        *,
        max_age_hours: int | None = None,
        excluded_domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        max_age = max_age_hours or int(cfg.research.filter.news_max_age_hours)
        excluded = {
            domain.lower()
            for domain in (excluded_domains or cfg.research.filter.excluded_news_domains)
        }
        now = datetime.now(timezone.utc)
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in headlines:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title and not url:
                continue
            domain = self.domain_for(item)
            if domain and domain in excluded:
                continue
            published = self._parse_published_at(item.get("published_at"))
            if published is not None and now - published > timedelta(hours=max_age):
                continue
            key = (url or title).lower()
            if key in seen:
                continue
            seen.add(key)
            preserved = dict(item)
            preserved.update(
                {
                    "title": title or url,
                    "url": url,
                    "content": item.get("content") or item.get("content_text"),
                    "content_text": item.get("content_text") or item.get("content"),
                    "score": item.get("score"),
                    "published_at": item.get("published_at"),
                    "domain": domain,
                }
            )
            normalized.append(preserved)
        return normalized

    @staticmethod
    def _article_identity(ticker: str, item: dict[str, Any]) -> str:
        basis = f"{ticker.upper()}:{item.get('url') or item.get('title') or ''}".lower()
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _market_article_identity(item: dict[str, Any]) -> str:
        basis = f"MARKET_DIGEST:{item.get('url') or item.get('title') or ''}".lower()
        return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]

    def _item_detected_tickers(self, item: dict[str, Any]) -> list[str]:
        tickers = item.get("tickers") or []
        if isinstance(tickers, str):
            tickers = [tickers]
        normalized = {str(ticker).upper().strip() for ticker in tickers if ticker}
        if not normalized:
            detected = extract_tickers_from_text(
                " ".join(
                    [
                        self._item_text(item),
                        str(item.get("url") or ""),
                        str(item.get("company_names") or ""),
                    ]
                ),
                self._universe(),
            )
            normalized.update(detected)
        return sorted(ticker for ticker in normalized if ticker)

    def _unseen_market_digest_items(
        self,
        headlines: list[dict[str, Any]],
        *,
        cooldown_hours: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, str], datetime]:
        cooldown = cooldown_hours or int(cfg.research.filter.news_alert_cooldown_hours)
        now = utc_now()
        if self.persist_files:
            try:
                history = read_json(self.alert_history_path, {})
            except (OSError, TypeError, ValueError):
                history = {}
        else:
            history = dict(self._alert_history)
        if not isinstance(history, dict):
            history = {}
        cutoff = now - timedelta(hours=cooldown)
        pruned: dict[str, str] = {}
        for key, value in history.items():
            try:
                seen_at = parse_datetime_utc(value)
            except ValueError:
                continue
            if seen_at >= cutoff:
                pruned[key] = seen_at.isoformat()

        return (
            [item for item in headlines if self._market_article_identity(item) not in pruned],
            pruned,
            now,
        )

    def _store_market_digest_alerts(
        self,
        items: list[dict[str, Any]],
        history: dict[str, str],
        seen_at: datetime,
    ) -> None:
        updated = dict(history)
        for item in items:
            updated[self._market_article_identity(item)] = seen_at.isoformat()
        if not self.persist_files:
            self._alert_history = updated
            return
        write_json(self.alert_history_path, updated)

    def build_market_digest(
        self,
        payload: dict[str, Any],
        *,
        max_items: int | None = None,
        max_ticker_groups: int | None = None,
        max_per_ticker: int | None = None,
        max_general: int | None = None,
        cooldown_hours: int | None = None,
    ) -> dict[str, Any]:
        filter_cfg = cfg.research.filter
        max_items = (
            int(filter_cfg.market_news_digest_max_items) if max_items is None else max_items
        )
        max_ticker_groups = (
            int(filter_cfg.market_news_digest_max_ticker_groups)
            if max_ticker_groups is None
            else max_ticker_groups
        )
        max_per_ticker = (
            int(filter_cfg.market_news_digest_max_items_per_ticker)
            if max_per_ticker is None
            else max_per_ticker
        )
        max_general = (
            int(filter_cfg.market_news_digest_max_general_items)
            if max_general is None
            else max_general
        )
        normalized = self.normalize_headlines(list(payload.get("results", [])))
        fresh_items, alert_history, seen_at = self._unseen_market_digest_items(
            normalized,
            cooldown_hours=cooldown_hours,
        )
        entries_by_ticker = {entry["ticker"]: entry for entry in self._universe()}
        grouped: dict[str, list[dict[str, Any]]] = {}
        general: list[dict[str, Any]] = []

        for item in fresh_items[:max_items]:
            detected = self._item_detected_tickers(item)
            preserved = dict(item)
            preserved["tickers"] = detected
            if not detected:
                general.append(preserved)
                continue
            for ticker in detected:
                grouped.setdefault(ticker, [])
                if len(grouped[ticker]) < max_per_ticker:
                    grouped[ticker].append(preserved)

        ticker_groups = []
        for ticker, items in sorted(grouped.items()):
            if not items:
                continue
            ticker_groups.append(
                {
                    "ticker": ticker,
                    "company_name": entries_by_ticker.get(ticker, {}).get("name", ticker),
                    "items": items,
                }
            )
            if len(ticker_groups) >= max_ticker_groups:
                break

        general = general[:max_general]
        displayed_items = [
            item for group in ticker_groups for item in group["items"]
        ] + general
        self._store_market_digest_alerts(displayed_items, alert_history, seen_at)
        return {
            "query": payload.get("query"),
            "source": payload.get("source"),
            "sources": payload.get("sources", []),
            "ticker_groups": ticker_groups,
            "general": general,
            "item_count": len(displayed_items),
            "generated_at_ist": self._now_ist().isoformat(),
        }

    def filter_new_alerts(
        self,
        ticker: str,
        headlines: list[dict[str, Any]],
        *,
        cooldown_hours: int | None = None,
        company_name: str | None = None,
    ) -> list[dict[str, Any]]:
        cooldown = cooldown_hours or int(cfg.research.filter.news_alert_cooldown_hours)
        now = utc_now()
        if self.persist_files:
            try:
                history = read_json(self.alert_history_path, {})
            except (OSError, TypeError, ValueError):
                history = {}
        else:
            history = dict(self._alert_history)
        if not isinstance(history, dict):
            history = {}
        cutoff = now - timedelta(hours=cooldown)
        pruned: dict[str, str] = {}
        for key, value in history.items():
            try:
                seen_at = parse_datetime_utc(value)
            except ValueError:
                continue
            if seen_at >= cutoff:
                pruned[key] = seen_at.isoformat()

        new_items: list[dict[str, Any]] = []
        for item in self._filter_stock_relevant_results(
            ticker,
            headlines,
            company_name=company_name,
        ):
            identity = self._article_identity(ticker, item)
            if identity in pruned:
                continue
            pruned[identity] = now.isoformat()
            new_items.append(item)
        if not self.persist_files:
            self._alert_history = pruned
            return new_items
        write_json(self.alert_history_path, pruned)
        return new_items

    @staticmethod
    def build_stock_news_query(ticker: str, company_name: str | None = None) -> str:
        company = (company_name or ticker).strip()
        if company.upper() == ticker.upper():
            company = f"{ticker} NSE"
        return f"{company} {ticker} stock news India last 24 hours"
