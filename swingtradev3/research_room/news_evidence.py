"""Bounded reads over the existing news store's immutable source revisions.

No ingestion, network, migration, graph write, or aggregator import occurs here.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from data.news.fresh_source import SOURCES
from memory.db import get_session_factory
from memory.news_snapshot import NewsSnapshotRepository, _utc

from .grounding import packet

READABLE_SOURCES = {**SOURCES, "pib_html": ("https://www.pib.gov.in/", "government_release")}


@contextmanager
def read_scope():
    with get_session_factory()() as session:
        if session.bind.dialect.name == "postgresql":
            session.execute(text("SET TRANSACTION READ ONLY"))
        yield session


def _offset(value, maximum):
    value = value or "0"
    if not value.isascii() or not value.isdigit() or int(value) > maximum:
        raise ValueError("Invalid bounded source offset")
    return int(value)


class NewsEvidence:
    def __init__(self, room, scope=read_scope, *, stale_after_seconds=86400):
        self.room, self.scope = room, scope
        self.options = room.get("evidence_scope") or {}
        # The room pins availability at creation, not at a later tool invocation.
        pinned = self.options.get("cutoff") or room.get("source_cutoff")
        if not pinned:
            raise ValueError("Legacy room lacks a pinned source cutoff; start a linked new room")
        self.cutoff = _utc(pinned)
        self.stale_after_seconds = stale_after_seconds

    def search(self, args):
        cutoff = _utc(args["cutoff"]) if args["cutoff"] else self.cutoff
        if cutoff > self.cutoff:
            raise ValueError("Cutoff is later than the room's pinned source snapshot")
        start = _utc(args["start"]) if args["start"] else cutoff - timedelta(days=30)
        end = _utc(args["end"]) if args["end"] else cutoff
        if start >= end or end > cutoff or end - start > timedelta(days=366):
            raise ValueError("Source window must be <=366 days and no later than cutoff")
        providers = [p.strip() for p in args["sources"].split(",") if p.strip()] or list(
            READABLE_SOURCES
        )
        if set(providers) - set(READABLE_SOURCES) or len(providers) > len(READABLE_SOURCES):
            raise ValueError("Unknown source ID; use the configured primary-source set")
        topic = args["topic"].strip()
        if len(topic) > 160:
            raise ValueError("Source query exceeds 160 characters")
        offset = _offset(args["offset"], 48)
        with self.scope() as session:
            found = NewsSnapshotRepository(session).search(
                cutoff=cutoff,
                start=start,
                end=end,
                providers=providers,
                topic=topic,
                limit=50,
                include_unknown=True,
                version_ids=self.options.get("version_ids"),
            )
        candidates = found.pop("items")
        found["coverage"] = coverage_freshness(found["coverage"], cutoff, self.stale_after_seconds)
        undated = found.pop("undated_items", [])
        allowed = self.options.get("version_ids")
        if allowed is not None:
            candidates = [item for item in candidates if item["version_id"] in allowed]
            undated = [item for item in undated if item["version_id"] in allowed]
        selected = candidates[offset : offset + 6]
        undated = undated[:2] if offset == 0 else []
        retrieval = {
            **found,
            "scope": "saved primary-source revisions; textual topic match only",
            "cutoff": cutoff.isoformat(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "query": topic,
            "sources": providers,
            "offset": offset,
            "result_limit": 6,
            "next_offset": offset + 6 if offset + 6 < len(candidates) else None,
            "candidate_cap": 50,
            "undated_returned": len(undated),
            "undated_policy": "not placed in requested publication window; membership unknown",
            "completeness": "bounded current feed windows; absence does not establish no release",
            "conflicts": "matching records retained; no semantic contradiction classifier",
            "identity_basis": "requested topic; no issuer/event mapping inferred",
        }
        return {
            "status": "ok" if selected else "partial" if undated else "empty",
            "retrieval": retrieval,
            "coverage": found["coverage"],
            "evidence": [self._packet(item, retrieval, cutoff) for item in selected + undated],
        }

    def read(self, version_id, offset="0", *, cutoff=None):
        offset = _offset(offset, 24000)
        cutoff = _utc(cutoff) if cutoff else self.cutoff
        if cutoff > self.cutoff:
            raise ValueError("Read cutoff exceeds the pinned snapshot")
        allowed = self.options.get("version_ids")
        if allowed is not None and version_id not in allowed:
            raise ValueError("Version is outside this frozen room snapshot")
        with self.scope() as session:
            item = NewsSnapshotRepository(session).read(version_id, cutoff=cutoff)
        if item is None:
            return {
                "status": "unavailable",
                "evidence": [],
                "reason": "No saved version known available by this cutoff",
            }
        retrieval = {
            "scope": "one immutable saved version",
            "offset": offset,
            "completeness": "retained source metadata/snippet only; linked attachments not fetched",
        }
        return {
            "status": "ok",
            "retrieval": retrieval,
            "evidence": [self._packet(item, retrieval, cutoff, offset)],
        }

    def _packet(self, item, retrieval, cutoff, offset=0):
        # Quotes contain only actual retained source text. Manager labels stay metadata.
        body = "\n".join(str(item.get(k) or "") for k in ("title", "summary", "content")).strip()
        excerpt = body[offset : offset + 6000]
        retrieval = {
            **retrieval,
            "offset": offset,
            "end_offset": offset + len(excerpt),
            "truncated": bool(retrieval.get("truncated")) or offset + len(excerpt) < len(body),
        }
        result = packet(
            self.room["target"],
            item["canonical_url"],
            excerpt,
            published_at=item.get("published_at_utc"),
            record_id=item["version_id"],
            event_id=item.get("event_id"),
            event_at=item.get("event_at"),
            decision_cutoff=cutoff.isoformat(),
            source_type=item.get("source_type"),
            retrieval=retrieval,
            status="ok" if excerpt else "unavailable",
        )
        snapshot = {
            **item,
            "requested_cutoff": cutoff.isoformat(),
            "availability": "observed_by_cutoff",
            "units": item.get("units"),
            "currency": item.get("currency"),
            "period": item.get("period"),
            "graph_link": {
                "node_id": "news:" + item["news_id"] if item.get("news_id") else None,
                "scope": "current projection only; source snapshot authoritative",
            },
        }
        for key in ("title", "summary", "content"):
            snapshot.pop(key, None)
        result["source_snapshot"] = snapshot
        result["entity_identity"] = item.get("identity_basis", "unmapped")
        return result


def coverage_freshness(coverage, cutoff, stale_after_seconds):
    result = {}
    for provider, value in coverage.items():
        value = dict(value)
        value.update(
            freshness="unknown",
            freshness_basis="time since last fetch; not publication",
            stale_after_seconds=stale_after_seconds,
        )
        try:
            age = (cutoff - _utc(value.get("fetched_at"))).total_seconds()
            value.update(
                fetch_age_seconds=age,
                freshness="stale" if age > stale_after_seconds else "recent_fetch",
            )
        except (ValueError, TypeError):
            pass
        result[provider] = value
    return result


def source_status(scope=read_scope, *, stale_after_seconds=86400):
    now = datetime.now(timezone.utc)
    with scope() as session:
        coverage = NewsSnapshotRepository(session).status(
            cutoff=now, providers=list(READABLE_SOURCES)
        )
    coverage = coverage_freshness(coverage, now, stale_after_seconds)
    return {
        "sources": [
            {
                "source_id": provider,
                "source_type": READABLE_SOURCES[provider][1],
                "endpoint": READABLE_SOURCES[provider][0],
                **coverage[provider],
            }
            for provider in READABLE_SOURCES
        ],
        "coverage": "Current feed windows only; company disclosure coverage unavailable",
        "as_of": now.isoformat(),
    }
