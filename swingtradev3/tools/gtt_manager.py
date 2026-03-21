from __future__ import annotations

from swingtradev3.config import cfg
from swingtradev3.mcp_client import KiteMCPClient
from swingtradev3.models import GTTOrder
from swingtradev3.paper.gtt_simulator import GTTSimulator


class GTTManager:
    def __init__(
        self,
        simulator: GTTSimulator | None = None,
        mcp_client: KiteMCPClient | None = None,
    ) -> None:
        self.simulator = simulator or GTTSimulator()
        self.mcp_client = mcp_client or KiteMCPClient()

    def place_gtt(self, position_id: str, ticker: str, stop_price: float, target_price: float) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use place_gtt_async() for live MCP-backed GTT access")
        return self.simulator.place(position_id, ticker, stop_price, target_price)

    async def place_gtt_async(
        self, position_id: str, ticker: str, stop_price: float, target_price: float
    ) -> GTTOrder:
        if cfg.trading.mode.value != "live":
            return self.place_gtt(position_id, ticker, stop_price, target_price)
        await self.mcp_client.call_tool(
            "place_gtt_order",
            {
                "tradingsymbol": ticker,
                "exchange": cfg.trading.exchange,
                "trigger_values": [stop_price, target_price],
                "last_price": target_price,
            },
        )
        return GTTOrder(position_id=position_id, ticker=ticker, stop_price=stop_price, target_price=target_price)

    def modify_gtt(self, position_id: str, new_trigger: float) -> GTTOrder:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use modify_gtt_async() for live MCP-backed GTT access")
        return self.simulator.modify_stop(position_id, new_trigger)

    async def modify_gtt_async(self, position_id: str, new_trigger: float) -> GTTOrder:
        if cfg.trading.mode.value != "live":
            return self.modify_gtt(position_id, new_trigger)
        await self.mcp_client.call_tool("modify_gtt_order", {"trigger_id": position_id, "trigger_price": new_trigger})
        current = self.simulator.get(position_id)
        if current is not None:
            current.stop_price = new_trigger
            return current
        return GTTOrder(position_id=position_id, ticker="", stop_price=new_trigger, target_price=new_trigger)

    def cancel_gtt(self, position_id: str) -> None:
        if cfg.trading.mode == "live":
            raise NotImplementedError("Use cancel_gtt_async() for live MCP-backed GTT access")
        self.simulator.cancel(position_id)

    async def cancel_gtt_async(self, position_id: str) -> None:
        if cfg.trading.mode.value != "live":
            self.cancel_gtt(position_id)
            return
        await self.mcp_client.call_tool("delete_gtt_order", {"trigger_id": position_id})

    def get_gtt(self, position_id: str) -> GTTOrder | None:
        return self.simulator.get(position_id)
