from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo


IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    return datetime.now(IST)


def iso(value: Any | None = None) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    else:
        parsed = now_ist()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST).isoformat()


def payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(payload_json(payload).encode("utf-8")).hexdigest()


def clean_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", ":", "."} else "_" for ch in value)


def label_for(properties: dict[str, Any], labels: list[str]) -> str:
    for key in ("label", "ticker", "name", "title", "event_type", "id"):
        value = properties.get(key)
        if value:
            text = str(value)
            return text if len(text) <= 80 else f"{text[:77]}..."
    return labels[0] if labels else "Node"


def ticker_list(value: Any) -> list[str]:
    if not value:
        return []
    values = value if isinstance(value, list) else [value]
    tickers: list[str] = []
    for item in values:
        ticker = str(item or "").strip().upper()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return tickers
