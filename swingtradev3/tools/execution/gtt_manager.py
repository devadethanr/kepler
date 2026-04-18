from __future__ import annotations

from auth.kite.client import (
    delete_live_gtt,
    fetch_gtt,
    fetch_gtts,
    fetch_ltp,
    has_kite_session,
    modify_live_gtt,
    place_live_gtt,
)
from config import cfg
from integrations.kite.mcp_client import KiteMCPClient
from models import GTTOrder
from paper.gtt_simulator import GTTSimulator


class GTTManager:
    def __init__(
        self,
        simulator: GTTSimulator | None = None,
        mcp_client: KiteMCPClient | None = None,
    ) -> None:
        self.simulator = simulator or GTTSimulator()
        self.mcp_client = mcp_client or KiteMCPClient()

    async def _resolve_last_price(self, ticker: str, fallback: float) -> float:
        if has_kite_session():
            try:
                return fetch_ltp(cfg.trading.exchange, ticker)
            except Exception:
                pass
        try:
            result = await self.mcp_client.call_tool(
                "get_ltp",
                {"exchange": cfg.trading.exchange, "tradingsymbol": ticker},
            )
            if "last_price" in result:
                return float(result["last_price"])
            content = result.get("content", [])
            if content and isinstance(content, list) and isinstance(content[0], dict):
                text = str(content[0].get("text", ""))
                if text:
                    import re

                    match = re.search(r"(\d+(?:\.\d+)?)", text)
                    if match:
                        return float(match.group(1))
        except Exception:
            pass
        return fallback

    def place_gtt(
        self,
        position_id: str,
        ticker: str,
        stop_price: float,
        target_price: float,
        quantity: int = 1,
    ) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use place_gtt_async() for live MCP-backed GTT access")
        return self.simulator.place(position_id, ticker, stop_price, target_price)

    async def place_gtt_async(
        self,
        position_id: str,
        ticker: str,
        stop_price: float,
        target_price: float,
        quantity: int = 1,
    ) -> GTTOrder:
        if cfg.trading.mode.value != "live":
            return self.place_gtt(position_id, ticker, stop_price, target_price, quantity=quantity)
        if has_kite_session():
            last_price = await self._resolve_last_price(ticker, target_price)
            trigger_id = place_live_gtt(
                exchange=cfg.trading.exchange,
                ticker=ticker,
                quantity=quantity,
                stop_price=stop_price,
                target_price=target_price,
                last_price=last_price,
            )
            return GTTOrder(
                oco_gtt_id=trigger_id,
                ticker=ticker,
                stop_price=stop_price,
                target_price=target_price,
            )
        await self.mcp_client.call_tool(
            "place_gtt_order",
            {
                "tradingsymbol": ticker,
                "exchange": cfg.trading.exchange,
                "trigger_values": [stop_price, target_price],
                "last_price": target_price,
            },
        )
        return GTTOrder(
            oco_gtt_id=position_id,
            ticker=ticker,
            stop_price=stop_price,
            target_price=target_price,
        )

    def modify_gtt(
        self,
        position_id: str,
        new_trigger: float,
        *,
        ticker: str | None = None,
        target_price: float | None = None,
        quantity: int = 1,
    ) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use modify_gtt_async() for live MCP-backed GTT access")
        return self.simulator.modify_stop(position_id, new_trigger)

    async def modify_gtt_async(
        self,
        position_id: str,
        new_trigger: float,
        *,
        ticker: str | None = None,
        target_price: float | None = None,
        quantity: int = 1,
    ) -> GTTOrder:
        if cfg.trading.mode.value != "live":
            return self.modify_gtt(
                position_id,
                new_trigger,
                ticker=ticker,
                target_price=target_price,
                quantity=quantity,
            )
        if has_kite_session():
            live_ticker = ticker or ""
            live_target_price = target_price if target_price is not None else new_trigger
            if live_ticker:
                last_price = await self._resolve_last_price(live_ticker, live_target_price)
                modify_live_gtt(
                    trigger_id=position_id,
                    exchange=cfg.trading.exchange,
                    ticker=live_ticker,
                    quantity=quantity,
                    stop_price=new_trigger,
                    target_price=live_target_price,
                    last_price=last_price,
                )
            current = await self.get_gtt_async(position_id)
            if current is not None:
                current.stop_price = new_trigger
                return current
            return GTTOrder(
                oco_gtt_id=position_id,
                ticker=live_ticker,
                stop_price=new_trigger,
                target_price=live_target_price,
            )
        await self.mcp_client.call_tool("modify_gtt_order", {"trigger_id": position_id, "trigger_price": new_trigger})
        current = self.simulator.get(position_id)
        if current is not None:
            current.stop_price = new_trigger
            return current
        return GTTOrder(
            oco_gtt_id=position_id,
            ticker="",
            stop_price=new_trigger,
            target_price=new_trigger,
        )

    def cancel_gtt(self, position_id: str) -> None:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use cancel_gtt_async() for live MCP-backed GTT access")
        self.simulator.cancel(position_id)

    async def cancel_gtt_async(self, position_id: str) -> None:
        if cfg.trading.mode.value != "live":
            self.cancel_gtt(position_id)
            return
        if has_kite_session():
            delete_live_gtt(position_id)
            return
        await self.mcp_client.call_tool("delete_gtt_order", {"trigger_id": position_id})

    def get_gtt(self, position_id: str) -> GTTOrder | None:
        return self.simulator.get(position_id)

    async def get_gtt_async(self, position_id: str) -> GTTOrder | None:
        if cfg.trading.mode.value != "live":
            return self.get_gtt(position_id)
        if has_kite_session():
            try:
                items = [fetch_gtt(position_id)]
            except Exception:
                items = fetch_gtts()
            for item in items:
                trigger_id = str(item.get("id") or item.get("trigger_id") or "")
                if trigger_id != position_id:
                    continue
                condition = item.get("condition") or {}
                trigger_values = condition.get("trigger_values") or []
                orders = item.get("orders") or []
                stop_price = float(trigger_values[0]) if trigger_values else 0.0
                target_price = float(trigger_values[1]) if len(trigger_values) > 1 else stop_price
                ticker = str(item.get("tradingsymbol") or (orders[0].get("tradingsymbol") if orders else ""))
                raw_status = str(item.get("status", "")).lower()
                status = (
                    raw_status
                    if raw_status in {"active", "triggered", "disabled", "expired", "cancelled", "rejected", "deleted"}
                    else "active"
                )
                triggered_leg = None
                exit_order_id = None
                exit_exchange_order_id = None
                exit_order_status = None
                exit_rejection_reason = None
                if isinstance(orders, list):
                    for index, order in enumerate(orders):
                        if not isinstance(order, dict):
                            continue
                        result = order.get("result") or order.get("order_result")
                        if not result or not isinstance(result, dict):
                            continue
                        triggered_leg = "stop" if index == 0 else "target"
                        nested = result.get("order_result") if isinstance(result.get("order_result"), dict) else result
                        if isinstance(nested, dict):
                            exit_order_id = str(nested.get("order_id") or "") or None
                            exit_exchange_order_id = str(nested.get("exchange_order_id") or "") or None
                            if nested.get("status") not in (None, ""):
                                exit_order_status = str(nested["status"]).strip().lower()
                            if nested.get("rejection_reason") not in (None, ""):
                                exit_rejection_reason = str(nested["rejection_reason"])
                        break
                return GTTOrder(
                    oco_gtt_id=trigger_id,
                    ticker=ticker,
                    stop_price=stop_price,
                    target_price=target_price,
                    status=status,
                    triggered_leg=triggered_leg,
                    exit_order_id=exit_order_id,
                    exit_exchange_order_id=exit_exchange_order_id,
                    exit_order_status=exit_order_status,
                    exit_rejection_reason=exit_rejection_reason,
                )
            return None
        return self.get_gtt(position_id)
