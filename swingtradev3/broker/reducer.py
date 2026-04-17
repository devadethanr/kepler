from __future__ import annotations

from datetime import datetime
from typing import Any

from models import AccountState, PositionState
from memory.db import session_scope
from memory.repositories import MemoryRepository

from .kite_rest import fetch_gtts, fetch_holdings, fetch_orders, fetch_positions
from .types import (
    BrokerOrderEvent,
    BrokerPositionSnapshot,
    normalize_status,
    normalize_kite_gtt_event,
    normalize_kite_order_event,
    normalize_kite_position_snapshots,
)


TRACKED_ORDER_STATUSES = {
    "open",
    "open_pending",
    "modify_pending",
    "modify_validation_pending",
    "trigger_pending",
    "cancel_pending",
    "put_order_req_received",
    "after_market_order_req_received",
    "validation_pending",
}


def _to_datetime(value: object, fallback: datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return fallback
    return fallback


class BrokerReducer:
    def apply_order_update(self, payload: dict[str, Any], *, source: str) -> dict[str, Any]:
        event = normalize_kite_order_event(payload)
        if not event.broker_order_id:
            return {"status": "ignored", "reason": "missing_order_id"}

        with session_scope() as session:
            repo = MemoryRepository(session)
            return self._apply_order_update(repo, event, source=source)

    def apply_orders_snapshot(self, payload: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
        applied = 0
        deduplicated = 0
        with session_scope() as session:
            repo = MemoryRepository(session)
            for item in payload:
                result = self._apply_order_update(repo, normalize_kite_order_event(item), source=source)
                if result["status"] == "applied":
                    applied += 1
                elif result["status"] == "deduplicated":
                    deduplicated += 1
        return {"status": "ok", "applied": applied, "deduplicated": deduplicated}

    def apply_gtt_snapshot(self, payload: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
        applied = 0
        deduplicated = 0
        with session_scope() as session:
            repo = MemoryRepository(session)
            for item in payload:
                event = normalize_kite_gtt_event(item)
                if not event.oco_gtt_id:
                    continue
                event_key = (
                    f"gtt:{event.oco_gtt_id}:{event.status}:{event.stop_price}:{event.target_price}:"
                    f"{event.triggered_leg_index}"
                )
                if repo.execution_event_exists(
                    event_type="broker_event_applied",
                    entity_type="broker_event",
                    entity_id=event_key,
                ):
                    deduplicated += 1
                    continue
                trigger_payload = dict(event.raw)
                trigger_payload["oco_gtt_id"] = event.oco_gtt_id
                trigger_payload["stop_price"] = event.stop_price
                trigger_payload["target_price"] = event.target_price
                trigger_payload["triggered_leg_index"] = event.triggered_leg_index
                repo.upsert_protective_trigger(
                    protective_trigger_id=event.oco_gtt_id,
                    position_id=event.ticker.upper(),
                    ticker=event.ticker,
                    status=event.status,
                    payload=trigger_payload,
                    source=source,
                )
                repo.append_execution_event(
                    event_type="broker_event_applied",
                    entity_type="broker_event",
                    entity_id=event_key,
                    source=source,
                    payload={"oco_gtt_id": event.oco_gtt_id, "status": event.status},
                )
                applied += 1
        return {"status": "ok", "applied": applied, "deduplicated": deduplicated}

    def apply_position_snapshot(
        self,
        positions_payload: dict[str, Any],
        holdings_payload: list[dict[str, Any]],
        *,
        source: str,
    ) -> dict[str, Any]:
        snapshots = normalize_kite_position_snapshots(positions_payload, holdings_payload)
        with session_scope() as session:
            repo = MemoryRepository(session)
            current_state = AccountState.model_validate(repo.get_account_state_payload())
            triggers = {
                item["ticker"].upper(): item
                for item in repo.list_protective_triggers()
                if item.get("ticker")
            }
            existing_positions = {item.ticker.upper(): item for item in current_state.positions}
            now = datetime.now()
            merged_positions = [
                self._merge_position_snapshot(
                    item,
                    existing_positions.get(item.ticker.upper()),
                    triggers.get(item.ticker.upper()),
                    now,
                )
                for item in snapshots
            ]
            next_state = current_state.model_copy(update={"positions": merged_positions})
            repo.replace_account_state(next_state.model_dump(mode="json"), source=source)
        return {"status": "ok", "positions": len(snapshots)}

    def sync_from_broker(self, *, source: str = "rest_snapshot") -> dict[str, Any]:
        started_at = datetime.now().isoformat()
        run_id = f"reconcile:{started_at}"
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_reconciliation_run(
                reconciliation_run_id=run_id,
                status="started",
                payload={"started_at": started_at, "source": source},
                source=source,
            )

        try:
            orders = fetch_orders()
            gtts = fetch_gtts()
            positions = fetch_positions()
            holdings = fetch_holdings()
            order_result = self.apply_orders_snapshot(orders, source=source)
            gtt_result = self.apply_gtt_snapshot(gtts, source=source)
            position_result = self.apply_position_snapshot(positions, holdings, source=source)
            tracked_tickers = sorted(self._tracked_tickers(orders, positions, holdings))
        except Exception as exc:
            with session_scope() as session:
                repo = MemoryRepository(session)
                repo.upsert_failure_incident(
                    incident_id="broker_sync",
                    status="open",
                    severity="warning",
                    payload={"detail": str(exc), "source": source, "at": datetime.now().isoformat()},
                    source=source,
                )
                repo.upsert_reconciliation_run(
                    reconciliation_run_id=run_id,
                    status="failed",
                    payload={"started_at": started_at, "source": source, "error": str(exc)},
                    source=source,
                )
            raise

        completed_payload = {
            "started_at": started_at,
            "completed_at": datetime.now().isoformat(),
            "source": source,
            "orders": order_result,
            "gtts": gtt_result,
            "positions": position_result,
            "tracked_tickers": tracked_tickers,
        }
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_reconciliation_run(
                reconciliation_run_id=run_id,
                status="completed",
                payload=completed_payload,
                source=source,
            )
            repo.upsert_failure_incident(
                incident_id="broker_sync",
                status="resolved",
                severity="warning",
                payload={"source": source, "resolved_at": datetime.now().isoformat()},
                source=source,
            )
        return completed_payload

    def _apply_order_update(
        self,
        repo: MemoryRepository,
        event: BrokerOrderEvent,
        *,
        source: str,
    ) -> dict[str, Any]:
        event_key = event.event_key()
        if repo.execution_event_exists(
            event_type="broker_event_applied",
            entity_type="broker_event",
            entity_id=event_key,
        ):
            return {"status": "deduplicated", "event_key": event_key}

        previous = repo.get_broker_order(event.broker_order_id)
        repo.upsert_broker_order(
            broker_order_id=event.broker_order_id,
            exchange_order_id=event.exchange_order_id,
            ticker=event.ticker,
            status=event.status,
            broker_tag=event.broker_tag,
            payload=dict(event.raw),
            source=source,
        )

        previous_payload = previous["payload"] if previous else {}
        previous_filled = int(previous_payload.get("filled_quantity") or 0)
        fill_id = event.fill_id(previous_filled)
        if fill_id and event.average_price is not None:
            repo.upsert_broker_fill(
                fill_id=fill_id,
                broker_order_id=event.broker_order_id,
                ticker=event.ticker,
                quantity=max(event.filled_quantity - previous_filled, 0),
                fill_price=event.average_price,
                payload={
                    "average_price": event.average_price,
                    "filled_quantity": event.filled_quantity,
                    "previous_filled_quantity": previous_filled,
                    "occurred_at": event.occurred_at,
                    "raw": dict(event.raw),
                },
                source=source,
            )

        repo.append_execution_event(
            event_type="broker_event_applied",
            entity_type="broker_event",
            entity_id=event_key,
            source=source,
            payload={
                "broker_order_id": event.broker_order_id,
                "status": event.status,
                "filled_quantity": event.filled_quantity,
                "broker_tag": event.broker_tag,
            },
        )
        return {"status": "applied", "event_key": event_key}

    def _tracked_tickers(
        self,
        orders: list[dict[str, Any]],
        positions_payload: dict[str, Any],
        holdings_payload: list[dict[str, Any]],
    ) -> set[str]:
        tracked = {
            snapshot.ticker
            for snapshot in normalize_kite_position_snapshots(positions_payload, holdings_payload)
        }
        for order in orders:
            status = normalize_status(order.get("status"))
            ticker = str(order.get("tradingsymbol") or "").strip().upper()
            if ticker and status in TRACKED_ORDER_STATUSES:
                tracked.add(ticker)
        return tracked

    def _merge_position_snapshot(
        self,
        snapshot: BrokerPositionSnapshot,
        existing: PositionState | None,
        trigger: dict[str, Any] | None,
        now: datetime,
    ) -> PositionState:
        trigger_payload = trigger["payload"] if trigger else {}
        gtt_id = trigger["protective_trigger_id"] if trigger else None
        stop_price = float(
            trigger_payload.get("stop_price")
            or (existing.stop_price if existing is not None else 0.0)
            or 0.0
        )
        target_price = float(
            trigger_payload.get("target_price")
            or (existing.target_price if existing is not None else 0.0)
            or 0.0
        )
        entry_price = snapshot.average_price or (existing.entry_price if existing is not None else 0.0)
        opened_at = existing.opened_at if existing is not None else now
        position_kwargs: dict[str, Any] = {
            "ticker": snapshot.ticker,
            "quantity": snapshot.quantity,
            "entry_price": entry_price,
            "current_price": snapshot.current_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "opened_at": _to_datetime(opened_at, now),
            "entry_order_id": existing.entry_order_id if existing is not None else None,
            "oco_gtt_id": gtt_id or (existing.oco_gtt_id if existing is not None else None),
            "stop_gtt_id": gtt_id or (existing.stop_gtt_id if existing is not None else None),
            "target_gtt_id": gtt_id or (existing.target_gtt_id if existing is not None else None),
            "thesis_score": existing.thesis_score if existing is not None else None,
            "research_date": existing.research_date if existing is not None else None,
            "skill_version": existing.skill_version if existing is not None else None,
            "sector": existing.sector if existing is not None else None,
        }
        if existing is not None:
            position_kwargs["pending_corporate_action"] = existing.pending_corporate_action

        return PositionState(
            **position_kwargs,
        )
