from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
from zoneinfo import ZoneInfo

IST_ZONE = "Asia/Kolkata"
IST = ZoneInfo(IST_ZONE)
MINUTES_PER_DAY = 24 * 60

# NSE Capital Market trading holidays for 2026. Keep this small and explicit:
# it is an operational guardrail, not a substitute for an exchange-calendar feed.
NSE_TRADING_HOLIDAYS_2026: dict[date, str] = {
    date(2026, 1, 15): "Municipal Corporation Election in Maharashtra",
    date(2026, 1, 26): "Republic Day",
    date(2026, 3, 3): "Holi",
    date(2026, 3, 26): "Shri Ram Navami",
    date(2026, 3, 31): "Shri Mahavir Jayanti",
    date(2026, 4, 3): "Good Friday",
    date(2026, 4, 14): "Dr. Baba Saheb Ambedkar Jayanti",
    date(2026, 5, 1): "Maharashtra Day",
    date(2026, 5, 28): "Bakri Id",
    date(2026, 6, 26): "Muharram",
    date(2026, 9, 14): "Ganesh Chaturthi",
    date(2026, 10, 2): "Mahatma Gandhi Jayanti",
    date(2026, 10, 20): "Dussehra",
    date(2026, 11, 10): "Diwali-Balipratipada",
    date(2026, 11, 24): "Prakash Gurpurb Sri Guru Nanak Dev",
    date(2026, 12, 25): "Christmas",
}

NSE_SPECIAL_TRADING_DAYS_2026: dict[date, str] = {
    date(2026, 2, 1): "Union Budget live trading session",
}


@dataclass(frozen=True)
class SessionSegment:
    key: str
    label: str
    start: dt_time
    end: dt_time


SESSION_SEGMENTS: tuple[SessionSegment, ...] = (
    SessionSegment("overnight_monitoring", "Overnight", dt_time(22, 0), dt_time(6, 0)),
    SessionSegment("pre_market_prep", "Pre-Market", dt_time(6, 0), dt_time(9, 15)),
    SessionSegment("market_hours", "Market", dt_time(9, 15), dt_time(15, 30)),
    SessionSegment("post_market", "Post", dt_time(15, 30), dt_time(18, 0)),
    SessionSegment("evening_research", "Research", dt_time(18, 0), dt_time(21, 0)),
    SessionSegment("wind_down", "Wind", dt_time(21, 0), dt_time(22, 0)),
)

PHASE_LABELS = {
    "overnight_monitoring": "Overnight",
    "pre_market_prep": "Pre-Market",
    "market_hours": "Market Active",
    "market_closed": "Market Closed",
    "post_market": "Post-Market",
    "evening_research": "Evening Research",
    "wind_down": "Wind-Down",
}


def now_ist() -> datetime:
    return datetime.now(IST)


def _minute_of_day(value: dt_time) -> int:
    return value.hour * 60 + value.minute


def _duration_minutes(start: dt_time, end: dt_time) -> int:
    start_minute = _minute_of_day(start)
    end_minute = _minute_of_day(end)
    return (end_minute - start_minute) % MINUTES_PER_DAY or MINUTES_PER_DAY


def _contains_time(segment: SessionSegment, current: dt_time) -> bool:
    start = _minute_of_day(segment.start)
    end = _minute_of_day(segment.end)
    now = _minute_of_day(current)
    if start < end:
        return start <= now < end
    return now >= start or now < end


def _elapsed_pct(segment: SessionSegment, current: dt_time) -> float:
    start = _minute_of_day(segment.start)
    now = _minute_of_day(current)
    elapsed = (now - start) % MINUTES_PER_DAY
    duration = _duration_minutes(segment.start, segment.end)
    return round(min(max(elapsed / duration, 0.0), 1.0) * 100.0, 2)


def holiday_name(day: date) -> str | None:
    if day.year == 2026:
        return NSE_TRADING_HOLIDAYS_2026.get(day)
    return None


def is_trading_day(moment: datetime | date | None = None) -> bool:
    value = moment or now_ist()
    day = value if isinstance(value, date) and not isinstance(value, datetime) else value.date()
    if day.year == 2026 and day in NSE_SPECIAL_TRADING_DAYS_2026:
        return True
    return day.weekday() < 5 and holiday_name(day) is None


def phase_for_time(current: dt_time) -> str:
    for segment in SESSION_SEGMENTS:
        if _contains_time(segment, current):
            return segment.key
    return "overnight_monitoring"


def market_status(moment: datetime | None = None) -> str:
    current = moment.astimezone(IST) if moment else now_ist()
    if not is_trading_day(current):
        return "closed"
    current_time = current.time()
    if dt_time(9, 0) <= current_time < dt_time(9, 15):
        return "pre_open"
    if dt_time(9, 15) <= current_time < dt_time(15, 30):
        return "open"
    if dt_time(15, 30) <= current_time < dt_time(16, 0):
        return "closing"
    return "closed"


def session_snapshot(moment: datetime | None = None) -> dict:
    current = moment.astimezone(IST) if moment else now_ist()
    wallclock_phase = phase_for_time(current.time())
    trading_day = is_trading_day(current)
    status = market_status(current)
    current_phase = (
        "market_closed"
        if not trading_day and wallclock_phase in {"pre_market_prep", "market_hours"}
        else wallclock_phase
    )
    holiday = holiday_name(current.date())

    segments = []
    for segment in SESSION_SEGMENTS:
        active = segment.key == wallclock_phase
        duration = _duration_minutes(segment.start, segment.end)
        segments.append(
            {
                "key": segment.key,
                "label": segment.label,
                "start": segment.start.strftime("%H:%M"),
                "end": segment.end.strftime("%H:%M"),
                "duration_minutes": duration,
                "width_pct": round((duration / MINUTES_PER_DAY) * 100.0, 2),
                "active": active,
                "elapsed_pct": _elapsed_pct(segment, current.time()) if active else 0.0,
            }
        )

    return {
        "timezone": IST_ZONE,
        "current_time": current.isoformat(),
        "trading_day": trading_day,
        "holiday": holiday,
        "market_status": status,
        "current_phase": current_phase,
        "wallclock_phase": wallclock_phase,
        "phase_label": PHASE_LABELS.get(current_phase, current_phase),
        "day_label": "T-0" if trading_day else "CLOSED",
        "segments": segments,
    }
