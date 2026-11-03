from datetime import datetime

import pytest
from pydantic import ValidationError

from data.market_context.calendar import last_completed_sti_close, session, sti_session
from data.market_context.collector import collect
from data.market_context.snapshot import MarketSnapshot, assess


def dt(s):
    return datetime.fromisoformat(s)


def make(**kw):
    data = dict(
        provider="fixture",
        symbol="NIFTY",
        received_at=dt("2026-11-02T05:00:00+00:00"),
        first_seen_at=dt("2026-11-02T05:00:00+00:00"),
        quote_value=25000,
        quote_unit="index_points",
        exchange_asof=dt("2026-11-02T04:59:00+00:00"),
        delay_seconds=120,
        status="ok",
        market_state="open",
    )
    data.update(kw)
    return MarketSnapshot(**data)


def test_unavailable_collect_is_network_free_and_preserves_identity():
    gift, sti = collect(dt("2026-11-02T05:00:00+00:00"))
    assert gift["quote_value"] is None and gift["status"] == "unavailable"
    assert sti["instrument_kind"] == "cash_index" and sti["market_state"] == "open"
    assert sti["session_id"] == "sti_calculation"
    assert all(len(item["raw_observation_hash"]) == 64 for item in (gift, sti))
    assert gift["config_version"] == "availability-only-v1"
    assert [x["raw_observation_hash"] for x in collect(dt("2026-11-03T05:00:00+00:00"))] == [
        gift["raw_observation_hash"],
        sti["raw_observation_hash"],
    ]


def test_sgx_holiday_halfday_and_boundaries():
    assert session("SGX", dt("2026-11-09T02:00:00+08:00"))["market_state"] == "closed"
    assert session("SGX", dt("2026-12-24T12:10:00+08:00"))["market_state"] == "unknown"
    assert session("SGX", dt("2026-12-24T13:00:00+08:00"))["market_state"] == "closed"
    assert session("SGX", dt("2026-11-02T12:00:00+08:00"))["market_state"] == "break"
    assert session("SGX", dt("2027-01-04T10:00:00+08:00"))["market_state"] == "unknown"
    assert session("SGX", datetime(2026, 11, 2))["market_state"] == "unknown"


def test_overnight_business_date_and_special_session_unknown():
    friday = session("NSEIX", dt("2026-11-07T01:00:00+05:30"))
    assert friday["market_date"] is None and friday["market_state"] == "unknown"
    assert session("NSEIX", dt("2026-11-08T12:00:00+05:30"))["market_state"] == "unknown"
    assert session("NSEIX", dt("2026-10-02T12:00:00+05:30"))["market_state"] == "unknown"


def test_validation_and_quality_are_separate_from_session():
    with pytest.raises(ValidationError):
        make(instrument_kind="future")
    with pytest.raises(ValidationError):
        make(quote_value=float("nan"))
    with pytest.raises(ValidationError):
        make(reference_value=1)
    with pytest.raises(ValidationError):
        make(exchange_asof=datetime(2026, 11, 2))
    now = dt("2026-11-02T05:05:00+00:00")
    assert assess(make(), now=now, stale_after_seconds=120).status == "stale"
    closed = assess(make(market_state="closed"), now=now, stale_after_seconds=120)
    assert closed.status == "partial" and "closed_reference_unverified" in closed.quality_reasons
    partial = assess(make(status="partial", delay_seconds=None), now=now, stale_after_seconds=1000)
    assert partial.status == "partial" and "delay_unknown" in partial.quality_reasons
    earlier = make(exchange_asof=dt("2026-11-02T04:58:00+00:00"))
    assert assess(earlier, now=now, stale_after_seconds=1000, previous=make()).status == "invalid"
    with pytest.raises(ValueError):
        assess(make(), now=dt("2026-11-02T04:00:00+00:00"), stale_after_seconds=120)


@pytest.mark.parametrize(
    ("when", "state", "market_date"),
    [
        ("2026-11-07T00:00:00+05:30", "unknown", None),
        ("2026-11-07T02:44:59+05:30", "unknown", None),
        ("2026-11-07T02:45:00+05:30", "unknown", None),
        ("2026-10-03T01:00:00+05:30", "unknown", None),
        ("2026-11-09T01:00:00+05:30", "unknown", None),
        ("2027-01-04T10:00:00+05:30", "unknown", None),
    ],
)
def test_gift_overnight_holiday_and_coverage(when, state, market_date):
    result = session("NSEIX", dt(when))
    assert (result["market_state"], result["market_date"]) == (state, market_date)


