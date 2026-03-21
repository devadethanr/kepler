from __future__ import annotations

import uuid

from swingtradev3.auth.kite.client import has_kite_session, place_live_order
from swingtradev3.config import cfg
from swingtradev3.integrations.kite.mcp_client import KiteMCPClient
from swingtradev3.models import AccountState
from swingtradev3.paper.fill_engine import FillEngine
from swingtradev3.tools.execution.gtt_manager import GTTManager
from swingtradev3.tools.execution.risk_check import RiskCheckTool


class OrderExecutionTool:
    def __init__(
        self,
        fill_engine: FillEngine | None = None,
        risk_tool: RiskCheckTool | None = None,
        gtt_manager: GTTManager | None = None,
        mcp_client: KiteMCPClient | None = None,
    ) -> None:
        self.fill_engine = fill_engine or FillEngine()
        self.risk_tool = risk_tool or RiskCheckTool()
        self.gtt_manager = gtt_manager or GTTManager()
        self.mcp_client = mcp_client or KiteMCPClient()

    def place_order(
        self,
        state: AccountState,
        ticker: str,
        side: str,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
    ) -> dict[str, object]:
        risk = self.risk_tool.check_risk(state, score, price, stop_price, target_price)
        if not risk["approved"]:
            return {"status": "rejected", "reason": risk["reason"], "quantity": 0}
        quantity = int(risk["quantity"])
        order_id = f"order-{uuid.uuid4().hex[:10]}"
        if cfg.trading.mode.value == "live":
            raise NotImplementedError("Live order execution requires Kite credentials")
        fill = self.fill_engine.fill(ticker, side, quantity, price, order_id)
        position_id = f"pos-{uuid.uuid4().hex[:10]}"
        gtt = self.gtt_manager.place_gtt(
            position_id,
            ticker,
            stop_price,
            target_price,
            quantity=quantity,
        )
        return {
            "order_id": fill.order_id,
            "status": fill.status,
            "average_price": fill.average_price,
            "quantity": fill.quantity,
            "position_id": position_id,
            "stop_gtt_id": gtt.position_id,
            "target_gtt_id": gtt.position_id,
        }

    async def place_order_async(
        self,
        state: AccountState,
        ticker: str,
        side: str,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
    ) -> dict[str, object]:
        risk = self.risk_tool.check_risk(state, score, price, stop_price, target_price)
        if not risk["approved"]:
            return {"status": "rejected", "reason": risk["reason"], "quantity": 0}
        quantity = int(risk["quantity"])
        order_id = f"order-{uuid.uuid4().hex[:10]}"
        if cfg.trading.mode.value != "live":
            return self.place_order(state, ticker, side, score, price, stop_price, target_price)
        if has_kite_session():
            try:
                order_id = place_live_order(
                    exchange=cfg.trading.exchange,
                    ticker=ticker,
                    side=side,
                    quantity=quantity,
                    price=price,
                )
            except Exception:
                order_id = f"order-{uuid.uuid4().hex[:10]}"
                await self.mcp_client.call_tool(
                    "place_order",
                    {
                        "exchange": cfg.trading.exchange,
                        "tradingsymbol": ticker,
                        "transaction_type": side.upper(),
                        "quantity": quantity,
                        "order_type": "LIMIT",
                        "product": "CNC",
                        "variety": "regular",
                        "price": price,
                    },
                )
        else:
            order_id = f"order-{uuid.uuid4().hex[:10]}"
            await self.mcp_client.call_tool(
                "place_order",
                {
                    "exchange": cfg.trading.exchange,
                    "tradingsymbol": ticker,
                    "transaction_type": side.upper(),
                    "quantity": quantity,
                    "order_type": "LIMIT",
                    "product": "CNC",
                    "variety": "regular",
                    "price": price,
                },
            )
        gtt = await self.gtt_manager.place_gtt_async(
            order_id,
            ticker,
            stop_price,
            target_price,
            quantity=quantity,
        )
        return {
            "order_id": order_id,
            "status": "filled",
            "average_price": price,
            "quantity": quantity,
            "position_id": order_id,
            "stop_gtt_id": gtt.position_id,
            "target_gtt_id": gtt.position_id,
        }
