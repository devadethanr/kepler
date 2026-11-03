"""Typed, JSON-serializable market observations, independent of broker access."""

from datetime import date, datetime, timezone
from math import isfinite
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class MarketSnapshot(BaseModel):
    schema_version: Literal["market_context.snapshot.v1"] = "market_context.snapshot.v1"
    snapshot_id: str | None = None
    provider: str
    source: str | None = None
    instrument_id: str | None = None
    symbol: str
    underlying: str | None = None
    instrument_kind: Literal["cash_index", "future", "proxy", "unknown"] = "unknown"
    exchange: str | None = None
    contract: str | None = None
    expiry: date | None = None
    quote_value: float | None = None
    quote_unit: Literal["index_points"] | None = None
    quote_basis: Literal["last_quote", "last_completed_session_close", "unknown"] = "unknown"
    settlement_currency: str | None = None
    exchange_asof: datetime | None = None
    provider_asof: datetime | None = None
    received_at: datetime
    first_seen_at: datetime
    market_date: date | None = None
    session_id: str | None = None
    market_state: Literal["open", "closed", "break", "unknown"] = "unknown"
    timezone: str | None = None
    delay_seconds: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    status: Literal["ok", "partial", "stale", "unavailable", "invalid"] = "unavailable"
    quality_reasons: list[str] = Field(default_factory=list)
    reference_value: float | None = None
    reference_asof: datetime | None = None
    basis: str | None = None
    source_version: str | None = None
    source_document_sha256: str | None = None
    config_version: str | None = None
    calendar_version: str | None = None
    raw_observation_hash: str | None = None
    contract_multiplier_usd_per_point: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    contract_specification: str | None = None
    expiry_rule_source: str | None = None
    expiry_rule_document_sha256: str | None = None

    @field_validator(
        "received_at", "first_seen_at", "exchange_asof", "provider_asof", "reference_asof"
    )
    @classmethod
    def aware_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamps must include a timezone")
            return value.astimezone(timezone.utc)
        return None

    @field_validator("quote_value", "reference_value")
    @classmethod
    def valid_price(cls, value: float | None) -> float | None:
        if value is not None and (not isfinite(value) or value <= 0):
            raise ValueError("value must be finite and positive")
        return value

    @model_validator(mode="after")
    def coherent(self):
        if self.first_seen_at < self.received_at:
            raise ValueError("first_seen_at cannot precede received_at")
        if self.quote_value is None and self.status not in ("unavailable", "invalid"):
            raise ValueError("a missing quote cannot have a usable status")
        if self.quote_value is not None and self.quote_unit is None:
            raise ValueError("quote unit is required when a quote is present")
        if self.instrument_kind == "future" and self.quote_value is not None:
            if not self.contract or not self.expiry:
                raise ValueError("future quotes require an identified contract and expiry")
            if self.market_date is None:
                raise ValueError("future quotes require a verified market date")
            if self.expiry < self.market_date:
                raise ValueError("future quote is after its expiry")
        if self.reference_value is not None and (not self.reference_asof or not self.basis):
            raise ValueError("reference requires timestamp and explicit basis")
        if self.status == "ok" and (not self.exchange_asof or self.delay_seconds is None):
            raise ValueError("ok requires exchange time and known delay")
        for value in (self.exchange_asof, self.provider_asof, self.reference_asof):
            if value and value > self.received_at:
                raise ValueError("source timestamps cannot be after receipt")
        return self


def assess(
    snapshot: MarketSnapshot,
    *,
    now: datetime,
    stale_after_seconds: float,
    previous: MarketSnapshot | None = None,
    market_state_at_cutoff: Literal["open", "closed", "break", "unknown"] | None = None,
    last_completed_close_at: datetime | None = None,
) -> MarketSnapshot:
    """Assess at a cutoff; callers reading later must supply its session state.

    If omitted, the saved observation state is assumed to apply at the cutoff.
    An unknown cutoff state must be passed explicitly when the calendar is uncertain.
    """
    if now.tzinfo is None or now.utcoffset() is None or stale_after_seconds < 0:
        raise ValueError("aware time and non-negative stale threshold required")
    if last_completed_close_at is not None and (
        last_completed_close_at.tzinfo is None
        or last_completed_close_at.utcoffset() is None
        or last_completed_close_at > now
    ):
        raise ValueError("last completed close must be timezone-aware and no later than cutoff")
    if snapshot.received_at > now or snapshot.first_seen_at > now:
        raise ValueError("observation not yet available")
    if snapshot.quote_value is None or snapshot.status in ("invalid", "unavailable"):
        return snapshot
    reasons = list(snapshot.quality_reasons)
    status = snapshot.status
    state = market_state_at_cutoff if market_state_at_cutoff is not None else snapshot.market_state
    if (
        previous
        and previous.provider == snapshot.provider
        and previous.instrument_id == snapshot.instrument_id
        and previous.symbol == snapshot.symbol
        and previous.contract == snapshot.contract
        and previous.exchange_asof
        and snapshot.exchange_asof
        and snapshot.exchange_asof < previous.exchange_asof
    ):
        status = "invalid"
        reasons.append("out_of_order_exchange_time")
    elif snapshot.exchange_asof is None:
        status = "partial"
        reasons.append("exchange_time_unknown")
    elif state == "open" and (now - snapshot.exchange_asof).total_seconds() > (
        stale_after_seconds + (snapshot.delay_seconds or 0)
    ):
        status = "stale"
        reasons.append("open_market_quote_stale")
    elif state == "closed" and (
        snapshot.quote_basis != "last_completed_session_close"
        or last_completed_close_at is None
        or snapshot.exchange_asof != last_completed_close_at
    ):
        if status == "ok":
            status = "partial"
        reasons.append("closed_reference_unverified")
    if snapshot.delay_seconds is None:
        if status == "ok":
            status = "partial"
        reasons.append("delay_unknown")
    if state == "unknown":
        if status == "ok":
            status = "partial"
        reasons.append("market_session_unknown")
        if (
            snapshot.exchange_asof
            and (now - snapshot.exchange_asof).total_seconds() > stale_after_seconds
        ):
            reasons.append("quote_age_exceeds_threshold_session_unknown")
    if snapshot.delay_seconds:
        reasons.append("provider_delay_reported")
    return snapshot.model_copy(
        update={"status": status, "quality_reasons": list(dict.fromkeys(reasons))}
    )