def test_gift_muhurat_is_explicitly_unknown_and_sgx_is_not_sti():
    special = session("NSEIX", dt("2026-11-08T18:00:00+05:30"))
    assert special["market_state"] == "unknown"
    assert special["session_id"] == "muhurat_timing_unverified"
    gift, sti = collect(dt("2026-11-02T04:30:00+00:00"))
    assert (gift["instrument_kind"], gift["quote_unit"], gift["settlement_currency"]) == (
        "future",
        "index_points",
        "USD",
    )
    assert gift["contract"] is None and gift["expiry"] is None
    assert sti["session_id"] == "sti_calculation" and sti["market_state"] == "open"


@pytest.mark.parametrize(
    ("when", "state"),
    [
        ("2026-12-24T08:59:59+08:00", "closed"),
        ("2026-12-24T09:00:00+08:00", "open"),
        ("2026-12-24T11:59:59+08:00", "open"),
        ("2026-12-24T12:00:00+08:00", "unknown"),
        ("2026-12-24T12:16:00+08:00", "closed"),
        ("2026-11-02T12:59:59+08:00", "break"),
        ("2026-11-02T13:00:00+08:00", "open"),
        ("2026-11-02T17:00:00+08:00", "unknown"),
        ("2026-11-02T17:16:00+08:00", "closed"),
        ("2026-11-09T10:00:00+08:00", "closed"),
        ("2027-01-04T10:00:00+08:00", "unknown"),
    ],
)
def test_sgx_securities_calendar_boundaries(when, state):
    assert session("SGX", dt(when))["market_state"] == state


def test_quote_validation_units_expiry_reference_and_temporal_availability():
    with pytest.raises(ValidationError):
        make(quote_unit="USD")
    with pytest.raises(ValidationError):
        make(delay_seconds=-1)
    with pytest.raises(ValidationError):
        make(exchange_asof=dt("2026-11-02T05:01:00+00:00"))
    with pytest.raises(ValidationError):
        make(
            instrument_kind="future", contract="NOV", expiry="2026-10-30", market_date="2026-11-02"
        )
    with pytest.raises(ValidationError):
        make(reference_value=24900, basis="previous_close")
    known_reference = make(
        reference_value=24900,
        basis="previous_close",
        reference_asof=dt("2026-10-30T10:00:00+00:00"),
    )
    assert known_reference.basis == "previous_close" and known_reference.reference_value == 24900
    not_available = make(first_seen_at=dt("2026-11-02T05:10:00+00:00"))
    with pytest.raises(ValueError, match="not yet available"):
        assess(not_available, now=dt("2026-11-02T05:05:00+00:00"), stale_after_seconds=100)


def test_quality_failure_precedence_cutoff_state_and_out_of_order_identity():
    now = dt("2026-11-02T05:05:00+00:00")
    for failed in ("invalid", "unavailable"):
        item = make(status=failed, delay_seconds=None)
        assert assess(item, now=now, stale_after_seconds=10).status == failed
    old_closed = make(market_state="closed")
    opened = assess(old_closed, now=now, stale_after_seconds=120, market_state_at_cutoff="open")
    assert opened.status == "stale" and opened.market_state == "closed"
    unknown = assess(old_closed, now=now, stale_after_seconds=120, market_state_at_cutoff="unknown")
    assert unknown.status == "partial"
    assert "quote_age_exceeds_threshold_session_unknown" in unknown.quality_reasons
    delayed = assess(make(), now=now, stale_after_seconds=1000)
    assert "provider_delay_reported" in delayed.quality_reasons
    earlier = make(exchange_asof=dt("2026-11-02T04:58:00+00:00"))
    other = make(symbol="OTHER")
    assert assess(earlier, now=now, stale_after_seconds=1000, previous=other).status == "ok"


