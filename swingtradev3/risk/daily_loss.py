"""Phase 7 (P3): Realized-daily-loss threshold computation.

Sums realized PnL for trades closed today (IST) and compares against equity.
Used by the reconciler's ``run_daily_loss_loop`` to trip the
``daily_loss_limit`` kill switch and ``exit_only_mode`` when breached.

Realized-only by design — unrealized PnL on open positions is already
throttled by trailing stops and GTTs; gating on unrealized would double-count
and cause spurious flaps on normal intraday wiggles.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select

from config import cfg
from memory.db import session_scope
from memory.models import TradeRow
from memory.repository import MemoryRepository
from models import AccountState


# IST is UTC+5:30 — the exchange runs 09:15-15:30 IST.
_IST_OFFSET = timedelta(hours=5, minutes=30)


def _ist_day_bounds(now_utc: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Return the [start, end) UTC bounds covering the current IST trading day."""
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    ist_now = now_utc.astimezone(timezone(_IST_OFFSET))
    ist_day_start = datetime.combine(ist_now.date(), time.min, tzinfo=timezone(_IST_OFFSET))
    ist_day_end = ist_day_start + timedelta(days=1)
    return ist_day_start.astimezone(timezone.utc), ist_day_end.astimezone(timezone.utc)


def compute_realized_pnl_today(*, now_utc: Optional[datetime] = None) -> float:
    start, end = _ist_day_bounds(now_utc)
    with session_scope() as session:
        rows = session.scalars(
            select(TradeRow).where(
                TradeRow.closed_at_effective >= start,
                TradeRow.closed_at_effective < end,
            )
        ).all()
        return float(sum(row.pnl_abs for row in rows))


def _estimate_equity(state: AccountState) -> float:
    """Rough total equity: cash + mark-to-market of open positions.

    ``current_price`` may be None on a freshly bootstrapped position — fall
    back to entry_price so we never report a zero denominator.
    """
    position_value = 0.0
    for position in state.positions:
        price = position.current_price if position.current_price else position.entry_price
        position_value += float(price or 0.0) * int(position.quantity)
    return float(state.cash_inr) + position_value


def daily_loss_snapshot(*, now_utc: Optional[datetime] = None) -> Optional[dict[str, Any]]:
    """Return the current realized daily-loss state or None when we lack data.

    Output keys:
    - ``realized_pnl``   (float, negative = loss)
    - ``equity``         (float)
    - ``loss_pct``       (float, positive = loss as fraction of equity)
    - ``threshold_pct``  (float, from config)
    - ``breached``       (bool)
    - ``as_of``          (ISO timestamp UTC)
    """
    with session_scope() as session:
        repo = MemoryRepository(session)
        payload = repo.get_account_state_payload()
    state = AccountState.model_validate(payload or {})
    equity = _estimate_equity(state)
    if equity <= 0:
        return None

    realized = compute_realized_pnl_today(now_utc=now_utc)
    # realized < 0 is a loss. loss_pct is positive when in the red.
    loss_pct = -realized / equity if realized < 0 else 0.0
    threshold_pct = float(cfg.risk.max_daily_loss_pct)
    breached = loss_pct >= threshold_pct

    return {
        "realized_pnl": realized,
        "equity": equity,
        "loss_pct": loss_pct,
        "threshold_pct": threshold_pct,
        "breached": breached,
        "as_of": (now_utc or datetime.now(timezone.utc)).isoformat(),
    }


def daily_loss_exceeded(*, equity: float, realized_pnl: float) -> tuple[bool, float]:
    """Pure helper for unit testing.

    Returns ``(breached, loss_pct)``. ``loss_pct`` is 0 when PnL is positive.
    """
    if equity <= 0:
        return False, 0.0
    loss_pct = -realized_pnl / equity if realized_pnl < 0 else 0.0
    threshold_pct = float(cfg.risk.max_daily_loss_pct)
    return loss_pct >= threshold_pct, loss_pct
