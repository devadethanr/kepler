"""Caller-owned transactions for immutable market observations and availability reads."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select

from data.market_context.snapshot import MarketSnapshot, assess
from memory.models import MarketObservationRow
from memory.news_snapshot import _utc

SCOPES = ("gift_nifty", "singapore_sti", "nifty_cash")


def stored_utc(session, value):
    """SQLite drops timezone metadata from our already-validated UTC DB columns."""
    if value is not None and value.tzinfo is None and session.bind.dialect.name == "sqlite":
        value = value.replace(tzinfo=timezone.utc)
    return _utc(value) if value is not None else None


class MarketSnapshotRepository:
    def __init__(self, session):
        self.session = session

    def record(self, scope, observation, *, observed_at=None):
        """Pin server availability; provider timestamps cannot backdate availability."""
        if scope not in SCOPES:
            raise ValueError("Unknown market context scope")
        observed_at = _utc(observed_at or datetime.now(timezone.utc))
        raw = dict(observation)
        raw.update(snapshot_id=None, first_seen_at=observed_at.isoformat())
        item = MarketSnapshot.model_validate(raw).model_dump(mode="json")
        if _utc(item["received_at"]) > observed_at:
            raise ValueError("Receipt is later than recorded availability")
        latest = self.session.scalar(
            select(MarketObservationRow)
            .where(MarketObservationRow.scope == scope)
            .order_by(MarketObservationRow.first_seen_at.desc())
            .limit(1)
        )
        if latest and observed_at < stored_utc(self.session, latest.first_seen_at):
            raise ValueError("Cannot retroactively insert market availability")
        prior_query = select(MarketObservationRow).where(
            MarketObservationRow.scope == scope,
            MarketObservationRow.first_seen_at <= observed_at,
            MarketObservationRow.payload["status"].as_string().not_in(("invalid", "unavailable")),
            MarketObservationRow.payload["exchange_asof"].as_string().is_not(None),
        )
        for key in ("provider", "instrument_id", "contract", "expiry", "symbol"):
            field = MarketObservationRow.payload[key].as_string()
            prior_query = prior_query.where(
                field == item[key] if item[key] is not None else field.is_(None)
            )
        previous = self.session.scalar(
            prior_query.order_by(MarketObservationRow.first_seen_at.desc()).limit(1)
        )
        prior = MarketSnapshot.model_validate(previous.payload) if previous else None
        item = assess(
            MarketSnapshot.model_validate(item),
            now=observed_at,
            stale_after_seconds=300,
            previous=prior,
        ).model_dump(mode="json")
        item["scope"] = scope
        digest = hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()
        item["snapshot_id"] = digest
        existing = self.session.get(MarketObservationRow, digest)
        if existing:
            if existing.payload != item:
                raise ValueError("Immutable snapshot identity mismatch")
            return dict(existing.payload)
        if latest and observed_at == stored_utc(self.session, latest.first_seen_at):
            raise ValueError("Conflicting observations at identical availability time")
        self.session.add(
            MarketObservationRow(
                snapshot_id=digest,
                scope=scope,
                provider=item["provider"],
                first_seen_at=observed_at,
                payload=item,
            )
        )
        self.session.flush()
        return item

    def latest(self, scope, *, cutoff, snapshot_ids=None):
        if scope not in SCOPES:
            raise ValueError("Unknown market context scope")
        query = select(MarketObservationRow).where(
            MarketObservationRow.scope == scope,
            MarketObservationRow.first_seen_at <= _utc(cutoff),
        )
        if snapshot_ids is not None:
            query = query.where(MarketObservationRow.snapshot_id.in_(snapshot_ids))
        row = self.session.scalars(
            query.order_by(
                MarketObservationRow.first_seen_at.desc(), MarketObservationRow.snapshot_id.desc()
            ).limit(1)
        ).first()
        return dict(row.payload) if row else None

    def latest_refresh(self):
        value = self.session.scalar(
            select(MarketObservationRow.first_seen_at)
            .order_by(MarketObservationRow.first_seen_at.desc())
            .limit(1)
        )
        return stored_utc(self.session, value)
