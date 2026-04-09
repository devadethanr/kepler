"""
Entry Timing Tool
=================
Determines optimal entry timing for a stock.
Rule-based logic — no LLM, no decisions.

Checks:
  - Market open noise (first 30 min)
  - F&O expiry proximity
  - F&O ban status
  - Earnings proximity
  - Lunch-time volume drop
  - Late-day square-off volatility
"""
from __future__ import annotations

from datetime import datetime, time
from typing import Any

from config import cfg


def check_entry_timing(
    ticker: str,
    current_time: datetime | None = None,
    in_fno_ban: bool = False,
    earnings_within_days: int = 0,
    is_fo_expiry_week: bool = False,
) -> dict[str, Any]:
    """
    Check if now is a good time to enter a position.

    Args:
        ticker: Stock symbol
        current_time: Current datetime (defaults to now)
        in_fno_ban: Whether stock is in F&O ban
        earnings_within_days: Days until next earnings
        is_fo_expiry_week: Whether this is F&O expiry week

    Returns:
        {
            optimal: bool,
            reason: str,
            wait_minutes: int | None,
            risk_factors: list[str],
        }
    """
    now = current_time or datetime.now()
    current_time_obj = now.time()
    risk_factors: list[str] = []
    wait_minutes: int | None = None

    # Check 1: Market open noise (first 30 min: 9:15-9:45)
    market_open = time(9, 15)
    market_open_end = time(9, 45)
    if market_open <= current_time_obj <= market_open_end:
        remaining = (datetime.combine(now.date(), market_open_end) - now).total_seconds() / 60
        return {
            "optimal": False,
            "reason": "Market open noise — wait for first 30-min candle to settle",
            "wait_minutes": int(remaining),
            "risk_factors": ["opening_volatility"],
        }

    # Check 2: Late-day square-off (after 3:00 PM)
    late_day = time(15, 0)
    if current_time_obj >= late_day:
        return {
            "optimal": False,
            "reason": "Late-day square-off volatility — enter tomorrow",
            "wait_minutes": None,
            "risk_factors": ["square_off_volatility"],
        }

    # Check 3: Lunch-time volume drop (12:00-13:00)
    lunch_start = time(12, 0)
    lunch_end = time(13, 0)
    if lunch_start <= current_time_obj <= lunch_end:
        risk_factors.append("low_volume_lunch")

    # Check 4: F&O ban
    if in_fno_ban:
        risk_factors.append("fno_ban")
        return {
            "optimal": False,
            "reason": f"{ticker} is in F&O ban — avoid entry",
            "wait_minutes": None,
            "risk_factors": risk_factors,
        }

    # Check 5: Earnings proximity
    if 0 < earnings_within_days <= cfg.research.exclude_earnings_within_days:
        risk_factors.append(f"earnings_in_{earnings_within_days}_days")
        if earnings_within_days <= 2:
            return {
                "optimal": False,
                "reason": f"Earnings in {earnings_within_days} days — too risky",
                "wait_minutes": None,
                "risk_factors": risk_factors,
            }

    # Check 6: F&O expiry week
    if is_fo_expiry_week:
        risk_factors.append("fo_expiry_week")

    # Determine optimal
    if risk_factors:
        return {
            "optimal": len(risk_factors) == 1 and "low_volume_lunch" in risk_factors,
            "reason": f"Entry possible but with caution: {', '.join(risk_factors)}",
            "wait_minutes": None,
            "risk_factors": risk_factors,
        }

    return {
        "optimal": True,
        "reason": "Entry timing is favorable",
        "wait_minutes": None,
        "risk_factors": [],
    }
