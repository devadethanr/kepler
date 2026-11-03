"""Bounded saved-data market reads. No provider, broker, migration or model calls."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text

from data.market_context.calendar import (
    last_completed_sti_close,
    session as market_session,
    sti_session,
)
from data.market_context.snapshot import MarketSnapshot, assess
from memory.market_snapshot import SCOPES, MarketSnapshotRepository
from memory.news_snapshot import _utc

from .grounding import packet
from .news_evidence import read_scope


def selected_scopes(value):
    if value == "all":
        return SCOPES
    if value not in SCOPES:
        raise ValueError("Use all, gift_nifty, singapore_sti or nifty_cash")
    return (value,)


def unavailable(scope, reason):
    """No synthetic observation/time is substituted for absent saved history."""
    symbol, kind, exchange = {
        "gift_nifty": ("GIFT Nifty", "future", "NSEIX"),
        "singapore_sti": ("STI", "cash_index", "SGX"),
        "nifty_cash": ("NIFTY 50", "cash_index", "NSE"),
    }[scope]
    return {
        "scope": scope,
        "snapshot_id": None,
        "provider": "unavailable",
        "symbol": symbol,
        "instrument_kind": kind,
        "exchange": exchange,
        "status": "unavailable",
        "market_state": "unknown",
        "quote_value": None,
        "received_at": None,
        "first_seen_at": None,
        "exchange_asof": None,
        "provider_asof": None,
        "delay_seconds": None,
        "quality_reasons": [reason],
        "basis": None,
    }


class MarketEvidence:
    def __init__(self, room=None, scope=read_scope, *, stale_after_seconds=300):
        self.room, self.scope = room, scope
        self.options = (room or {}).get("evidence_scope") or {}
        pinned = self.options.get("cutoff") or (room or {}).get("source_cutoff")
        if room is not None and not pinned:
            raise ValueError("Legacy room lacks a pinned cutoff; start a linked room")
        self.maximum = _utc(pinned) if pinned else datetime.now(timezone.utc)
        self.stale_after_seconds = stale_after_seconds

    def read(self, selection="all", cutoff=""):
        cutoff = _utc(cutoff) if cutoff else self.maximum
        if cutoff > self.maximum:
            raise ValueError("Market cutoff exceeds the room's pinned availability")
        allowed_scopes = self.options.get("market_scopes", SCOPES)
        scopes = selected_scopes(selection)
        if set(scopes) - set(allowed_scopes):
            raise ValueError("Market scope is outside this room's selected inputs")
        observations = []
        with self.scope() as session:
            if session.bind.dialect.name == "postgresql":
                session.execute(text("SET LOCAL statement_timeout = '3000ms'"))
            repo = MarketSnapshotRepository(session)
            for scope in scopes:
                item = repo.latest(
                    scope, cutoff=cutoff, snapshot_ids=self.options.get("market_snapshot_ids")
                )
                if item is None:
                    item = unavailable(scope, "no_saved_observation_available_by_cutoff")
                else:
                    saved_status = item["status"]
                    # STI calculation is distinct from SGX securities phases. GIFT
                    # schedule remains unknown until the effective circular is pinned.
                    state_at_cutoff = market_session(item.get("exchange"), cutoff)["market_state"]
                    if scope == "singapore_sti":
                        state_at_cutoff = sti_session(cutoff)["market_state"]
                    if scope == "nifty_cash":
                        state_at_cutoff = "unknown"
                    assessed = assess(
                        MarketSnapshot.model_validate(item),
                        now=cutoff,
                        stale_after_seconds=self.stale_after_seconds,
                        market_state_at_cutoff=state_at_cutoff,
                        last_completed_close_at=last_completed_sti_close(cutoff)
                        if scope == "singapore_sti"
                        else None,
                    )
                    item = {
                        **item,
                        "saved_status": saved_status,
                        "status": assessed.status,
                        "quality_reasons": assessed.quality_reasons,
                        "assessment_basis": "exchange age and separately derived cutoff session; saved body unchanged",
                        "market_state_at_cutoff": state_at_cutoff,
                    }
                    age = (cutoff - _utc(item["first_seen_at"])).total_seconds()
                    item["observation_age_seconds"] = age
                    if age > self.stale_after_seconds:
                        item["quality_reasons"] = list(
                            dict.fromkeys(
                                [*item["quality_reasons"], "collector_observation_not_recent"]
                            )
                        )
                    item["availability"] = "observed_by_cutoff"
                item["requested_cutoff"] = cutoff.isoformat()
                observations.append(item)
        result = {
            "as_of": cutoff.isoformat(),
            "cutoff": cutoff.isoformat(),
            "observations": observations,
            "coverage": "saved observations only; no historical backfill or implied quote entitlement",
            "limits": {
                "observation_limit": 3,
                "network_requests": 0,
                "stale_after_seconds": self.stale_after_seconds,
                "refresh": "explicit collector; reads never fetch",
                "authority": "descriptive context; no opening-gap prediction, causal proof or trading authority",
            },
        }
        if self.room:
            result["evidence"] = [self._packet(item, cutoff) for item in observations]
        return result

    def _packet(self, item, cutoff):
        # The service summary is explicitly derived metadata, never a provider quotation.
        lines = [
            f"Instrument: {item['symbol']} ({item['instrument_kind']}); venue {item['exchange']}.",
            f"Provider: {item['provider']}; quote status: {item['status']}.",
            f"Quote: {item.get('quote_value')}; unit: {item.get('quote_unit')}; delay seconds: {item.get('delay_seconds')}.",
            f"Exchange time: {item.get('exchange_asof')}; received: {item.get('received_at')}.",
            f"Session at observation: {item.get('session_id')}; state: {item['market_state']}.",
            "Quality reasons: " + ", ".join(item["quality_reasons"]) + ".",
            "A futures/cash spread is not a predicted opening gap; STI does not establish causality.",
        ]
        result = packet(
            self.room["target"],
            "market:" + item["scope"],
            "\n".join(lines),
            record_id=item.get("snapshot_id"),
            decision_cutoff=cutoff.isoformat(),
            source_type="derived_market_observation_summary",
            status="ok",
            delay=item.get("delay_seconds"),
            retrieval={
                "scope": item["scope"],
                "network_requests": 0,
                "completeness": "one latest saved observation; not full market coverage",
            },
        )
        result["market_snapshot"] = item
        result["authority"] = (
            "recorded observation metadata; not a verbatim exchange quote or interpretation verification"
        )
        return result
