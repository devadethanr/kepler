"""Classify an explicitly marked model admission failure for one Codex turn.

A generic HTTP 429 is insufficient: the server or another limit may also emit it.
The marker must survive the Codex protocol; if it does not, leave the failure
unclassified rather than substituting stale budget state.
"""

from __future__ import annotations

import re
from typing import Any

from .store import RoomStopped


BUDGET_DENIAL_MARKER = "kepler_budget_exhausted"
_MARKER = re.compile(r"(?<![A-Za-z0-9_])kepler_budget_exhausted(?![A-Za-z0-9_])")


def _has_marker(value: Any, depth: int = 0) -> bool:
    if depth > 8:
        return False
    if isinstance(value, str):
        return _MARKER.search(value) is not None
    if isinstance(value, dict):
        return any(_has_marker(v, depth + 1) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_has_marker(v, depth + 1) for v in value)
    return False


def classify_model_admission_error(
    error: Any, *, role: str, turn: int, denial: dict[str, Any] | None
) -> RoomStopped | None:
    """Return a typed limit only for a marked error and the matching recorded turn."""
    if not role or type(turn) is not int or turn < 1 or not isinstance(denial, dict):
        return None
    if (
        denial.get("kind") != "model"
        or denial.get("code") != "call_limit"
        or denial.get("role") != role
        or denial.get("turn") != turn
    ):
        return None
    reason = denial.get("reason")
    if not isinstance(reason, str) or not reason or not _has_marker(error):
        return None
    return RoomStopped(reason, "call_limit")
