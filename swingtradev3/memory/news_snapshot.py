"""Explicit source snapshot writes and bounded, side-effect-free evidence reads.

The caller owns transactions and must supply the actual observation time. Legacy
news articles are deliberately not backfilled: their historical availability is unknown.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from memory.models import NewsSourceFetchRow, NewsSourceObservationRow, NewsSourceVersionRow

UTC = timezone.utc


def _utc(value: datetime | str) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("a timezone-aware datetime is required")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("an explicit timezone is required")
    return value.astimezone(UTC)


def _stored_utc(value: datetime) -> datetime:
    # SQLite drops offsets for timezone-aware columns; these columns store UTC only.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def _version_content(payload: dict[str, Any]) -> dict[str, Any]:
    # These hashes describe raw fetch bytes, which can contain non-content noise.
    # Retain the initial raw values as provenance, but do not make revisions for them.
    return {k: v for k, v in payload.items() if k not in {"source_hash", "provider_content_hash"}}


class NewsSnapshotRepository:
    def __init__(self, session: Session):
        self.session = session

    def record(self, item: dict[str, Any], *, fetched_at: datetime | str) -> str:
        """Save one observed immutable version, returning its namespaced version ID."""
        seen = _utc(fetched_at)
        provider = str(item.get("provider") or "").strip()
        entry_id = str(item.get("provider_entry_id") or item.get("source_id") or "").strip()
        if not provider or not entry_id:
            raise ValueError("provider and provider entry ID are required")
        source_key = _hash([provider, entry_id])
        # The adapter supplies JSON data; observation-specific values never define a revision.
        payload = {k: v for k, v in item.items() if k not in {"fetched_at_utc", "fetched_at"}}
        payload.update(provider=provider, raw_provider_entry_id=item.get("provider_entry_id"),
                       resolved_entry_id=entry_id, source_key=source_key,
                       source_identity_basis=("provider_entry_id" if item.get("provider_entry_id")
                           else "canonical_url_fallback" if entry_id == item.get("canonical_url")
                           else "source_id_fallback"))
        payload.setdefault("identity_basis", "unmapped")
        payload.setdefault("issuer_identifiers", [])
        payload.setdefault("publication_precision", "unknown")
        payload["provider_content_hash"] = item.get("content_hash")
        payload["content_hash"] = _hash([payload.get("title"), payload.get("summary"),
                                         payload.get("content")])
        # Only identical URLs are grouped; a group is not proof of corroboration.
        if payload.get("canonical_url"):
            payload["duplicate_group"] = _hash(str(payload["canonical_url"]))
        version_id = _hash([source_key, _version_content(payload)])
        latest = self.session.scalars(select(NewsSourceObservationRow).where(
            NewsSourceObservationRow.source_key == source_key).order_by(
                NewsSourceObservationRow.fetched_at.desc()).limit(1)).first()
        if latest is not None and seen < _stored_utc(latest.fetched_at):
            raise ValueError("observation time predates a saved observation")
        # Versions created with the earlier hash algorithm retain their IDs.
        # Compare their content before deciding that an unchanged fetch is new.
        current = self.session.get(NewsSourceVersionRow, latest.version_id) if latest else None
        unchanged = current is not None and _version_content(current.payload) == _version_content(payload)
        if (latest is not None and seen == _stored_utc(latest.fetched_at)
                and not unchanged):
            raise ValueError("different versions cannot share an observation time")
        if unchanged:
            return latest.version_id
        version = self.session.get(NewsSourceVersionRow, version_id)
        if version is None:
            version = NewsSourceVersionRow(version_id=version_id, source_key=source_key,
                                           provider=provider, first_seen_at=seen, payload=payload)
            self.session.add(version)
        self.session.add(NewsSourceObservationRow(observation_id=uuid4().hex, source_key=source_key,
            version_id=version_id, supersedes_version_id=latest.version_id if latest else None,
            fetched_at=seen))
        self.session.flush()
        return version_id

    def record_fetch(self, provider: str, *, fetched_at: datetime | str,
                     status: str, details: dict[str, Any] | None = None) -> str:
        if not provider.strip() or not status.strip():
            raise ValueError("provider and status are required")
        fetch_id = uuid4().hex
        self.session.add(NewsSourceFetchRow(fetch_id=fetch_id, provider=provider,
                         fetched_at=_utc(fetched_at), payload={**(details or {}), "status": status}))
        self.session.flush()
        return fetch_id

    def status(self, *, cutoff: datetime | str, providers: list[str]) -> dict[str, Any]:
        if not providers or len(providers) > 20:
            raise ValueError("one to twenty providers are required")
        cutoff = _utc(cutoff)
        coverage: dict[str, Any] = {}
        for provider in providers:
            fetch = self.session.scalars(select(NewsSourceFetchRow).where(
                NewsSourceFetchRow.provider == provider, NewsSourceFetchRow.fetched_at <= cutoff
            ).order_by(NewsSourceFetchRow.fetched_at.desc(),
                       NewsSourceFetchRow.fetch_id.desc()).limit(1)).first()
            coverage[provider] = ({**fetch.payload,
                "fetched_at": _stored_utc(fetch.fetched_at).isoformat()} if fetch
                else {"status": "unknown"})
        return coverage

    def read(self, version_id: str, *, cutoff: datetime | str) -> dict[str, Any] | None:
        """Read a version only when it had actually been observed by the cutoff."""
        cutoff = _utc(cutoff)
        row = self.session.get(NewsSourceVersionRow, version_id)
        if row is None or _stored_utc(row.first_seen_at) > cutoff:
            return None
        observation = self.session.scalars(select(NewsSourceObservationRow).where(
            NewsSourceObservationRow.version_id == version_id,
            NewsSourceObservationRow.fetched_at <= cutoff).order_by(
                NewsSourceObservationRow.fetched_at.desc()).limit(1)).first()
        result = self._serialize(row, observation)
        latest = self.session.scalars(select(NewsSourceObservationRow).where(
            NewsSourceObservationRow.source_key == row.source_key,
            NewsSourceObservationRow.fetched_at <= cutoff).order_by(
                NewsSourceObservationRow.fetched_at.desc()).limit(1)).first()
        result["version_status"] = "current" if latest.version_id == version_id else "superseded"
        result["current_version_id"] = latest.version_id
        return result

    def _serialize(self, row: NewsSourceVersionRow,
                   observation: NewsSourceObservationRow) -> dict[str, Any]:
        source_first = self.session.scalar(select(func.min(NewsSourceObservationRow.fetched_at)).where(
            NewsSourceObservationRow.source_key == row.source_key))
        return {**row.payload, "version_id": row.version_id,
                "version_first_seen_at": _stored_utc(row.first_seen_at).isoformat(),
                "first_seen_at": _stored_utc(source_first).isoformat(),
                "fetched_at": _stored_utc(observation.fetched_at).isoformat(),
                "fetched_at_basis": "version_transition_observation",
                "supersedes_version_id": observation.supersedes_version_id}

    def search(self, *, cutoff: datetime | str, start: datetime | str, end: datetime | str,
               providers: list[str], topic: str = "", limit: int = 20,
               include_unknown: bool = False,
               version_ids: list[str] | None = None) -> dict[str, Any]:
        """Find latest observed revisions in a publication window, with disclosed gaps.

        Date-only publications are included only after the entire declared local date
        has elapsed. Unknown publication dates cannot be placed in a time window.
        Text matching is retrieval only; it does not establish issuer identity.
        """
        cutoff, start, end = _utc(cutoff), _utc(start), _utc(end)
        if (start >= end or not providers or len(providers) > 20 or len(topic) > 200
                or (version_ids is not None and len(version_ids) > 500)):
            raise ValueError("invalid window, providers or topic")
        limit = max(1, min(int(limit), 50))
        ranked = select(NewsSourceObservationRow.observation_id,
                        func.row_number().over(partition_by=NewsSourceObservationRow.source_key,
                            order_by=(NewsSourceObservationRow.fetched_at.desc(),
                                      NewsSourceObservationRow.observation_id.desc())).label("rank"))\
            .where(NewsSourceObservationRow.fetched_at <= cutoff).subquery()
        query = select(NewsSourceVersionRow, NewsSourceObservationRow).join(
            NewsSourceObservationRow, NewsSourceObservationRow.version_id == NewsSourceVersionRow.version_id).join(
            ranked, ranked.c.observation_id == NewsSourceObservationRow.observation_id).where(
                ranked.c.rank == 1, NewsSourceVersionRow.provider.in_(providers))
        # Apply the allowlist after ranking observations, so an older allowed
        # revision cannot stand in for a newer version at the requested cutoff.
        if version_ids is not None:
            query = query.where(NewsSourceVersionRow.version_id.in_(version_ids))
        rows = self.session.execute(query.order_by(
                    NewsSourceVersionRow.first_seen_at.desc(), NewsSourceVersionRow.version_id
                ).limit(1001)).all()
        truncated = len(rows) > 1000
        matches, undated, unknown, undated_matches = [], [], 0, 0
        for row, observation in rows[:1000]:
            payload = row.payload
            interval = _publication_interval(payload)
            if interval is None:
                unknown += 1
                if (include_unknown and (not topic or topic.casefold() in
                        (str(payload.get("title") or "") + " " +
                         str(payload.get("summary") or "")).casefold())):
                    undated_matches += 1
                    if len(undated) < 6:
                        undated.append({**self._serialize(row, observation),
                                        "temporal_membership": "unknown"})
                continue
            earliest, latest = interval
            if earliest < start or latest > end or latest > cutoff:
                continue
            if topic and topic.casefold() not in (str(payload.get("title") or "") + " " +
                    str(payload.get("summary") or "")).casefold():
                continue
            matches.append(self._serialize(row, observation))
        # Coverage is an observation, never an assertion that the source is complete.
        return {"items": matches[:limit], "undated_items": undated,
                "undated_truncated": undated_matches > len(undated) or (include_unknown and truncated),
                "coverage": self.status(cutoff=cutoff, providers=providers),
                "unknown_publication_dates": unknown,
                "truncated": truncated or len(matches) > limit,
                "historical_availability": "observed_versions_only"}


def _publication_interval(payload: dict[str, Any]) -> tuple[datetime, datetime] | None:
    precision = payload.get("publication_precision")
    try:
        if precision == "date":
            basis = str(payload["timezone_basis"])
            offset = re.fullmatch(r"source offset ([+-])(\d{2}):?(\d{2})", basis)
            if offset:
                hours, minutes = int(offset[2]), int(offset[3])
                if hours > 23 or minutes > 59:
                    return None
                delta = timedelta(hours=hours, minutes=minutes)
                zone = timezone(delta if offset[1] == "+" else -delta)
            else:
                zone = ZoneInfo(basis)
            day = date.fromisoformat(str(payload["published_date"]))
            start = datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)
            end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
            return start, end
        if precision in {"second", "minute", "timestamp"}:
            instant = _utc(payload["published_at_utc"])
            return instant, instant + (timedelta(minutes=1) if precision == "minute"
                                       else timedelta(seconds=1) if precision == "second"
                                       else timedelta())
    except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError):
        pass
    return None
