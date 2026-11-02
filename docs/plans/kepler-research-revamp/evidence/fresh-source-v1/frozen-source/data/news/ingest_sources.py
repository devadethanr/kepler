"""Explicit ingestion owner; never imported by model tools or API reads.

Run only after a backed-up, explicit schema upgrade. Existing news rows and the
execution-event projector remain the canonical current view; additive revisions
preserve availability. No paid fallback, scheduler, broker, or graph mutation here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

from sqlalchemy import text

from data.news.fresh_source import MIN_REFRESH_SECONDS, SOURCES, fetch_feed
from data.news.fresh_source_html import fetch_pib_release
from memory.db import get_session_factory
from memory.news_snapshot import NewsSnapshotRepository, _utc
from memory.models import NewsArticleRow
from memory.repository.news import NewsRepository

TERMS = {
    "sebi_rss": {
        "url": "https://www.sebi.gov.in/website-policy.html",
        "retention": "feed identification metadata and links only; no article bodies",
        "restriction": "prior permission required for reproduction of material",
    },
    "rbi_press_releases_rss": {
        "url": "https://www.rbi.org.in/Scripts/Disclaimer.aspx",
        "retention": "feed identification metadata and links only; no article bodies",
        "restriction": "body retention permission unconfirmed",
    },
    "pib_rss": {
        "url": "https://www.pib.gov.in/content/102_2_Copyright-Policy.aspx?lang=1&reg=30",
        "retention": "attributed feed metadata; reviewed first-party excerpt only on explicit request",
        "restriction": "accurate reproduction with acknowledgement; third-party material excluded",
    },
}


def ingest(providers, run_id):
    reports = []
    for provider in providers:
        if provider not in SOURCES:
            raise ValueError("Only explicitly configured primary sources are enabled")
        with get_session_factory().begin() as session:
            if session.bind.dialect.name == "postgresql":
                # Serialize owners across processes; no model or broker lock is touched.
                key = int(hashlib.sha256(provider.encode()).hexdigest()[:15], 16)
                if not session.scalar(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": key}):
                    reports.append(
                        {"provider": provider, "status": "owner_busy", "http_requests": 0}
                    )
                    continue
            repository = NewsSnapshotRepository(session)
            now = datetime.now(timezone.utc)
            previous = repository.status(cutoff=now, providers=[provider])[provider]
            if (
                previous.get("fetched_at")
                and (now - _utc(previous["fetched_at"])).total_seconds() < MIN_REFRESH_SECONDS
            ):
                reports.append({"provider": provider, "status": "rate_limited", "http_requests": 0})
                continue
            result = fetch_feed(
                provider,
                etag=previous.get("etag"),
                last_modified=previous.get("last_modified"),
                deadline=time.monotonic() + 25,
            )
            fetched = datetime.now(timezone.utc)
            items = result.pop("items")
            # Never treat a 304 as loss of previously observed coverage/counts.
            details = {
                **result,
                "entry_hashes": [
                    {"source_id": item.get("source_id"), "content_hash": item.get("content_hash")}
                    for item in items
                ],
                "run_id": run_id,
                "source_type": SOURCES[provider][1],
                "terms": TERMS[provider],
                "entry_count": len(items),
            }
            if result["status"] == "not_modified":
                details["entry_count"] = previous.get("entry_count")
                details["coverage"] = previous.get("coverage", "unknown")
            repository.record_fetch(
                provider, fetched_at=fetched, status=result["status"], details=details
            )
            versions, changed = [], 0
            for item in items:
                entry_id = item.get("provider_entry_id") or item["source_id"]
                canonical_id = (
                    "primary:" + hashlib.sha256((provider + "\0" + entry_id).encode()).hexdigest()
                )
                item = {
                    **item,
                    "news_id": canonical_id,
                    "terms": TERMS[provider],
                    "retention": "feed_metadata_only",
                    "source_owner": provider,
                    "identity_basis": "provider regulator/government origin; issuer unmapped",
                }
                # Provider timestamps never substitute for the observation clock.
                version = repository.record(item, fetched_at=fetched)
                saved = repository.read(version, cutoff=fetched)
                versions.append(version)
                current = session.get(NewsArticleRow, canonical_id)
                if current is not None and current.payload.get("source_version_id") == version:
                    continue
                NewsRepository(session).upsert_news_item(
                    {
                        **item,
                        "source_id": canonical_id,
                        "source_version_id": version,
                        "source_key": saved["source_key"],
                        "source_content_hash": saved["content_hash"],
                        "source_first_seen_at": saved["first_seen_at"],
                        "source_version_first_seen_at": saved["version_first_seen_at"],
                        "tickers": [],
                        "verified_tickers": [],
                        "mentioned_tickers": [],
                    },
                    source="primary_source_ingestion",
                )
                changed += 1
            reports.append(
                {
                    "provider": provider,
                    **details,
                    "fetched_at": fetched.isoformat(),
                    "version_ids": versions,
                    "changed": changed,
                }
            )
    return reports


def ingest_pib_release(url, run_id, *, first_party_reviewed=False):
    """Retain a reviewed, attributed excerpt; unsupported/unknown metadata stays so."""
    if not first_party_reviewed:
        raise ValueError("Selected PIB release requires explicit third-party/terms review")
    fetched = datetime.now(timezone.utc)
    # The inherited public fetch follows at most four checked requests; exact redirect
    # accounting is unavailable here. Reserve its bound, never report a measured zero.
    details = {
        "run_id": run_id,
        "http_requests": None,
        "request_bound": 4,
        "terms": TERMS["pib_rss"],
        "entry_count": 0,
        "coverage": "one reviewed HTML release; not a feed or company filing",
    }
    with get_session_factory().begin() as session:
        if session.bind.dialect.name == "postgresql" and not session.scalar(
            text("SELECT pg_try_advisory_xact_lock(2026110208)")
        ):
            return {"provider": "pib_html", "status": "owner_busy", "http_requests": 0}
        repository = NewsSnapshotRepository(session)
        previous = repository.status(cutoff=fetched, providers=["pib_html"])["pib_html"]
        if (
            previous.get("fetched_at")
            and (fetched - _utc(previous["fetched_at"])).total_seconds() < MIN_REFRESH_SECONDS
        ):
            return {"provider": "pib_html", "status": "rate_limited", "http_requests": 0}
        result = fetch_pib_release(url, deadline=time.monotonic() + 25)
        fetched = datetime.now(timezone.utc)
        details["status"] = result["status"]
        if result["status"] == "ok":
            entry_id = result["provider_entry_id"]
            news_id = "primary:" + hashlib.sha256(("pib_html\0" + entry_id).encode()).hexdigest()
            item = {
                "provider": "pib_html",
                "source_id": entry_id,
                "provider_entry_id": entry_id,
                "news_id": news_id,
                "source_type": "government_release",
                "canonical_url": result["source_url"],
                "title": result["title"],
                "summary": result["excerpt"],
                "published_raw": result.get("published_raw"),
                "publication_precision": result.get("publication_precision", "unknown"),
                "published_at_utc": None,
                "timezone_basis": result.get("timezone_basis"),
                "source_hash": result["source_hash"],
                "event_at": None,
                "event_id": None,
                "identity_basis": "PIB release ID; government origin; issuer unmapped",
                "issuer_identifiers": [],
                "source_owner": result["source_owner"],
                "terms": TERMS["pib_rss"],
                "retention": "attributed reviewed first-party excerpt",
                "extraction": {
                    k: result[k]
                    for k in ("offset", "end_offset", "offset_basis", "truncated", "completeness")
                },
            }
            version = repository.record(item, fetched_at=fetched)
            saved = repository.read(version, cutoff=fetched)
            current = session.get(NewsArticleRow, news_id)
            if current is None or current.payload.get("source_version_id") != version:
                NewsRepository(session).upsert_news_item(
                    {
                        **item,
                        "source_id": news_id,
                        "source_version_id": version,
                        "source_key": saved["source_key"],
                        "source_content_hash": saved["content_hash"],
                        "source_first_seen_at": saved["first_seen_at"],
                        "source_version_first_seen_at": saved["version_first_seen_at"],
                    },
                    source="primary_source_ingestion",
                )
            details.update(entry_count=1, version_id=version, source_hash=result["source_hash"])
        else:
            details["error"] = result.get("reason")
        repository.record_fetch(
            "pib_html", fetched_at=fetched, status=result["status"], details=details
        )
    return {"provider": "pib_html", **details, "fetched_at": fetched.isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", nargs="*", choices=sorted(SOURCES), default=[])
    parser.add_argument("--pib-release")
    parser.add_argument("--first-party-reviewed", action="store_true")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.sources and not args.pib_release:
        parser.error("Select feeds or one reviewed PIB release")
    reports = ingest(args.sources, args.run_id)
    if args.pib_release:
        reports.append(
            ingest_pib_release(
                args.pib_release, args.run_id, first_party_reviewed=args.first_party_reviewed
            )
        )
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
