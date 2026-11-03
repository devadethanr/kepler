"""Explicit unavailable observations until a licensed, entitled adapter is configured.

This is intentionally network-free. Neither provider documentation nor an instrument
master establishes account entitlement, rights to retain observations, or freshness.
"""

import hashlib
import json
from datetime import datetime, timezone

from data.market_context.calendar import session, sti_session
from data.market_context.snapshot import MarketSnapshot

CONFIG_VERSION = "availability-only-v1"


def _availability_record(snapshot: MarketSnapshot) -> dict:
    """Hash the static availability/specification metadata, never a price payload."""
    record = snapshot.model_dump(mode="json")
    keys = (
        "provider",
        "source",
        "symbol",
        "underlying",
        "instrument_kind",
        "exchange",
        "quote_unit",
        "settlement_currency",
        "status",
        "quality_reasons",
        "source_version",
        "source_document_sha256",
        "contract_specification",
        "expiry_rule_source",
        "expiry_rule_document_sha256",
        "config_version",
        "calendar_version",
    )
    metadata = {key: record[key] for key in keys}
    encoded = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    record["raw_observation_hash"] = hashlib.sha256(encoded).hexdigest()
    return record


def collect(now: datetime | None = None) -> list[dict]:
    """Collect two truthful availability records without touching broker services."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("collection time must be timezone-aware")
    gift = MarketSnapshot(
        provider="unconfigured",
        source="https://www.nseix.com/api/content/circulars/NSEIFSC_TRADE_904.pdf",
        symbol="GIFT Nifty",
        underlying="NIFTY 50",
        instrument_kind="future",
        exchange="NSEIX",
        quote_unit="index_points",
        settlement_currency="USD",
        source_version="NSEIFSC_TRADE_904 historical specification; current master unverified",
        source_document_sha256="1c5c7f43ef5dfe3060db990f3d6aac912356c0b8c5b32a9559c468b5e28625ac",
        contract_specification=(
            "NIFTY FUTIDX; historical 2022 circular specified USD 2 per index point; "
            "2025 circular revised monthly and quarterly expiries to last Tuesday, "
            "subject to holidays and later changes; current contract master required"
        ),
        expiry_rule_source="https://www.nseix.com/api/content/circulars/NSEIFSC_TRADE_2199.pdf",
        expiry_rule_document_sha256="b245b26bac5125d2010e6a8dc81364c10afb379ada891d3f1810aa198cce53b2",
        received_at=now,
        first_seen_at=now,
        config_version=CONFIG_VERSION,
        quality_reasons=[
            "no_verified_entitled_quote_provider",
            "contract_not_resolved",
            "hash_covers_availability_metadata_not_price",
        ],
        **session("NSEIX", now),
    )
    sti = MarketSnapshot(
        provider="unconfigured",
        source="https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/straits-times-index-ground-rules.pdf",
        symbol="STI",
        underlying="Straits Times Index",
        instrument_kind="cash_index",
        exchange="SGX",
        quote_unit="index_points",
        source_version="FTSE Russell STI Ground Rules v3.9 May 2026",
        source_document_sha256="1ae5f6fb6d906272660378bf748b3baadbc6b6e74215a65a79d29510d1664ff5",
        contract_specification=(
            "STI cash index: published index hours 09:00-17:10 Singapore time; "
            "no calculation on public holidays; special hours may vary"
        ),
        received_at=now,
        first_seen_at=now,
        config_version=CONFIG_VERSION,
        quality_reasons=[
            "no_verified_licensed_sti_quote_provider",
            "sti_special_sessions_may_be_unverified",
            "hash_covers_availability_metadata_not_price",
        ],
        **sti_session(now),
    )
    return [_availability_record(gift), _availability_record(sti)]
