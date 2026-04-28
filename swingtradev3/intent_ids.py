from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _normalized_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    entry_zone = payload.get("entry_zone") or {}
    return {
        "ticker": str(payload.get("ticker") or "").strip().upper(),
        "setup_type": str(payload.get("setup_type") or "").strip().lower(),
        "score": _to_float(payload.get("score")),
        "entry_low": _to_float(getattr(entry_zone, "get", lambda *_args, **_kwargs: None)("low")),
        "entry_high": _to_float(getattr(entry_zone, "get", lambda *_args, **_kwargs: None)("high")),
        "stop_price": _to_float(payload.get("stop_price")),
        "target_price": _to_float(payload.get("target_price")),
        "holding_days_expected": int(payload.get("holding_days_expected") or 0),
        "research_date": str(payload.get("research_date") or payload.get("scan_date") or "").strip(),
        "skill_version": str(payload.get("skill_version") or "").strip(),
    }


def candidate_fingerprint(payload: Mapping[str, Any]) -> str:
    normalized = _normalized_candidate(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:12]


def entry_intent_id(payload: Mapping[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "").strip().upper() or "UNKNOWN"
    return f"entry-intent:{ticker}:{candidate_fingerprint(payload)}"


def order_intent_id(payload: Mapping[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "").strip().upper() or "UNKNOWN"
    return f"order-intent:{ticker}:{candidate_fingerprint(payload)}"


def approval_id(payload: Mapping[str, Any]) -> str:
    ticker = str(payload.get("ticker") or "").strip().upper() or "UNKNOWN"
    return f"approval:{ticker}:{candidate_fingerprint(payload)}"
