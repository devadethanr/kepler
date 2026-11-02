"""Synthetic snapshot fixtures, isolated in SQLite."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from memory.models import Base, NewsSourceObservationRow, NewsSourceVersionRow
from memory.news_snapshot import NewsSnapshotRepository


def at(day, hour=0):
    return datetime(2026, 1, day, hour, tzinfo=timezone.utc)


@pytest.fixture
def repo():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[NewsSourceVersionRow.__table__,
        NewsSourceObservationRow.__table__, Base.metadata.tables["news_source_fetches"]])
    with Session(engine) as session:
        yield NewsSnapshotRepository(session)
    engine.dispose()


def item(**changes):
    return {"provider": "regulator", "provider_entry_id": "entry-1", "title": "Release",
            "summary": "Example", "publication_precision": "date",
            "published_date": "2026-01-01", "published_raw": "01 Jan 2026",
            "timezone_basis": "Asia/Kolkata", **changes}


def search(repo, cutoff, **kwargs):
    return repo.search(cutoff=cutoff, start=datetime(2025, 12, 31, tzinfo=timezone.utc),
                       end=at(5), providers=["regulator"], **kwargs)


def test_versions_observations_and_reversion_are_causal(repo):
    first = repo.record(item(), fetched_at=at(2))
    assert repo.record(item(), fetched_at=at(3)) == first
    second = repo.record(item(summary="Amended"), fetched_at=at(4))
    assert second != first
    assert repo.read(second, cutoff=at(3)) is None
    assert search(repo, at(3))["items"][0]["version_id"] == first
    assert search(repo, at(4))["items"][0]["version_id"] == second
    assert repo.record(item(), fetched_at=at(5)) == first
    assert search(repo, at(5))["items"][0]["version_id"] == first
    assert repo.read(first, cutoff=at(5))["first_seen_at"] == at(2).isoformat()
    assert len(repo.session.scalars(select(NewsSourceVersionRow)).all()) == 2
    assert len(repo.session.scalars(select(NewsSourceObservationRow)).all()) == 3
    assert repo.read(first, cutoff=at(5))["supersedes_version_id"] == second
    assert repo.read(second, cutoff=at(4))["version_first_seen_at"] == at(4).isoformat()
    assert repo.read(second, cutoff=at(4))["first_seen_at"] == at(2).isoformat()
    assert repo.read(first, cutoff=at(4))["version_status"] == "superseded"
    assert repo.read(first, cutoff=at(4))["current_version_id"] == second


def test_date_only_availability_and_unknown_dates(repo):
    repo.record(item(), fetched_at=at(1, 12))
    repo.record(item(provider_entry_id="unknown", publication_precision="unknown"), fetched_at=at(1, 12))
    result = search(repo, at(1, 12))
    assert result["items"] == []
    assert result["unknown_publication_dates"] == 1
    assert len(search(repo, at(1, 19))["items"]) == 1


def test_source_offset_date_is_conservatively_bounded(repo):
    repo.record(item(timezone_basis="source offset +0530"), fetched_at=at(1, 12))
    assert not search(repo, at(1, 18))["items"]
    assert len(search(repo, at(1, 19))["items"]) == 1


def test_minute_precision_is_not_an_exact_publication_instant(repo):
    repo.record(item(publication_precision="minute", published_at_utc="2026-01-01T12:00:00Z"),
                fetched_at=at(1, 12))
    assert not search(repo, at(1, 12))["items"]
    assert len(search(repo, datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc))["items"]) == 1


def test_minute_with_unknown_timezone_stays_undated(repo):
    version = repo.record(item(publication_precision="minute", published_at_utc=None,
                               timezone_basis="unknown"), fetched_at=at(2))
    found = search(repo, at(2), include_unknown=True)
    assert found["items"] == []
    assert found["unknown_publication_dates"] == 1
    assert found["undated_items"][0]["version_id"] == version
    assert found["undated_items"][0]["temporal_membership"] == "unknown"


def test_namespaces_identity_and_coverage(repo):
    a = repo.record(item(), fetched_at=at(2))
    b = repo.record(item(provider="another"), fetched_at=at(2))
    assert a != b
    row = repo.read(a, cutoff=at(2))
    assert row["identity_basis"] == "unmapped"
    assert row["issuer_identifiers"] == []
    repo.record_fetch("regulator", fetched_at=at(2), status="valid_empty")
    assert search(repo, at(2))["coverage"]["regulator"]["status"] == "valid_empty"
    assert search(repo, at(1))["coverage"]["regulator"]["status"] == "unknown"


def test_rejects_ambiguous_times_and_retroactive_observations(repo):
    with pytest.raises(ValueError):
        repo.record(item(), fetched_at="2026-01-02T00:00:00")
    repo.record(item(), fetched_at=at(2))
    with pytest.raises(ValueError):
        repo.record(item(summary="changed"), fetched_at=at(2))
    with pytest.raises(ValueError):
        repo.record(item(), fetched_at=at(1))


def test_provider_hash_and_identity_fallback_are_preserved(repo):
    version = repo.record(item(provider_entry_id=None, source_id="https://example.test/1",
                               canonical_url="https://example.test/1", content_hash="raw-hash"),
                          fetched_at=at(2))
    saved = repo.read(version, cutoff=at(2))
    assert saved["provider_content_hash"] == "raw-hash"
    assert saved["raw_provider_entry_id"] is None
    assert saved["provider_entry_id"] is None
    assert saved["resolved_entry_id"] == "https://example.test/1"
    assert saved["source_identity_basis"] == "canonical_url_fallback"


def test_raw_fetch_hash_changes_do_not_create_source_revisions(repo):
    first = repo.record(item(source_hash="body-a", content_hash="entry-a"), fetched_at=at(2))
    again = repo.record(item(source_hash="body-b", content_hash="entry-b"), fetched_at=at(3))
    assert again == first
    assert len(repo.session.scalars(select(NewsSourceObservationRow)).all()) == 1
    saved = repo.read(first, cutoff=at(3))
    assert saved["source_hash"] == "body-a"
    assert saved["provider_content_hash"] == "entry-a"
    revised_date = repo.record(item(source_hash="body-c", content_hash="entry-c",
                                    published_raw="corrected source date"), fetched_at=at(4))
    assert revised_date != first
    revised_title = repo.record(item(source_hash="body-d", content_hash="entry-d",
                                     published_raw="corrected source date", title="New title"),
                                fetched_at=at(5))
    assert revised_title not in {first, revised_date}


def test_unchanged_legacy_version_is_not_rewritten(repo):
    version = repo.record(item(source_hash="old-body"), fetched_at=at(2))
    row = repo.session.get(NewsSourceVersionRow, version)
    observation = repo.session.scalars(select(NewsSourceObservationRow)).one()
    row.version_id = "legacy-version-id"
    observation.version_id = "legacy-version-id"
    repo.session.flush()
    assert repo.record(item(source_hash="new-body"), fetched_at=at(3)) == "legacy-version-id"
    assert repo.read("legacy-version-id", cutoff=at(3))["source_hash"] == "old-body"
    assert len(repo.session.scalars(select(NewsSourceVersionRow)).all()) == 1


def test_undated_items_are_explicitly_separate_and_bounded(repo):
    for i in range(8):
        repo.record(item(provider_entry_id=str(i), publication_precision="unknown"), fetched_at=at(2))
    found = search(repo, at(2), include_unknown=True)
    assert found["items"] == []
    assert found["unknown_publication_dates"] == 8
    assert len(found["undated_items"]) == 6
    assert found["undated_truncated"] is True
    assert all(item["temporal_membership"] == "unknown" for item in found["undated_items"])
    assert search(repo, at(2), topic="missing", include_unknown=True)["undated_items"] == []
    assert search(repo, at(2))["undated_items"] == []


def test_frozen_allowlist_applies_before_caps_and_after_revision_ranking(repo):
    allowed = repo.record(item(provider_entry_id="allowed", publication_precision="unknown"),
                          fetched_at=at(2))
    for i in range(8):
        repo.record(item(provider_entry_id=str(i), publication_precision="unknown"), fetched_at=at(3))
    found = search(repo, at(3), include_unknown=True, version_ids=[allowed])
    assert [item["version_id"] for item in found["undated_items"]] == [allowed]
    assert found["unknown_publication_dates"] == 1
    assert search(repo, at(3), include_unknown=True, version_ids=[])["undated_items"] == []
    newer = repo.record(item(provider_entry_id="allowed", publication_precision="unknown",
                             summary="revised"), fetched_at=at(4))
    assert search(repo, at(4), include_unknown=True, version_ids=[allowed])["undated_items"] == []
    assert [item["version_id"] for item in search(
        repo, at(4), include_unknown=True, version_ids=[newer])["undated_items"]] == [newer]
