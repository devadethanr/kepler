from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: object) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_status(value: object) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    return text.replace(" ", "_")


def _best_timestamp(payload: dict[str, Any]) -> str | None:
    for key in (
        "exchange_update_timestamp",
        "exchange_timestamp",
        "order_timestamp",
        "fill_timestamp",
        "timestamp",
    ):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _normalize_gtt_status(payload: dict[str, Any]) -> tuple[str, int | None]:
    status = normalize_status(payload.get("status"))
    if status == "active":
        return "active", None
    if status in {"cancelled", "deleted", "disabled", "expired", "rejected"}:
        return "cancelled", None
    if status != "triggered":
        return status, None

    orders = payload.get("orders") or []
    if isinstance(orders, list):
        for index, item in enumerate(orders):
            if not isinstance(item, dict):
                continue
            result = item.get("result") or item.get("order_result")
            if result:
                return ("triggered_stop" if index == 0 else "triggered_target"), index
    return "triggered", None


@dataclass(slots=True)
class BrokerOrderEvent:
    broker_order_id: str
    exchange_order_id: str | None
    broker_tag: str | None
    ticker: str
    exchange: str
    side: str
    status: str
    quantity: int
    filled_quantity: int
    pending_quantity: int
    cancelled_quantity: int
    average_price: float | None
    price: float | None
    trigger_price: float | None
    product: str | None
    order_type: str | None
    variety: str | None
    occurred_at: str | None
    raw: dict[str, Any]

    def event_key(self) -> str:
        timestamp = self.occurred_at or "na"
        return (
            f"{self.broker_order_id}:{self.status}:{self.filled_quantity}:"
            f"{self.pending_quantity}:{timestamp}"
        )

    def fill_id(self, previous_filled_quantity: int) -> str | None:
        if self.filled_quantity <= previous_filled_quantity:
            return None
        timestamp = self.occurred_at or "na"
        return f"{self.broker_order_id}:{self.filled_quantity}:{timestamp}"


@dataclass(slots=True)
class BrokerProtectiveTriggerEvent:
    oco_gtt_id: str
    ticker: str
    status: str
    stop_price: float
    target_price: float
    triggered_leg_index: int | None
    raw: dict[str, Any]


@dataclass(slots=True)
class BrokerPositionSnapshot:
    ticker: str
    quantity: int
    average_price: float
    current_price: float | None
    source_kind: str
    raw: dict[str, Any]


@dataclass(slots=True)
class BrokerQuoteTick:
    instrument_token: int
    last_price: float
    last_trade_time: datetime | None
    raw: dict[str, Any]


def normalize_kite_order_event(payload: dict[str, Any]) -> BrokerOrderEvent:
    return BrokerOrderEvent(
        broker_order_id=str(payload.get("order_id") or ""),
        exchange_order_id=(
            str(payload["exchange_order_id"])
            if payload.get("exchange_order_id") not in (None, "")
            else None
        ),
        broker_tag=str(payload["tag"]) if payload.get("tag") not in (None, "") else None,
        ticker=str(payload.get("tradingsymbol") or ""),
        exchange=str(payload.get("exchange") or ""),
        side=str(payload.get("transaction_type") or "").lower(),
        status=normalize_status(payload.get("status")),
        quantity=_to_int(payload.get("quantity")),
        filled_quantity=_to_int(payload.get("filled_quantity")),
        pending_quantity=_to_int(payload.get("pending_quantity") or payload.get("unfilled_quantity")),
        cancelled_quantity=_to_int(payload.get("cancelled_quantity")),
        average_price=_to_float(payload.get("average_price")),
        price=_to_float(payload.get("price")),
        trigger_price=_to_float(payload.get("trigger_price")),
        product=str(payload["product"]) if payload.get("product") else None,
        order_type=str(payload["order_type"]) if payload.get("order_type") else None,
        variety=str(payload["variety"]) if payload.get("variety") else None,
        occurred_at=_best_timestamp(payload),
        raw=dict(payload),
    )


def normalize_kite_gtt_event(payload: dict[str, Any]) -> BrokerProtectiveTriggerEvent:
    trigger_id = str(payload.get("id") or payload.get("trigger_id") or "")
    condition = payload.get("condition") or {}
    orders = payload.get("orders") or []
    trigger_values = condition.get("trigger_values") or []
    stop_price = float(trigger_values[0]) if trigger_values else 0.0
    target_price = float(trigger_values[1]) if len(trigger_values) > 1 else stop_price
    ticker = str(
        payload.get("tradingsymbol")
        or condition.get("tradingsymbol")
        or (orders[0].get("tradingsymbol") if isinstance(orders, list) and orders else "")
    )
    status, triggered_leg_index = _normalize_gtt_status(dict(payload))
    return BrokerProtectiveTriggerEvent(
        oco_gtt_id=trigger_id,
        ticker=ticker,
        status=status,
        stop_price=stop_price,
        target_price=target_price,
        triggered_leg_index=triggered_leg_index,
        raw=dict(payload),
    )


def normalize_kite_position_snapshots(
    positions_payload: dict[str, Any],
    holdings_payload: list[dict[str, Any]],
) -> list[BrokerPositionSnapshot]:
    snapshots: list[BrokerPositionSnapshot] = []
    seen_tickers: set[str] = set()

    net_positions = positions_payload.get("net", [])
    if isinstance(net_positions, list):
        for row in net_positions:
            if not isinstance(row, dict):
                continue
            quantity = _to_int(row.get("quantity"))
            if quantity <= 0:
                continue
            ticker = str(row.get("tradingsymbol") or "").strip().upper()
            if not ticker:
                continue
            snapshots.append(
                BrokerPositionSnapshot(
                    ticker=ticker,
                    quantity=quantity,
                    average_price=_to_float(row.get("average_price")) or 0.0,
                    current_price=_to_float(row.get("last_price")),
                    source_kind="position",
                    raw=dict(row),
                )
            )
            seen_tickers.add(ticker)

    for row in holdings_payload:
        quantity = _to_int(row.get("quantity")) + _to_int(row.get("t1_quantity"))
        if quantity <= 0:
            continue
        ticker = str(row.get("tradingsymbol") or "").strip().upper()
        if not ticker or ticker in seen_tickers:
            continue
        snapshots.append(
            BrokerPositionSnapshot(
                ticker=ticker,
                quantity=quantity,
                average_price=_to_float(row.get("average_price")) or 0.0,
                current_price=_to_float(row.get("last_price")),
                source_kind="holding",
                raw=dict(row),
            )
        )
        seen_tickers.add(ticker)

    return snapshots
