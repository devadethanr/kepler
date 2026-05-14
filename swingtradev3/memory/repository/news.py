"""NewsArticle and NewsProviderHealth sub-repository."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


class NewsRepository:
    """News articles and provider health."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_news_items(self, items: Iterable[dict[str, Any]], *, source: str) -> None:
        for item in items:
            self.upsert_news_item(dict(item), source=source)

    def upsert_news_item(self, item: dict[str, Any], *, source: str = "news_aggregator") -> None:
        source_id = str(
            item.get("source_id")
            or item.get("canonical_url")
            or item.get("url")
            or item.get("raw_hash")
            or item.get("title")
            or ""
        )
        if not source_id:
            return
        news_id = source_id if len(source_id) <= 120 else hashlib.sha256(
            source_id.encode("utf-8")
        ).hexdigest()
        tickers = [str(t).upper() for t in item.get("tickers", [])]
        verified_tickers = [str(t).upper() for t in item.get("verified_tickers", [])]
        mentioned_tickers = [str(t).upper() for t in item.get("mentioned_tickers", [])]
        payload = {
            "news_id": news_id,
            "provider": str(item.get("provider") or item.get("source") or "unknown"),
            "source_type": str(item.get("source_type") or "unknown"),
            "category": str(item.get("category") or "unknown"),
            "title": str(item.get("title") or ""),
            "summary": str(item.get("summary") or item.get("description") or ""),
            "url": str(item.get("canonical_url") or item.get("url") or ""),
            "canonical_url": str(item.get("canonical_url") or item.get("url") or ""),
            "tickers": tickers,
            "verified_tickers": verified_tickers,
            "mentioned_tickers": mentioned_tickers,
            "mapping_reason": str(item.get("mapping_reason") or ""),
            "mapping_confidence": item.get("mapping_confidence") or item.get("confidence"),
            "published_at_ist": item.get("published_at_ist"),
            "published_at_utc": item.get("published_at_utc"),
            "fetched_at_ist": item.get("fetched_at_ist"),
        }

        row = self.session.get(models_module.NewsArticleRow, news_id)
        if row is None:
            row = models_module.NewsArticleRow(news_id=news_id)
            self.session.add(row)

        row.provider = payload["provider"]
        row.source_type = payload["source_type"]
        row.title = str(item.get("title") or "")
        row.canonical_url = payload["url"]
        row.published_at = _parse_datetime(
            item.get("published_at_utc")
            or item.get("published_at")
            or item.get("published_at_ist")
        )
        row.category = payload["category"]
        try:
            row.confidence = float(item.get("confidence") or 0.0)
        except (TypeError, ValueError):
            row.confidence = 0.0
        row.tickers = verified_tickers or tickers
        row.payload = {**dict(item), **payload}
        row.updated_at = datetime.now(ZoneInfo("Asia/Kolkata"))

        EventRepository(self.session).append_execution_event(
            event_type="news_item_ingested",
            entity_type="news_article",
            entity_id=news_id,
            source=source,
            payload=payload,
        )

    def list_news_items(
        self,
        *,
        limit: int = 100,
        ticker: str | None = None,
    ) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 500))
        query = select(models_module.NewsArticleRow)
        if ticker:
            ticker_upper = ticker.upper()
            query = query.where(models_module.NewsArticleRow.tickers.contains([ticker_upper]))
        rows = self.session.scalars(
            query.order_by(
                models_module.NewsArticleRow.updated_at.desc(),
                models_module.NewsArticleRow.published_at.desc().nullslast(),
            ).limit(bounded_limit)
        ).all()
        return [
            {
                **dict(row.payload or {}),
                "news_id": row.news_id,
                "provider": row.provider,
                "source_type": row.source_type,
                "title": row.title,
                "canonical_url": row.canonical_url,
                "category": row.category,
                "confidence": row.confidence,
                "tickers": list(row.tickers or []),
                "verified_tickers": list((row.payload or {}).get("verified_tickers") or []),
                "mentioned_tickers": list((row.payload or {}).get("mentioned_tickers") or []),
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]

    def upsert_news_provider_health(self, health: dict[str, dict[str, Any]]) -> None:
        for provider, payload in health.items():
            row = self.session.get(models_module.NewsProviderHealthRow, provider)
            if row is None:
                row = models_module.NewsProviderHealthRow(provider=provider)
                self.session.add(row)
            status = "healthy" if payload.get("last_error") in (None, "") else "degraded"
            row.enabled = bool(payload.get("enabled", True))
            row.status = status
            row.items_seen = int(payload.get("items_seen") or 0)
            row.items_emitted = int(payload.get("items_emitted") or 0)
            row.last_success_at = _parse_datetime(payload.get("last_success_at_ist"))
            row.last_failure_at = _parse_datetime(payload.get("last_failure_at_ist"))
            row.payload = dict(payload or {})

    def list_news_provider_health(self) -> dict[str, dict[str, Any]]:
        rows = self.session.scalars(select(models_module.NewsProviderHealthRow)).all()
        return {
            row.provider: {
                **dict(row.payload or {}),
                "provider": row.provider,
                "enabled": row.enabled,
                "status": row.status,
                "items_seen": row.items_seen,
                "items_emitted": row.items_emitted,
                "last_success_at_ist": (
                    _as_ist(row.last_success_at).isoformat() if row.last_success_at else None
                ),
                "last_failure_at_ist": (
                    _as_ist(row.last_failure_at).isoformat() if row.last_failure_at else None
                ),
            }
            for row in rows
        }


def _parse_datetime(value: Any) -> datetime | None:
    IST = ZoneInfo("Asia/Kolkata")
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=IST)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=IST)


def _as_ist(value: datetime) -> datetime:
    IST = ZoneInfo("Asia/Kolkata")
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)
