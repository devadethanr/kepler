"""Real isolated SQLite observation history, read budgets and typed unavailable states."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from data.market_context.refresh import refresh
from memory.market_snapshot import MarketSnapshotRepository
from memory.models import MarketObservationRow
from research_room.grounding import validate_claims
from research_room.market_evidence import MarketEvidence


def at(day, hour=0):
    return datetime(2026, 1, day, hour, tzinfo=timezone.utc)


def quote(**changes):
    return {
        "provider": "isolated_fixture",
        "symbol": "STI",
        "instrument_id": "cash:STI",
        "exchange": "SGX",
        "instrument_kind": "cash_index",
        "quote_value": 4000,
        "quote_unit": "index_points",
        "exchange_asof": at(2).isoformat(),
        "received_at": at(2).isoformat(),
        "first_seen_at": at(2).isoformat(),
        "market_state": "open",
        "delay_seconds": 0,
        "status": "ok",
        **changes,
    }


@pytest.fixture
def storage(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "market.sqlite"))
    MarketObservationRow.__table__.create(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def scope():
        with factory() as session, session.begin():
            yield session

    yield factory, scope
    engine.dispose()


def test_availability_asof_allowlists_and_out_of_order_highwater(storage):
    _, scope = storage
    with scope() as session:
        repo = MarketSnapshotRepository(session)
        a = repo.record("singapore_sti", quote(), observed_at=at(2))
        b = repo.record(
            "singapore_sti",
            quote(exchange_asof=at(3).isoformat(), received_at=at(3).isoformat()),
            observed_at=at(3),
        )
        c = repo.record("singapore_sti", quote(received_at=at(4).isoformat()), observed_at=at(4))
        assert c["status"] == "invalid"
        assert "out_of_order_exchange_time" in c["quality_reasons"]
        d = repo.record(
            "singapore_sti",
            quote(exchange_asof=at(2, 12).isoformat(), received_at=at(5).isoformat()),
            observed_at=at(5),
        )
        assert d["status"] == "invalid"  # Invalid arrivals never lower the high-water mark.
        assert repo.latest("singapore_sti", cutoff=at(1)) is None
        assert repo.latest("singapore_sti", cutoff=at(2))["snapshot_id"] == a["snapshot_id"]
        assert repo.latest("singapore_sti", cutoff=at(3))["snapshot_id"] == b["snapshot_id"]
        assert repo.latest("singapore_sti", cutoff=at(5), snapshot_ids=[a["snapshot_id"]]) == a
        assert repo.latest("singapore_sti", cutoff=at(5), snapshot_ids=[]) is None
        with pytest.raises(ValueError, match="retroactively"):
            repo.record("singapore_sti", quote(), observed_at=at(2))


def test_equal_availability_cannot_silently_select_hash_order(storage):
    _, scope = storage
    with scope() as session:
        repo = MarketSnapshotRepository(session)
        original = repo.record("singapore_sti", quote(), observed_at=at(2))
        assert repo.record("singapore_sti", quote(), observed_at=at(2)) == original
        with pytest.raises(ValueError, match="identical availability"):
            repo.record("singapore_sti", quote(quote_value=4001), observed_at=at(2))


def test_saved_body_and_cutoff_are_not_replaced_by_current_metadata(storage):
    _, scope = storage
    with scope() as session:
        saved = MarketSnapshotRepository(session).record(
            "singapore_sti", quote(), observed_at=at(2)
        )
    room = {
        "target": "Kepler",
        "source_cutoff": at(5).isoformat(),
        "evidence_scope": {
            "market_scopes": ["singapore_sti"],
            "market_snapshot_ids": [saved["snapshot_id"]],
        },
    }
    service = MarketEvidence(room, scope)
    found = service.read("singapore_sti", at(2).isoformat())
    assert found["observations"][0]["snapshot_id"] == saved["snapshot_id"]
    later = service.read("singapore_sti", at(5).isoformat())
    assert later["observations"][0]["market_state_at_cutoff"] == "closed"
    assert "collector_observation_not_recent" in later["observations"][0]["quality_reasons"]
    assert later["observations"][0]["market_state"] == "open"  # At original observation.
    with scope() as session:
        assert MarketSnapshotRepository(session).latest("singapore_sti", cutoff=at(5)) == saved
    with pytest.raises(ValueError, match="exceeds"):
        service.read("singapore_sti", at(6).isoformat())
    with pytest.raises(ValueError, match="selected inputs"):
        service.read("gift_nifty")


def test_missing_history_is_not_backfilled_and_availability_summary_is_citable(storage):
    _, scope = storage
    room = {"target": "Kepler", "source_cutoff": at(3).isoformat()}
    result = MarketEvidence(room, scope).read("all", at(1).isoformat())
    assert len(result["observations"]) == 3
    for item in result["observations"]:
        assert item["status"] == "unavailable" and item["quote_value"] is None
        assert item["first_seen_at"] is None and item["snapshot_id"] is None
    packet = result["evidence"][0]
    assert packet["source_type"] == "derived_market_observation_summary"
    assert packet["market_snapshot"]["status"] == "unavailable"
    assert validate_claims(
        "Kepler",
        [{"evidence_id": packet["id"], "quote": packet["quote_spans"][0]["id"]}],
        {packet["id"]: packet},
    )
    assert result["limits"]["network_requests"] == 0


def test_refresh_is_rate_limited_and_cancelled_without_provider_requests(storage):
    factory, scope = storage
    stopped = Event()
    stopped.set()
    assert refresh(factory=factory, cancelled=stopped)["status"] == "cancelled"
    first = refresh(factory=factory)
    assert first["status"] == "recorded_unavailable"
    assert len(first["snapshots"]) == 3 and first["network_requests"] == 0
    assert refresh(factory=factory)["status"] == "rate_limited"
    with scope() as session:
        assert session.scalar(select(func.count()).select_from(MarketObservationRow)) == 3
    with scope() as session:
        repo = MarketSnapshotRepository(session)
        original = repo.latest("gift_nifty", cutoff=datetime.now(timezone.utc))
        before = datetime.fromisoformat(
            original["first_seen_at"].replace("Z", "+00:00")
        ) - timedelta(seconds=1)
        assert repo.latest("gift_nifty", cutoff=before) is None
