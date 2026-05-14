"""Trade sub-repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import ValidationError

from ..models import TradeRecord
from .. import models as models_module
from .events import EventRepository


class TradeRepository:
    """Trade record management."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def trades_exist(self) -> bool:
        return self.session.scalars(
            select(models_module.TradeRow).limit(1)
        ).first() is not None

    def get_trades_payload(self) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(models_module.TradeRow).order_by(
                models_module.TradeRow.closed_at_effective.desc(),
                models_module.TradeRow.trade_id.asc(),
            )
        ).all()
        return [dict(row.payload) for row in rows]

    def upsert_trade(
        self,
        *,
        trade_id: str,
        ticker: str,
        quantity: int,
        entry_price: float,
        exit_price: float,
        opened_at: datetime,
        closed_at: datetime,
        pnl_abs: float,
        pnl_pct: float,
        exit_reason: str,
        payload: dict[str, Any] | None = None,
        source: str = "system",
    ) -> dict[str, Any]:
        row = self.session.get(models_module.TradeRow, trade_id)
        if row is None:
            row = models_module.TradeRow(trade_id=trade_id)
            self.session.add(row)
        row.ticker = ticker
        row.quantity = quantity
        row.entry_price = entry_price
        row.exit_price = exit_price
        row.opened_at_effective = opened_at
        row.closed_at_effective = closed_at
        row.pnl_abs = pnl_abs
        row.pnl_pct = pnl_pct
        row.exit_reason = exit_reason
        row.payload = dict(payload or {})
        EventRepository(self.session).append_execution_event(
            event_type="trade_upserted",
            entity_type="trade",
            entity_id=trade_id,
            source=source,
            payload={
                "ticker": ticker,
                "quantity": quantity,
                "pnl_abs": pnl_abs,
                "exit_reason": exit_reason,
            },
        )
        return {
            "trade_id": row.trade_id,
            "ticker": row.ticker,
            "exit_reason": row.exit_reason,
            "pnl_abs": row.pnl_abs,
        }

    def replace_trades(
        self,
        payload: Iterable[dict[str, Any]],
        *,
        source: str,
    ) -> list[dict[str, Any]]:
        existing_trade_ids = set(self.session.scalars(select(models_module.TradeRow.trade_id)).all())
        seen_trade_ids: set[str] = set()
        normalized_payload: list[dict[str, Any]] = []
        for item in payload:
            try:
                trade = TradeRecord.model_validate(item)
            except ValidationError:
                continue
            normalized = trade.model_dump(mode="json")
            row = self.session.get(models_module.TradeRow, trade.trade_id)
            if row is None:
                row = models_module.TradeRow(trade_id=trade.trade_id)
                self.session.add(row)
            row.ticker = trade.ticker
            row.quantity = trade.quantity
            row.entry_price = trade.entry_price
            row.exit_price = trade.exit_price
            row.opened_at_effective = trade.opened_at
            row.closed_at_effective = trade.closed_at
            row.pnl_abs = trade.pnl_abs
            row.pnl_pct = trade.pnl_pct
            row.exit_reason = trade.exit_reason
            row.payload = normalized
            normalized_payload.append(normalized)
            seen_trade_ids.add(trade.trade_id)

        for trade_id in existing_trade_ids - seen_trade_ids:
            row = self.session.get(models_module.TradeRow, trade_id)
            if row is not None:
                self.session.delete(row)

        EventRepository(self.session).append_execution_event(
            event_type="trades_replaced",
            entity_type="trades",
            entity_id="closed",
            source=source,
            payload={"count": len(normalized_payload)},
        )
        return normalized_payload
