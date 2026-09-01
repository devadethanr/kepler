from __future__ import annotations

from datetime import datetime, timezone, tzinfo
from typing import Any

UTC = timezone.utc


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def parse_datetime_utc(value: Any, *, naive_timezone: tzinfo = UTC) -> datetime:
    """Parse a timestamp and normalize legacy naive values to aware UTC."""
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC)
