"""Synthetic records live only in the fixture's disposable SQLite database."""

from contextlib import contextmanager
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from memory.models import Base
from memory.news_snapshot import NewsSnapshotRepository
from research_room.grounding import validate_claims
from research_room.news_evidence import NewsEvidence, source_status


@pytest.fixture
def source_scope(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "synthetic-news.db"))
    Base.metadata.create_all(engine)

    @contextmanager
    def scope():
        with Session(engine) as session, session.begin():
            yield session

    with scope() as session:
        repository = NewsSnapshotRepository(session)
        common = {
            "provider": "sebi_rss",
            "source_type": "regulator",
            "published_raw": "01 Jan, 2026 +0530",
            "published_date": "2026-01-01",
            "publication_precision": "date",
            "timezone_basis": "source offset +0530",
            "identity_basis": "text mention; issuer unmapped",
        }
        for n, title in enumerate(
            (
                "ACME permits a synthetic activity.",
                "ACME denies the synthetic activity.",
                "BETA releases unrelated synthetic accounts.",
            )
        ):
            repository.record(
                {
                    **common,
                    "provider_entry_id": str(n),
                    "title": title,
                    "canonical_url": f"https://example.invalid/{n}",
                },
                fetched_at="2026-01-02T00:00:00Z",
            )
        repository.record(
            {**common, "provider_entry_id": "late", "title": "ACME late record.",
             "canonical_url": "https://example.invalid/late"},
            fetched_at="2026-01-04T00:00:00Z",
        )
        repository.record_fetch("sebi_rss", fetched_at="2026-01-02T00:00:00Z", status="partial")
        repository.record_fetch(
            "rbi_press_releases_rss", fetched_at="2026-01-02T00:00:00Z", status="deadline"
        )
    yield scope
    engine.dispose()


def service(scope):
    return NewsEvidence(
        {"id": str(uuid4()), "target": "ACME", "source_cutoff": "2026-01-03T00:00:00Z"}, scope=scope
    )


def args(**changes):
    return {
        "topic": "ACME",
        "start": "2025-12-31T00:00:00Z",
        "end": "2026-01-03T00:00:00Z",
        "cutoff": "",
        "sources": "",
        "offset": "",
        **changes,
    }


def test_saved_sources_keep_conflicts_identity_precision_and_quote_provenance(source_scope):
    result = service(source_scope).search(args())
    assert len(result["evidence"]) == 2
    assert result["coverage"]["rbi_press_releases_rss"]["status"] == "deadline"
    for evidence in result["evidence"]:
        assert evidence["published_at"] is None
        assert evidence["event_id"] is None
        assert evidence["source_snapshot"]["publication_precision"] == "date"
        assert evidence["entity_identity"] == "text mention; issuer unmapped"
        assert evidence["source_snapshot"]["first_seen_at"] == "2026-01-02T00:00:00+00:00"
        validate_claims(
            "ACME",
            [{"evidence_id": evidence["id"], "quote": evidence["quote_spans"][0]["id"]}],
            {evidence["id"]: evidence},
        )


def test_future_cutoff_and_versions_are_not_read_as_historical_evidence(source_scope):
    reader = service(source_scope)
    with pytest.raises(ValueError):
        reader.search(args(cutoff="2026-01-05T00:00:00Z"))
    with pytest.raises(ValueError):
        reader.search(args(sources="made_up"))
    assert reader.read("not-a-saved-version")["status"] == "unavailable"
    assert reader.search(args(topic="No match"))["status"] == "empty"
    assert source_status(source_scope)["sources"]


def test_read_resolves_same_revision_and_frozen_allowlist(source_scope):
    reader = service(source_scope)
    evidence = reader.search(args())["evidence"][0]
    record = reader.read(evidence["record_id"])["evidence"][0]
    assert record["text"] == evidence["text"]
    assert record["source_snapshot"]["version_id"] == evidence["record_id"]
    reader.options["version_ids"] = []
    assert reader.search(args())["evidence"] == []
    with pytest.raises(ValueError):
        reader.read(evidence["record_id"])


def query(**kwargs):
    return {"topic": "", "start": "2025-12-31T00:00:00Z", "end": "2026-01-05T00:00:00Z",
            "cutoff": "", "sources": "sebi_rss", "offset": "", **kwargs}


