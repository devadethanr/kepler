"""AccountState sub-repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from paths import CONTEXT_DIR

from ..models import AccountState, PositionState
from .. import models as models_module


IST = ZoneInfo("Asia/Kolkata")
PRIMARY_ACCOUNT_KEY = "primary"


class AccountRepository:
    """Account state and position CRUD."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── helpers ──────────────────────────────────────────────────────

    def _sync_account_state_position_payload(
        self,
        *,
        position_id: str,
        updater,
    ) -> None:
        row = self.session.get(models_module.AccountStateRow, PRIMARY_ACCOUNT_KEY)
        if row is None:
            return

        payload = dict(row.payload or {})
        positions = list(payload.get("positions") or [])
        updated = False
        next_positions: list[dict[str, Any]] = []
        for item in positions:
            position_payload = dict(item or {})
            ticker = str(position_payload.get("ticker") or "").upper()
            if ticker == position_id.upper():
                position_payload = updater(position_payload)
                updated = True
            next_positions.append(position_payload)

        if updated:
            payload["positions"] = next_positions
            row.payload = payload

    # ── public API ───────────────────────────────────────────────────

    def account_state_exists(self) -> bool:
        return self.session.get(models_module.AccountStateRow, PRIMARY_ACCOUNT_KEY) is not None

    def get_account_state_payload(self) -> dict[str, Any]:
        row = self.session.get(models_module.AccountStateRow, PRIMARY_ACCOUNT_KEY)
        if row is None:
            return AccountState().model_dump(mode="json")
        return dict(row.payload)

    def replace_account_state(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        state = AccountState.model_validate(payload or {})
        normalized = state.model_dump(mode="json")

        row = self.session.get(models_module.AccountStateRow, PRIMARY_ACCOUNT_KEY)
        if row is None:
            row = models_module.AccountStateRow(account_key=PRIMARY_ACCOUNT_KEY)
            self.session.add(row)

        row.cash_inr = state.cash_inr
        row.realized_pnl = state.realized_pnl
        row.unrealized_pnl = state.unrealized_pnl
        row.drawdown_pct = state.drawdown_pct
        row.weekly_loss_pct = state.weekly_loss_pct
        row.consecutive_losses = state.consecutive_losses
        row.payload = normalized

        existing_positions = {
            str(position.ticker).upper(): position
            for position in self.session.scalars(select(models_module.PositionRow)).all()
        }
        seen_tickers: set[str] = set()

        for position in state.positions:
            self._upsert_position(position, existing_positions)
            seen_tickers.add(position.ticker.upper())

        for ticker, row_position in existing_positions.items():
            if ticker not in seen_tickers:
                self.session.delete(row_position)

        from .events import EventRepository
        EventRepository(self.session).append_execution_event(
            event_type="account_state_replaced",
            entity_type="account_state",
            entity_id=PRIMARY_ACCOUNT_KEY,
            source=source,
            payload={
                "positions": len(state.positions),
                "cash_inr": state.cash_inr,
            },
        )
        return normalized

    def _upsert_position(
        self,
        position: PositionState,
        existing_positions: dict[str, models_module.PositionRow],
    ) -> None:
        ticker_key = position.ticker.upper()
        row = existing_positions.get(ticker_key)
        if row is None:
            row = models_module.PositionRow(position_id=ticker_key, ticker=position.ticker)
            existing_positions[ticker_key] = row
            self.session.add(row)

        row.ticker = position.ticker
        row.state = position.lifecycle_state
        row.quantity = position.quantity
        row.entry_price = position.entry_price
        row.stop_price = position.stop_price
        row.target_price = position.target_price
        row.opened_at = position.opened_at
        row.payload = position.model_dump(mode="json")