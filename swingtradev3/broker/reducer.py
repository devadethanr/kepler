from __future__ import annotations

from datetime import datetime
from typing import Any

from models import AccountState, PositionState
from memory.db import session_scope
from memory.repositories import MemoryRepository

from .kite_rest import fetch_gtts, fetch_holdings, fetch_order_trades, fetch_orders, fetch_positions
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
                    f"{event.triggered_leg_index}:{event.exit_order_id}:{event.exit_order_status}"
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
                trigger_payload["triggered_leg"] = event.triggered_leg
                trigger_payload["exit_order_id"] = event.exit_order_id
                trigger_payload["exit_exchange_order_id"] = event.exit_exchange_order_id
                trigger_payload["exit_order_status"] = event.exit_order_status
                trigger_payload["exit_rejection_reason"] = event.exit_rejection_reason
                trigger_payload["broker_status"] = event.status
                trigger_row_status = event.status
                if event.status == "triggered":
                    if event.exit_order_status == "complete":
                        trigger_row_status = "exit_filled"
                    elif event.exit_order_status not in (None, "", "failed", "rejected", "cancelled"):
                        trigger_row_status = "exit_order_open"
                elif event.status in {"cancelled", "deleted", "disabled", "expired"}:
                    trigger_row_status = event.status
                repo.upsert_protective_trigger(
                    protective_trigger_id=event.oco_gtt_id,
                    position_id=event.ticker.upper(),
                    ticker=event.ticker,
                    status=trigger_row_status,
                    payload=trigger_payload,
                    source=source,
                )
                repo.append_execution_event(
                    event_type="broker_event_applied",
                    entity_type="broker_event",
                    entity_id=event_key,
                    source=source,
                    payload={
                        "oco_gtt_id": event.oco_gtt_id,
                        "status": trigger_row_status,
                        "broker_status": event.status,
                        "exit_order_id": event.exit_order_id,
                        "exit_order_status": event.exit_order_status,
                    },
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
            triggers: dict[str, dict[str, Any]] = {}
            for item in repo.list_protective_triggers():
                ticker = str(item.get("ticker") or "").upper()
                if not ticker:
                    continue
                existing = triggers.get(ticker)
                if existing is None:
                    triggers[ticker] = item
                    continue
                if str(existing.get("status") or "").strip().lower() == "active":
                    continue
                if str(item.get("status") or "").strip().lower() == "active":
                    triggers[ticker] = item
            existing_positions = {item.ticker.upper(): item for item in current_state.positions}
            now = datetime.now()
            reconciled_intents = {
                item.ticker.upper(): self._reconcile_order_intent_from_position_snapshot(
                    repo,
                    item,
                    existing_positions.get(item.ticker.upper()),
                    triggers.get(item.ticker.upper()),
                    source=source,
                    now=now,
                )
                for item in snapshots
            }
            merged_positions = [
                self._merge_position_snapshot(
                    item,
                    existing_positions.get(item.ticker.upper()),
                    triggers.get(item.ticker.upper()),
                    reconciled_intents.get(item.ticker.upper()),
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
        matched_intent = (
            repo.get_order_intent_by_broker_tag(event.broker_tag)
            if event.broker_tag
            else None
        )
        order_intent_id = (
            str(matched_intent["order_intent_id"])
            if matched_intent is not None
            else str(previous["order_intent_id"])
            if previous is not None and previous.get("order_intent_id")
            else None
        )
        repo.upsert_broker_order(
            broker_order_id=event.broker_order_id,
            exchange_order_id=event.exchange_order_id,
            ticker=event.ticker,
            order_intent_id=order_intent_id,
            status=event.status,
            broker_tag=event.broker_tag,
            payload={**dict(event.raw), "order_intent_id": order_intent_id},
            source=source,
        )

        previous_payload = previous["payload"] if previous else {}
        previous_filled = int(previous_payload.get("filled_quantity") or 0)
        if matched_intent is not None:
            intent_payload = {
                **dict(matched_intent["payload"]),
                "broker_order_id": event.broker_order_id,
                "exchange_order_id": event.exchange_order_id,
                "broker_order_status": event.status,
            }
            repo.upsert_order_intent(
                order_intent_id=str(matched_intent["order_intent_id"]),
                ticker=str(matched_intent["ticker"]),
                status=str(matched_intent["status"]),
                approval_id=matched_intent.get("approval_id"),
                entry_intent_id=matched_intent.get("entry_intent_id"),
                broker_order_id=event.broker_order_id,
                broker_tag=event.broker_tag or matched_intent.get("broker_tag"),
                payload=intent_payload,
                source=source,
            )
        self._persist_order_fills(
            repo,
            event,
            previous_filled_quantity=previous_filled,
            order_intent_id=order_intent_id,
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

    def _persist_order_fills(
        self,
        repo: MemoryRepository,
        event: BrokerOrderEvent,
        *,
        previous_filled_quantity: int,
        order_intent_id: str | None,
        source: str,
    ) -> None:
        if event.filled_quantity <= previous_filled_quantity:
            return

        persisted = False
        try:
            trades = fetch_order_trades(event.broker_order_id)
        except Exception:
            trades = []

        for trade in trades:
            if not isinstance(trade, dict):
                continue
            trade_order_id = str(trade.get("order_id") or "").strip()
            trade_id = str(trade.get("trade_id") or "").strip()
            quantity = int(trade.get("quantity") or trade.get("filled") or 0)
            fill_price = float(trade.get("average_price") or 0.0)
            if trade_order_id and trade_order_id != event.broker_order_id:
                continue
            if not trade_id or quantity <= 0 or fill_price <= 0:
                continue
            repo.upsert_broker_fill(
                fill_id=trade_id,
                broker_order_id=event.broker_order_id,
                order_intent_id=order_intent_id,
                ticker=event.ticker,
                quantity=quantity,
                fill_price=fill_price,
                payload={
                    "trade_id": trade_id,
                    "fill_timestamp": trade.get("fill_timestamp"),
                    "exchange_timestamp": trade.get("exchange_timestamp"),
                    "order_timestamp": trade.get("order_timestamp"),
                    "raw": dict(trade),
                },
                source=source,
            )
            persisted = True

        if persisted:
            return

        fill_id = event.fill_id(previous_filled_quantity)
        if fill_id is None or event.average_price is None:
            return

        repo.upsert_broker_fill(
            fill_id=fill_id,
            broker_order_id=event.broker_order_id,
            order_intent_id=order_intent_id,
            ticker=event.ticker,
            quantity=max(event.filled_quantity - previous_filled_quantity, 0),
            fill_price=event.average_price,
            payload={
                "average_price": event.average_price,
                "filled_quantity": event.filled_quantity,
                "previous_filled_quantity": previous_filled_quantity,
                "occurred_at": event.occurred_at,
                "raw": dict(event.raw),
            },
            source=source,
        )

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
        intent: dict[str, Any] | None,
        now: datetime,
    ) -> PositionState:
        trigger_payload = trigger["payload"] if trigger else {}
        intent_payload = intent["payload"] if intent else {}
        gtt_id = trigger["protective_trigger_id"] if trigger else None
        stop_price = float(
            trigger_payload.get("stop_price")
            or (existing.stop_price if existing is not None else 0.0)
            or intent_payload.get("stop_price")
            or 0.0
        )
        target_price = float(
            trigger_payload.get("target_price")
            or (existing.target_price if existing is not None else 0.0)
            or intent_payload.get("target_price")
            or 0.0
        )
        entry_price = (
            snapshot.average_price
            or (existing.entry_price if existing is not None else 0.0)
            or float(intent_payload.get("average_price") or 0.0)
            or float(((intent_payload.get("entry_zone") or {}).get("high")) or 0.0)
        )
        opened_at = (
            existing.opened_at
            if existing is not None
            else _to_datetime(
                intent_payload.get("submitted_at")
                or intent_payload.get("position_materialized_at")
                or intent_payload.get("created_at"),
                now,
            )
        )
        position_kwargs: dict[str, Any] = {
            "ticker": snapshot.ticker,
            "quantity": snapshot.quantity,
            "entry_price": entry_price,
            "current_price": snapshot.current_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "opened_at": _to_datetime(opened_at, now),
            "entry_order_id": (
                existing.entry_order_id
                if existing is not None
                else str(
                    (intent or {}).get("broker_order_id") or intent_payload.get("broker_order_id") or ""
                )
                or None
            ),
            "oco_gtt_id": gtt_id or (existing.oco_gtt_id if existing is not None else None),
            "lifecycle_state": (
                existing.lifecycle_state
                if existing is not None
                else "open"
            ),
            "thesis_score": (
                existing.thesis_score
                if existing is not None
                else float(intent_payload.get("score"))
                if intent_payload.get("score") not in (None, "")
                else None
            ),
            "research_date": (
                existing.research_date if existing is not None else intent_payload.get("research_date")
            ),
            "skill_version": (
                existing.skill_version if existing is not None else intent_payload.get("skill_version")
            ),
            "sector": existing.sector if existing is not None else intent_payload.get("sector"),
        }
        if existing is not None:
            position_kwargs["pending_corporate_action"] = existing.pending_corporate_action

        return PositionState(
            **position_kwargs,
        )

    def _reconcile_order_intent_from_position_snapshot(
        self,
        repo: MemoryRepository,
        snapshot: BrokerPositionSnapshot,
        existing: PositionState | None,
        trigger: dict[str, Any] | None,
        *,
        source: str,
        now: datetime,
    ) -> dict[str, Any] | None:
        intents = repo.list_order_intents_for_ticker(snapshot.ticker)
        intent = next(
            (
                item
                for item in intents
                if str(item["status"]).strip().lower() not in {"failed", "cancelled", "expired"}
            ),
            None,
        )
        if intent is None:
            return None

        current_status = str(intent["status"]).strip().lower()
        if trigger is not None and str(trigger.get("status") or "").strip().lower() == "active":
            next_status = "protected"
        elif current_status == "protected":
            next_status = "protection_pending"
        elif current_status in {"entry_filled", "protection_pending"}:
            next_status = current_status
        else:
            next_status = "protection_pending"

        payload = {
            **dict(intent["payload"]),
            "broker_position_source": snapshot.source_kind,
            "broker_snapshot_reconciled_at": now.isoformat(),
            "filled_quantity": snapshot.quantity,
            "average_price": snapshot.average_price,
            "broker_position_quantity": snapshot.quantity,
            "broker_position_price": snapshot.average_price,
        }
        broker_order_id = str(intent.get("broker_order_id") or payload.get("broker_order_id") or "").strip()
        if not broker_order_id:
            orders = repo.list_broker_orders_by_tag(str(intent.get("broker_tag") or ""))
            if orders:
                broker_order_id = str(orders[0]["broker_order_id"])
                payload["broker_order_id"] = broker_order_id

        repo.upsert_order_intent(
            order_intent_id=str(intent["order_intent_id"]),
            ticker=snapshot.ticker,
            status=next_status,
            approval_id=intent.get("approval_id"),
            entry_intent_id=intent.get("entry_intent_id"),
            broker_order_id=broker_order_id or None,
            broker_tag=(
                str(intent.get("broker_tag"))
                if intent.get("broker_tag") not in (None, "")
                else None
            ),
            payload=payload,
            source=source,
        )
        return repo.get_order_intent(str(intent["order_intent_id"]))
