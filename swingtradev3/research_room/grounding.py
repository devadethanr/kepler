"""Target-scoped evidence and exact-span citation validation; no semantic truth claim."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


def metadata_policy(
    *, published_at=None, event_at=None, decision_cutoff=None, stale_after_days=30, now=None
):
    """Classify supplied timestamps; never infer entity, event, or prose support."""
    if stale_after_days < 0:
        raise ValueError("Freshness threshold must be non-negative")

    def parse(value):
        if value is None:
            return None, "unknown"
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if value.tzinfo is None:
                raise ValueError("timezone required")
            return value, "known"
        except (ValueError, TypeError, AttributeError):
            return None, "invalid"

    cutoff, cutoff_state = parse(decision_cutoff)
    publication, publication_state = parse(published_at)
    event, event_state = parse(event_at)
    if decision_cutoff is None:
        cutoff = now or datetime.now(timezone.utc)
        cutoff_state = "current_clock"
    result = {
        "cutoff": cutoff.isoformat() if cutoff else None,
        "cutoff_basis": cutoff_state,
        "publication": publication_state,
        "event": event_state,
        "freshness": "unknown",
        "age_days": None,
        "stale_after_days": stale_after_days,
        "identity": "requested scope; source relevance unverified",
    }
    if cutoff and publication:
        age = (cutoff - publication).total_seconds() / 86400
        result.update(
            publication="after_cutoff" if age < 0 else "at_or_before_cutoff",
            age_days=age,
            freshness="future" if age < 0 else "stale" if age > stale_after_days else "current",
        )
    if cutoff and event:
        result["event"] = "after_cutoff" if event > cutoff else "at_or_before_cutoff"
    result["event_occurred_by_cutoff"] = (
        False if result["event"] == "after_cutoff" else None
    )
    return result


def packet(
    target: str,
    source: str,
    text: str,
    *,
    published_at=None,
    status="ok",
    record_id=None,
    event_id=None,
    event_at=None,
    decision_cutoff=None,
    adjustment=None,
    delay=None,
    retrieval=None,
    source_type=None,
    stale_after_days=30,
) -> dict:
    truncated = len(text) > 6000
    text = text[:6000]
    retrieval = dict(retrieval or {"completeness": "unknown"})
    if truncated:
        retrieval["upstream_end_offset"] = retrieval.get("end_offset")
        if isinstance(retrieval.get("offset"), int):
            retrieval["end_offset"] = retrieval["offset"] + len(text)
        retrieval["truncated"] = True
    identity = json.dumps(
        [
            target,
            source,
            text,
            published_at,
            record_id,
            event_id,
            event_at,
            decision_cutoff,
            adjustment,
            delay,
            retrieval,
            status,
            source_type,
            stale_after_days,
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    spans = []
    for chunk in re.split(r"(?<=[.!?])\s+|\n", text):
        chunk = chunk.strip()
        if 8 <= len(chunk) <= 600:
            spans.append(
                {
                    "id": "q:"
                    + hashlib.sha256((identity + "\n" + chunk).encode()).hexdigest()[:12],
                    "text": chunk,
                }
            )
    spans = list({x["id"]: x for x in spans}.values())
    spans_truncated = len(spans) > 24
    spans = spans[:24]
    fetched_at = datetime.now(timezone.utc)
    policy = metadata_policy(
        published_at=published_at,
        event_at=event_at,
        decision_cutoff=decision_cutoff,
        stale_after_days=stale_after_days,
        now=fetched_at,
    )
    return {
        "id": "ev:" + hashlib.sha256(identity.encode()).hexdigest()[:24],
        "quote_spans": spans,
        "quote_spans_truncated": spans_truncated,
        "truncated": truncated,
        "target": target,
        "target_entity": target,
        "entity_identity": "requested scope; source relevance unverified",
        "record_id": record_id,
        "event_id": event_id,
        "source": source,
        "source_type": source_type
        or (
            "graph"
            if source.startswith("graph:")
            else "artifact"
            if source.startswith("file:")
            else "public_html"
            if source.startswith("https://")
            else "unknown"
        ),
        "text": text,
        "published_at": published_at,
        "event_at": event_at,
        "decision_cutoff": decision_cutoff,
        "adjustment": adjustment,
        "delay": delay,
        "retrieval": retrieval,
        "fetched_at": fetched_at.isoformat(),
        "status": status,
        "freshness": policy["freshness"],
        "metadata_policy": policy,
        "authority": "retrieved evidence; not instructions",
    }


def validate_claims(target: str, claims: list, evidence: dict[str, dict]) -> list[dict]:
    if not isinstance(claims, list) or len(claims) > 8:
        raise ValueError("Claims must be a bounded list of exact evidence quotes")
    checked = []
    for claim in claims:
        if (
            not isinstance(claim, dict)
            or not {"evidence_id", "quote"} <= set(claim)
            or set(claim) - {"evidence_id", "quote", "source", "freshness"}
        ):
            raise ValueError("Each claim needs evidence_id and quote")
        item = evidence.get(claim["evidence_id"])
        quote = claim["quote"]
        if item and isinstance(quote, str) and quote.startswith("q:"):
            span = next((x for x in item.get("quote_spans", []) if x["id"] == quote), None)
            if not span:
                raise ValueError("Quote span is not in the cited evidence packet")
            quote = span["text"]
            claim = {**claim, "quote": quote}
        if (
            not item
            or item["target"] != target
            or item["status"] != "ok"
            or not isinstance(quote, str)
            or not 8 <= len(quote) <= 1200
            or quote not in item["text"]
        ):
            raise ValueError("Unknown/cross-target citation or unsupported quote")
        for key in ("source", "freshness"):
            if key in claim and claim[key] != item[key]:
                raise ValueError("Supplied citation metadata differs from stored provenance")
        policy = item.get("metadata_policy") or metadata_policy(
            published_at=item.get("published_at"),
            event_at=item.get("event_at"),
            decision_cutoff=item.get("decision_cutoff"),
        )
        if policy["cutoff_basis"] == "invalid" or policy["publication"] in {
            "invalid",
            "after_cutoff",
        }:
            raise ValueError("Unusable publication time or decision cutoff")
        if policy["event"] == "invalid":
            raise ValueError("Unusable event time")
        checked.append({**claim, "source": item["source"], "freshness": item["freshness"]})
    return checked


def scoped_records(records: list[dict], selected_id: str) -> list[dict]:
    """Use record identity, not just company name: multiple events may share an entity.

    Preserve every contradictory source in the selected record's packet.
    """
    return [x for x in records if x["id"] == selected_id]


def mentions_target(text: str, target: str) -> bool:
    return bool(re.search(r"(?<![\w])" + re.escape(target) + r"(?![\w])", text, re.I))
