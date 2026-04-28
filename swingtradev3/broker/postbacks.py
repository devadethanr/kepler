from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any


def compute_postback_checksum(order_id: str, order_timestamp: str, api_secret: str) -> str:
    payload = f"{order_id}{order_timestamp}{api_secret}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_postback_checksum(payload: dict[str, Any], api_secret: str | None = None) -> bool:
    secret = (api_secret or os.getenv("KITE_API_SECRET", "")).strip()
    if not secret:
        raise RuntimeError("KITE_API_SECRET is required to verify Kite postbacks")
    order_id = str(payload.get("order_id") or "").strip()
    order_timestamp = str(payload.get("order_timestamp") or "").strip()
    checksum = str(payload.get("checksum") or "").strip()
    if not order_id or not order_timestamp or not checksum:
        return False
    expected = compute_postback_checksum(order_id, order_timestamp, secret)
    return hmac.compare_digest(expected, checksum)
