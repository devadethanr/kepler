from __future__ import annotations

from datetime import datetime

from api.tasks.session_phase import is_trading_day, market_status, now_ist


ENTRY_STREAM_REQUIRED_STATUSES = {"pre_open", "open"}


def entry_stream_required_for_new_entries(moment: datetime | None = None) -> bool:
    """Return True when live entry submission needs fresh broker stream state."""
    current = moment or now_ist()
    return is_trading_day(current) and market_status(current) in ENTRY_STREAM_REQUIRED_STATUSES
