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
            {**common, "provider_entry_id": "late", "title": "ACME late record."},
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
