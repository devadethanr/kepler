"""Position sub-repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models as models_module
from .events import EventRepository


IST = ZoneInfo("Asia/Kolkata")


class PositionRepository:
    """Position state management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_positions(self, *, states: set[str] | None = None) -> list[dict[str, Any]]:
        query = select(models_module.PositionRow).order_by(
            models_module.PositionRow.ticker.asc()
        )
        if states is not None:
            normalized = [str(s).lower() for s in states]
            query = query.where(models_module.PositionRow.state.in_(normalized))
        rows = self.session.scalars(query).all()
        return [
            {
                "position_id": row.position_id,
                "ticker": row.ticker,
                "state": row.state,
                "quantity": row.quantity,
                "entry_price": row.entry_price,
                "stop_price": row.stop_price,
                "target_price": row.target_price,
                "opened_at": row.opened_at,
                "payload": dict(row.payload),
            }
            for row in rows
        ]

    def get_position(self, position_id: str) -> dict[str, Any] | None:
        row = self.session.get(models_module.PositionRow, position_id)
        if row is None:
            return None
        return {
            "position_id": row.position_id,
            "ticker": row.ticker,
            "state": row.state,
            "quantity": row.quantity,
            "entry_price": row.entry_price,
            "stop_price": row.stop_price,
            "target_price": row.target_price,
            "opened_at": row.opened_at,
            "payload": dict(row.payload),
        }

    def update_position_state(
        self,
        *,
        position_id: str,
        new_state: str,
        source: str,
        detail: str | None = None,
    ) -> dict[str, Any] | None:
        row = self.session.get(models_module.PositionRow, position_id)
        if row is None:
            return None

        previous_state = row.state
        if previous_state == new_state:
            return {
                "position_id": row.position_id,
                "ticker": row.ticker,
                "state": row.state,
                "quantity": row.quantity,
                "entry_price": row.entry_price,
                "stop_price": row.stop_price,
                "target_price": row.target_price,
                "opened_at": row.opened_at,
                "payload": dict(row.payload),
            }

        row.state = new_state
        payload = dict(row.payload or {})
        payload["lifecycle_state"] = new_state
        if detail:
            payload["reconcile_detail"] = detail
        row.payload = payload

        from .account import AccountRepository

        AccountRepository(self.session)._sync_account_state_position_payload(
            position_id=position_id,
            updater=lambda item: {
                **item,
                "lifecycle_state": new_state,
                **({"reconcile_detail": detail} if detail else {}),
            },
        )

        EventRepository(self.session).append_execution_event(
            event_type="position_state_changed",
            entity_type="position",
            entity_id=position_id,
            source=source,
            payload={
                "ticker": row.ticker,
                "previous_state": previous_state,
                "new_state": new_state,
                "detail": detail,
            },
        )
        return {
            "position_id": row.position_id,
            "ticker": row.ticker,
            "state": row.state,
            "quantity": row.quantity,
            "entry_price": row.entry_price,
            "stop_price": row.stop_price,
            "target_price": row.target_price,
            "opened_at": row.opened_at,
            "payload": dict(row.payload),
        }

    def update_position_price(
        self,
        *,
        position_id: str,
        current_price: float,
        source: str,
    ) -> dict[str, Any] | None:
        row = self.session.get(models_module.PositionRow, position_id)
        if row is None:
            return None
        payload = dict(row.payload or {})
        updated_at = datetime.now(IST).isoformat()
        payload["current_price"] = current_price
        payload["price_updated_at"] = updated_at
        row.payload = payload

        from .account import AccountRepository

        AccountRepository(self.session)._sync_account_state_position_payload(
            position_id=position_id,
            updater=lambda item: {
                **item,
                "current_price": current_price,
                "price_updated_at": updated_at,
            },
        )
        return {
            "position_id": row.position_id,
            "ticker": row.ticker,
            "current_price": current_price,
            "updated_at": updated_at,
        }