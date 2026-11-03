"""Explicit bounded availability refresh, independent of trading and inference.

No quote provider has yet passed local entitlement/retention qualification. This
hook saves that fact; it never attempts hidden broker login or provider fallback.
"""

from datetime import datetime, timezone

from sqlalchemy import text

from data.market_context.collector import collect
from data.market_context.snapshot import MarketSnapshot
from memory.db import get_session_factory
from memory.market_snapshot import MarketSnapshotRepository
from memory.news_snapshot import _utc

MIN_REFRESH_SECONDS = 60


def refresh(*, cancelled=None, factory=None):
    if cancelled is not None and cancelled.is_set():
        return {"status": "cancelled", "network_requests": 0, "snapshots": []}
    factory = factory or get_session_factory()
    with factory() as session, session.begin():
        if session.bind.dialect.name == "postgresql":
            session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            locked = session.scalar(text("SELECT pg_try_advisory_xact_lock(7011030009)"))
            if not locked:
                return {"status": "busy", "network_requests": 0, "snapshots": []}
        repo = MarketSnapshotRepository(session)
        now = datetime.now(timezone.utc)
        latest = repo.latest_refresh()
        if latest and (now - _utc(latest)).total_seconds() < MIN_REFRESH_SECONDS:
            return {"status": "rate_limited", "network_requests": 0, "snapshots": []}
        observations = collect(now)
        if cancelled is not None and cancelled.is_set():
            return {"status": "cancelled", "network_requests": 0, "snapshots": []}
        scopes = ("gift_nifty", "singapore_sti")
        saved = [repo.record(scope, item) for scope, item in zip(scopes, observations, strict=True)]
        reference = MarketSnapshot(
            provider="unconfigured",
            source="https://kite.trade/docs/connect/v3/market-quotes/",
            symbol="NIFTY 50",
            underlying="NIFTY 50",
            exchange="NSE",
            instrument_kind="cash_index",
            quote_unit="index_points",
            timezone="Asia/Kolkata",
            received_at=now,
            first_seen_at=now,
            config_version="availability-only-v1",
            quality_reasons=["no_verified_entitled_nifty_reference"],
        ).model_dump(mode="json")
        saved.append(repo.record("nifty_cash", reference))
    return {
        "status": "recorded_unavailable",
        "network_requests": 0,
        "minimum_refresh_seconds": MIN_REFRESH_SECONDS,
        "snapshots": saved,
    }
