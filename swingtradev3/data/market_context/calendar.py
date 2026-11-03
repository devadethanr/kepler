"""Conservative exchange calendars; unknown dates and special sessions fail closed.

SGX market phases here describe *securities trading*, not index calculation.
NSE IX has announced a 05:00 open from 2026-10-26; the complete new
schedule and special-session hours require confirmation before classification.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SGX_VERSION = "sgx-securities-2026-mom-2025-06-16"
GIFT_VERSION = "nseix-2026-holidays-schedule-unconfirmed"
STI_VERSION = "ftse-sti-ground-rules-v3.9-2026-calendar-partial"
SGX_HOLIDAYS = frozenset(
    date.fromisoformat(d)
    for d in (
        "2026-01-01",
        "2026-02-17",
        "2026-02-18",
        "2026-04-03",
        "2026-05-01",
        "2026-05-27",
        "2026-06-01",
        "2026-08-10",
        "2026-11-09",
        "2026-12-25",
    )
)
SGX_HALF_DAYS = frozenset(
    date.fromisoformat(d)
    for d in (
        "2026-02-16",
        "2026-12-24",
        "2026-12-31",
    )
)
GIFT_HOLIDAYS = frozenset((date(2026, 1, 26), date(2026, 10, 2)))


def session(venue: str, at: datetime) -> dict:
    """Return locally derived session; no assertion of live exchange status."""
    if at.tzinfo is None or at.utcoffset() is None:
        return {
            "market_state": "unknown",
            "market_date": None,
            "session_id": None,
            "calendar_version": None,
            "timezone": None,
        }
    if venue == "SGX":
        local = at.astimezone(ZoneInfo("Asia/Singapore"))
        day, clock = local.date(), local.time().replace(tzinfo=None)
        state, phase = "unknown", None
        if day.year == 2026:
            if day.weekday() >= 5 or day in SGX_HOLIDAYS:
                state, phase = "closed", "holiday_or_weekend"
            elif time(9) <= clock < time(12):
                state, phase = "open", "securities_morning"
            elif day in SGX_HALF_DAYS:
                state, phase = (
                    ("unknown", "closing_auction")
                    if time(12) <= clock < time(12, 16)
                    else ("closed", "outside_trading")
                )
            elif time(12) <= clock < time(13):
                state, phase = "break", "securities_midday"
            elif time(13) <= clock < time(17):
                state, phase = "open", "securities_afternoon"
            elif time(17) <= clock < time(17, 16):
                state, phase = "unknown", "closing_auction"
            else:
                state, phase = "closed", "outside_trading"
        return {
            "market_state": state,
            "market_date": day.isoformat(),
            "session_id": phase,
            "calendar_version": SGX_VERSION,
            "timezone": "Asia/Singapore",
        }
    if venue == "NSEIX":
        local = at.astimezone(ZoneInfo("Asia/Kolkata"))
        # The revised complete schedule and its overnight business-date rule are
        # not verified. Even a local holiday can overlap a prior session.
        phase = "muhurat_timing_unverified" if local.date() == date(2026, 11, 8) else None
        return {
            "market_state": "unknown",
            "market_date": None,
            "session_id": phase,
            "calendar_version": GIFT_VERSION,
            "timezone": "Asia/Kolkata",
        }
    return {
        "market_state": "unknown",
        "market_date": None,
        "session_id": None,
        "calendar_version": None,
        "timezone": None,
    }


def sti_session(at: datetime) -> dict:
    """STI calculation hours, distinct from the SGX securities trading phases.

    Coverage is limited to known 2026 holidays and half-days. Unscheduled special
    hours cannot be established by this static calendar and require confirmation.
    """
    if at.tzinfo is None or at.utcoffset() is None:
        return {
            "market_state": "unknown",
            "market_date": None,
            "session_id": None,
            "calendar_version": None,
            "timezone": None,
        }
    local = at.astimezone(ZoneInfo("Asia/Singapore"))
    day, clock = local.date(), local.time().replace(tzinfo=None)
    state, phase = "unknown", "calendar_coverage_unknown"
    if day.year == 2026:
        if day in SGX_HALF_DAYS:
            phase = "special_hours_unverified"
        elif day.weekday() >= 5 or day in SGX_HOLIDAYS:
            state, phase = "closed", "holiday_or_weekend"
        elif time(9) <= clock < time(17, 10):
            state, phase = "open", "sti_calculation"
        else:
            state, phase = "closed", "outside_sti_calculation"
    return {
        "market_state": state,
        "market_date": day.isoformat(),
        "session_id": phase,
        "calendar_version": STI_VERSION,
        "timezone": "Asia/Singapore",
    }


def last_completed_sti_close(cutoff: datetime) -> datetime | None:
    """Return a known ordinary STI close; fail closed on uncertain special days."""
    if cutoff.tzinfo is None or cutoff.utcoffset() is None:
        return None
    local = cutoff.astimezone(ZoneInfo("Asia/Singapore"))
    day = local.date()
    while day.year == 2026:
        if day in SGX_HALF_DAYS:
            return None
        if day.weekday() < 5 and day not in SGX_HOLIDAYS:
            close = datetime.combine(day, time(17, 10), tzinfo=local.tzinfo)
            if close <= local:
                return close
        day -= timedelta(days=1)
    return None
