"""Target-scoped evidence and exact-span citation validation; no semantic truth claim."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone


def packet(target: str, source: str, text: str, *, published_at=None, status="ok") -> dict:
    truncated = len(text) > 6000
    text = text[:6000]
    identity = json.dumps([target, source, text, published_at], ensure_ascii=False)
    spans = []
    for chunk in re.split(r"(?<=[.!?])\s+|\n", text):
        chunk = chunk.strip()
        if 8 <= len(chunk) <= 600:
            spans.append(
                {
                    "id": "q:" + hashlib.sha256((source + "\n" + chunk).encode()).hexdigest()[:12],
                    "text": chunk,
                }
            )
    spans = list({x["id"]: x for x in spans}.values())[:24]
    return {
        "id": "ev:" + hashlib.sha256(identity.encode()).hexdigest()[:24],
        "quote_spans": spans,
        "truncated": truncated,
        "target": target,
        "source": source,
        "text": text,
        "published_at": published_at,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "freshness": "unknown" if not published_at else "observed",
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
        # Evidence carrying a known future publication time cannot support a present claim.
        if item.get("published_at"):
            try:
                when = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                if when.tzinfo is None or when > datetime.now(timezone.utc):
                    raise ValueError("Future or timezone-unknown evidence")
            except (TypeError, ValueError) as exc:
                raise ValueError("Unusable publication time") from exc
        checked.append({**claim, "source": item["source"], "freshness": item["freshness"]})
    return checked


def scoped_records(records: list[dict], selected_id: str) -> list[dict]:
    """Use record identity, not just company name: multiple events may share an entity.

    Preserve every contradictory source in the selected record's packet.
    """
    return [x for x in records if x["id"] == selected_id]


def mentions_target(text: str, target: str) -> bool:
    return bool(re.search(r"(?<![\w])" + re.escape(target) + r"(?![\w])", text, re.I))
