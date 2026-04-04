from __future__ import annotations

from dataclasses import dataclass

from models import GTTOrder


@dataclass
class GTTTriggerResult:
    position_id: str
    ticker: str
    exit_reason: str
    trigger_price: float


class GTTSimulator:
    def __init__(self) -> None:
        self._orders: dict[str, GTTOrder] = {}

    def place(self, position_id: str, ticker: str, stop_price: float, target_price: float) -> GTTOrder:
        order = GTTOrder(position_id=position_id, ticker=ticker, stop_price=stop_price, target_price=target_price)
        self._orders[position_id] = order
        return order

    def modify_stop(self, position_id: str, new_stop_price: float) -> GTTOrder:
        order = self._orders[position_id]
        order.stop_price = new_stop_price
        self._orders[position_id] = order
        return order

    def cancel(self, position_id: str) -> None:
        if position_id in self._orders:
            self._orders[position_id].status = "cancelled"

    def get(self, position_id: str) -> GTTOrder | None:
        return self._orders.get(position_id)

    def all(self) -> dict[str, GTTOrder]:
        return dict(self._orders)

    def process_candle(
        self,
        position_id: str,
        candle_low: float,
        candle_high: float,
    ) -> GTTTriggerResult | None:
        order = self._orders.get(position_id)
        if order is None or order.status != "active":
            return None
        if candle_low <= order.stop_price:
            order.status = "triggered_stop"
            return GTTTriggerResult(position_id, order.ticker, "stop_loss", order.stop_price)
        if candle_high >= order.target_price:
            order.status = "triggered_target"
            return GTTTriggerResult(position_id, order.ticker, "target", order.target_price)
        return None
