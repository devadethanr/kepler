"""Phase 7: shared Kite auth-freshness helper.

Single source of truth for "is the broker session safe to transact with right
now". Reused by:

- ``execution.reconciler._check_auth_freshness`` — periodic runtime loop
- ``execution.coordinator.submit_order_intent`` — per-order preflight
- ``api.tasks.scheduler._auth_preflight`` — pre-market (08:50) refresh job

Reads ``auth_sessions.payload.created_at`` (or ``login_time``) and compares
against ``cfg.execution.reconciliation.auth_max_age_hours``. Returns a tuple
``(fresh, reason_if_stale, age_hours)``.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from auth.kite.client import has_kite_session
from config import cfg
from memory.db import session_scope
from memory.repository import MemoryRepository


IST = ZoneInfo("Asia/Kolkata")


def _now() -> datetime:
    return datetime.now(IST)


def _max_age_hours(override: Optional[float] = None) -> float:
    if override is not None:
        return float(override)
    return float(cfg.execution.reconciliation.auth_max_age_hours)


def read_auth_session_age_hours() -> Optional[float]:
    """Return the current session age in hours, or None if no timestamp found."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_auth_session_payload()
    if not payload:
        return None
    created_at_raw = payload.get("created_at") or payload.get("login_time")
    if not created_at_raw:
        return None
    try:
        created_at = datetime.fromisoformat(str(created_at_raw))
    except (TypeError, ValueError):
        return None
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=IST)
    else:
        created_at = created_at.astimezone(IST)
    delta = _now() - created_at
    return delta.total_seconds() / 3600.0


def is_session_fresh(
    *,
    max_age_hours: Optional[float] = None,
) -> tuple[bool, Optional[str], Optional[float]]:
    """Check whether the Kite session is present AND within ``max_age_hours``.

    Returns ``(fresh, reason, age_hours)``:
    - ``fresh`` is False on missing session, missing timestamp, unparseable
      timestamp, or age > threshold.
    - ``reason`` is a short machine-friendly token (``missing`` / ``stale``)
      when ``fresh`` is False; ``None`` when fresh.
    - ``age_hours`` is the session age when determinable, else ``None``.
    """
    if not has_kite_session():
        return False, "missing", None

    age_hours = read_auth_session_age_hours()
    if age_hours is None:
        # Session present but we can't prove freshness — treat as missing for safety.
        return False, "missing_timestamp", None

    threshold = _max_age_hours(max_age_hours)
    if age_hours > threshold:
        return False, "stale", age_hours
    return True, None, age_hours
