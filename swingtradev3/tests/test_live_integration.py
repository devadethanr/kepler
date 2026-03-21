from __future__ import annotations

import asyncio
from datetime import datetime

from swingtradev3.agents.execution_agent import ExecutionAgent
from swingtradev3.models import AccountState, PositionState
from swingtradev3.tools.order_execution import OrderExecutionTool


class RecordingGTTManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def place_gtt(
        self,
        position_id: str,
        ticker: str,
        stop_price: float,
        target_price: float,
        quantity: int = 1,
    ) -> object:
        self.calls.append(
            {
                "position_id": position_id,
                "ticker": ticker,
                "stop_price": stop_price,
                "target_price": target_price,
                "quantity": quantity,
            }
        )

        class Result:
            def __init__(self, value: str) -> None:
                self.position_id = value

        return Result(f"gtt-{position_id}")

    async def modify_gtt_async(
        self,
        position_id: str,
        new_trigger: float,
        *,
        ticker: str | None = None,
        target_price: float | None = None,
        quantity: int = 1,
    ) -> object:
        self.calls.append(
            {
                "position_id": position_id,
                "new_trigger": new_trigger,
                "ticker": ticker,
                "target_price": target_price,
                "quantity": quantity,
            }
        )
        return object()

    async def place_gtt_async(
        self,
        position_id: str,
        ticker: str,
        stop_price: float,
        target_price: float,
        quantity: int = 1,
    ) -> object:
        return self.place_gtt(position_id, ticker, stop_price, target_price, quantity=quantity)


class AllowAllRiskTool:
    def check_risk(
        self,
        state: AccountState,
        score: float,
        price: float,
        stop_price: float,
        target_price: float,
    ) -> dict[str, object]:
        return {"approved": True, "quantity": 7, "reason": ""}


class StubMCPClient:
    async def call_tool(self, name: str, arguments: dict[str, object] | None = None) -> dict[str, object]:
        return {"name": name, "arguments": arguments or {}}


def test_execution_agent_trailing_updates_use_stop_gtt_id_and_quantity() -> None:
    gtt_manager = RecordingGTTManager()
    agent = ExecutionAgent(gtt_manager=gtt_manager)
    state = AccountState(
        positions=[
            PositionState(
                ticker="INFY",
                quantity=5,
                entry_price=100.0,
                current_price=112.0,
                stop_price=95.0,
                target_price=125.0,
                opened_at=datetime.utcnow(),
                entry_order_id="entry-123",
                stop_gtt_id="gtt-456",
            )
        ]
    )

    asyncio.run(agent._check_trailing(state))

    assert gtt_manager.calls
    assert gtt_manager.calls[0]["position_id"] == "gtt-456"
    assert gtt_manager.calls[0]["ticker"] == "INFY"
    assert gtt_manager.calls[0]["target_price"] == 125.0
    assert gtt_manager.calls[0]["quantity"] == 5


def test_order_execution_passes_risk_quantity_into_gtt() -> None:
    gtt_manager = RecordingGTTManager()
    tool = OrderExecutionTool(
        risk_tool=AllowAllRiskTool(),
        gtt_manager=gtt_manager,
        mcp_client=StubMCPClient(),
    )
    state = AccountState(cash_inr=100000.0)

    result = asyncio.run(
        tool.place_order_async(
            state=state,
            ticker="INFY",
            side="buy",
            score=0.9,
            price=100.0,
            stop_price=95.0,
            target_price=120.0,
        )
    )

    assert result["quantity"] == 7
    assert gtt_manager.calls
    assert gtt_manager.calls[0]["quantity"] == 7