def test_master_index_candidate_is_not_future_or_a_quote():
    from data.market_context.instruments import kite_master_candidates

    rows = [
        {
            "exchange": "NSEIX",
            "tradingsymbol": "GIFT NIFTY",
            "name": "GIFT NIFTY",
            "segment": "INDICES",
            "instrument_type": "EQ",
            "expiry": "",
            "instrument_token": "123",
        },
        {
            "exchange": "NSE",
            "tradingsymbol": "NIFTY TRANS LOGIS",
            "name": "NIFTY TRANSPORTATION & LOGISTICS",
            "segment": "INDICES",
            "instrument_type": "EQ",
        },
        {"exchange": "SGX", "tradingsymbol": "STI", "segment": "INDICES", "instrument_type": "EQ"},
    ]
    gift, sti = kite_master_candidates(rows)
    assert gift["instrument_type"] == "EQ" and gift["expiry"] is None
    assert gift["qualification"] == "master_entry_only_quote_entitlement_unverified"
    assert sti["scope"] == "singapore_sti"


@pytest.mark.parametrize(
    ("when", "state"),
    [
        ("2026-11-02T08:59:59+08:00", "closed"),
        ("2026-11-02T09:00:00+08:00", "open"),
        ("2026-11-02T12:30:00+08:00", "open"),
        ("2026-11-02T17:09:59+08:00", "open"),
        ("2026-11-02T17:10:00+08:00", "closed"),
        ("2026-11-09T10:00:00+08:00", "closed"),
        ("2026-12-24T10:00:00+08:00", "unknown"),
        ("2026-12-24T18:00:00+08:00", "unknown"),
        ("2027-01-04T10:00:00+08:00", "unknown"),
    ],
)
def test_sti_calculation_calendar_boundaries(when, state):
    assert sti_session(dt(when))["market_state"] == state


def test_sti_naive_time_is_unknown():
    assert sti_session(datetime(2026, 11, 2))["market_date"] is None


def test_delayed_quote_staleness_accounts_for_declared_delay():
    now = dt("2026-11-02T05:09:00+00:00")
    delayed = make(delay_seconds=600)
    assert assess(delayed, now=now, stale_after_seconds=300).status == "ok"
    assert (
        assess(delayed, now=dt("2026-11-02T05:15:00+00:00"), stale_after_seconds=300).status
        == "stale"
    )


def test_closed_quote_requires_matching_verified_last_close():
    friday_close = dt("2026-10-30T09:10:00+00:00")
    weekend = dt("2026-11-01T05:00:00+00:00")
    snapshot = make(
        received_at=friday_close,
        first_seen_at=friday_close,
        exchange_asof=friday_close,
        market_state="closed",
        quote_basis="last_completed_session_close",
    )
    verified = last_completed_sti_close(weekend)
    assert verified == friday_close
    assert (
        assess(
            snapshot, now=weekend, stale_after_seconds=300, last_completed_close_at=verified
        ).status
        == "ok"
    )
    assert assess(snapshot, now=weekend, stale_after_seconds=300).status == "partial"
    assert (
        assess(
            snapshot.model_copy(update={"quote_basis": "last_quote"}),
            now=weekend,
            stale_after_seconds=300,
            last_completed_close_at=verified,
        ).status
        == "partial"
    )
    monday_open = dt("2026-11-02T02:00:00+00:00")
    assert (
        assess(
            snapshot,
            now=monday_open,
            stale_after_seconds=300,
            market_state_at_cutoff="open",
            last_completed_close_at=verified,
        ).status
        == "stale"
    )


def test_sti_last_close_fails_closed_for_half_days_and_year_gaps():
    assert last_completed_sti_close(dt("2026-12-25T12:00:00+08:00")) is None
    assert last_completed_sti_close(dt("2027-01-04T12:00:00+08:00")) is None
    assert last_completed_sti_close(datetime(2026, 11, 2)) is None


def test_future_quote_requires_market_date_but_unavailable_metadata_does_not():
    with pytest.raises(ValidationError, match="verified market date"):
        make(instrument_kind="future", contract="NOV", expiry="2026-11-24")
    future = make(
        instrument_kind="future", contract="NOV", expiry="2026-11-24", market_date="2026-11-02"
    )
    assert future.expiry.isoformat() == "2026-11-24"
    assert collect(dt("2026-11-02T05:00:00+00:00"))[0]["market_date"] is None
