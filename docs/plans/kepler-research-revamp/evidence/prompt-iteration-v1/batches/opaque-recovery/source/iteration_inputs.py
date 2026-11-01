"""Evidence projection for offline input-style experiments.

Citation admissibility checks provenance and time metadata, not semantic relevance or truth.
"""

from __future__ import annotations

from .grounding import validate_claims


def compact_evidence(evidence: dict, target: str) -> dict:
    """Project existing packets without deriving claims or discarding source records."""
    sources = []
    options = []
    allowed = [""]
    for evidence_id, item in evidence.items():
        spans = item.get("quote_spans", [])
        sources.append(
            {
                "text": item.get("text"),
                "evidence_id": evidence_id,
                "source": item.get("source"),
                "source_type": item.get("source_type"),
                "record_id": item.get("record_id"),
                "source_event_id": item.get("event_id"),
                "status": item.get("status"),
                "published_at": item.get("published_at"),
                "event_at": item.get("event_at"),
                "fetched_at": item.get("fetched_at"),
                "decision_cutoff": item.get("decision_cutoff"),
                "adjustment": item.get("adjustment"),
                "delay": item.get("delay"),
                "metadata_policy": item.get("metadata_policy"),
                "retrieval": item.get("retrieval"),
                "truncated": item.get("truncated"),
                "quote_spans_truncated": item.get("quote_spans_truncated"),
            }
        )
        for span in spans:
            quote_id = span["id"]
            try:
                validate_claims(target, [{"evidence_id": evidence_id, "quote": quote_id}], evidence)
            except ValueError as exc:
                admissible = False
                reason = str(exc)
            else:
                admissible = True
                reason = "Citation metadata admissible; semantic relevance unassessed"
                if quote_id not in allowed:
                    allowed.append(quote_id)
            options.append(
                {
                    "quote_id": quote_id,
                    "text": span["text"],
                    "source": item.get("source"),
                    "source_event_id": item.get("event_id"),
                    "admissible": admissible,
                    "reason": reason,
                }
            )
    return {
        "sources": sources,
        "quote_options": options,
        "allowed_quote_ids": allowed,
        "requested_scope": {
            "label": target,
            "meaning": "requested scope; source relevance unverified",
        },
    }