@pytest.mark.parametrize("count", [3, 6, 8])
def test_undated_counts_on_every_dated_page(source_scope, count):
    with source_scope() as session:
        repo = NewsSnapshotRepository(session)
        for n in range(count):
            repo.record({"provider": "sebi_rss", "provider_entry_id": f"undated-{n}",
                         "canonical_url": f"https://example.invalid/u{n}", "title": "unknown",
                         "publication_precision": "unknown"}, fetched_at="2026-01-02T00:00:00Z")
        for n in range(8):
            repo.record({"provider": "sebi_rss", "provider_entry_id": f"dated-{n}",
                         "canonical_url": f"https://example.invalid/d{n}", "title": "dated",
                         "publication_precision": "date", "published_date": "2026-01-01",
                         "timezone_basis": "source offset +0000"}, fetched_at="2026-01-02T00:00:00Z")
    service = NewsEvidence({"target": "ACME", "source_cutoff": "2026-01-05T00:00:00Z"},
                           scope=source_scope)
    first = service.search(query())["retrieval"]
    later = service.search(query(offset="6"))["retrieval"]
    assert first["undated_returned"] == 2 and first["undated_omitted_scanned"] == count - 2
    assert later["undated_returned"] == 0 and later["undated_omitted_scanned"] == count
    assert first["undated_truncated"] and later["undated_truncated"]
    assert "unavailable" in later["undated_continuation"]


def test_gateway_predecessor_reversion_and_frozen_scope(source_scope, monkeypatch):
    from types import SimpleNamespace
    import research_room.news_evidence as evidence_module
    from research_room.tools import Gateway

    base = {"provider": "sebi_rss", "provider_entry_id": "revision",
            "canonical_url": "https://example.invalid/revision", "title": "Alpha",
            "publication_precision": "date", "published_date": "2026-01-01",
            "timezone_basis": "source offset +0000"}
    with source_scope() as session:
        repo = NewsSnapshotRepository(session)
        a = repo.record(base, fetched_at="2026-01-02T00:00:00Z")
        b = repo.record({**base, "title": "Beta"}, fetched_at="2026-01-03T00:00:00Z")
        assert repo.record(base, fetched_at="2026-01-04T00:00:00Z") == a
    original = evidence_module.NewsEvidence

    class LocalEvidence(original):
        def __init__(self, room, **kwargs):
            super().__init__(room, scope=source_scope, **kwargs)

    monkeypatch.setattr(evidence_module, "NewsEvidence", LocalEvidence)
    gateway = Gateway.__new__(Gateway)
    gateway.room = {"target": "ACME", "source_cutoff": "2026-01-05T00:00:00Z"}
    gateway.settings = SimpleNamespace(source_stale_after_seconds=86400)
    gateway.evidence, gateway.news_versions = {}, {}
    def dispatch(name, values):
        return gateway.dispatch("analyst", "fixture", name, values)

    dispatch("news_search", query(topic="Alpha", cutoff="2026-01-02T12:00:00Z",
                                  end="2026-01-02T12:00:00Z"))
    dispatch("news_search", query(topic="Beta", cutoff="2026-01-03T12:00:00Z",
                                  end="2026-01-03T12:00:00Z"))
    dispatch("news_search", query(topic="Alpha", cutoff="2026-01-04T12:00:00Z",
                                  end="2026-01-04T12:00:00Z"))
    result = dispatch("news_read", {"version_id": a, "offset": ""})["evidence"][0]
    assert result["decision_cutoff"] == "2026-01-02T12:00:00+00:00"
    assert result["source_snapshot"]["version_status"] != "superseded"
    assert gateway.news_versions[b] == "2026-01-03T12:00:00+00:00"
    gateway.room["evidence_scope"] = {"version_ids": [a]}
    with pytest.raises(ValueError, match="frozen"):
        dispatch("news_read", {"version_id": b, "offset": ""})
    assert not dispatch("news_search", query(topic="Beta", cutoff="2026-01-03T12:00:00Z",
                                             end="2026-01-03T12:00:00Z"))["evidence"]


def test_undated_scan_limit_reports_lower_bound(source_scope):
    with source_scope() as session:
        repo = NewsSnapshotRepository(session)
        for n in range(1001):
            repo.record({"provider": "sebi_rss", "provider_entry_id": f"scan-{n}",
                         "title": "scan", "canonical_url": f"https://example.invalid/scan{n}",
                         "publication_precision": "unknown"},
                        fetched_at="2026-01-02T00:00:00Z")
    service = NewsEvidence({"target": "ACME", "source_cutoff": "2026-01-05T00:00:00Z"},
                           scope=source_scope)
    retrieval = service.search(query(topic="scan"))["retrieval"]
    assert retrieval["scan_truncated"]
    assert retrieval["undated_matches_scanned"] <= 1000
    assert "lower bound" in retrieval["undated_count_scope"]
    assert retrieval["undated_truncated"]
