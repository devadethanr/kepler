from __future__ import annotations

from typing import Any, AsyncGenerator
import json

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import AccountState
from tools.execution.risk_check import RiskCheckTool
from tools.execution.order_execution import OrderExecutionTool
from tools.execution.alerts import AlertsTool
from regime_adapter import RegimeAdaptiveConfig
from data.market_regime import MarketRegimeDetector


class OrderExecutionAgent(BaseAgent):
    """
    Checks for human-approved trades in pending_approvals.json
    and executes them with regime-adaptive position sizing.
    """

    def __init__(self, name: str = "OrderExecutionAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        risk_tool = RiskCheckTool()
        order_tool = OrderExecutionTool()
        alerts_tool = AlertsTool()

        # Get regime for position sizing adaptation
        regime_str = MarketRegimeDetector().detect_regime().get("regime", "neutral")
        regime_config = RegimeAdaptiveConfig(regime_str)

        approvals = read_json(CONTEXT_DIR / "pending_approvals.json", [])
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text="No active state found, skipping execution")],
                ),
            )
            return

        state = AccountState.model_validate(state_payload)

        executed_count = 0
        new_approvals = []

        for approval in approvals:
            if not approval.get("approved"):
                new_approvals.append(approval)
                continue

            ticker = approval["ticker"]
            score = approval["score"]
            entry_price = approval["entry_zone"]["high"]
            stop_price = approval["stop_price"]
            target_price = approval["target_price"]

            # 1. Run check_risk tool
            risk_decision = risk_tool.check_risk(
                state, score, entry_price, stop_price, target_price
            )

            if risk_decision["approved"]:
                # Apply regime-based position sizing
                base_qty = risk_decision["quantity"]
                adjusted_qty = regime_config.position_size(base_quantity=base_qty)

                if adjusted_qty == 0:
                    yield Event(
                        author=self.name,
                        content=types.Content(
                            role="assistant",
                            parts=[
                                types.Part(
                                    text=f"⚠️ {ticker} - New entries paused in {regime_str} regime. Skipping."
                                )
                            ],
                        ),
                    )
                    continue

                # Use adjusted quantity for order
                try:
                    result = await order_tool.place_order_async(
                        state=state,
                        ticker=ticker,
                        side="buy",
                        score=score,
                        price=entry_price,
                        stop_price=stop_price,
                        target_price=target_price,
                        quantity=adjusted_qty,
                    )
                    await alerts_tool.send_alert(f"🟢 Order placed for {ticker}: {result}")
                    executed_count += 1
                except Exception as e:
                    await alerts_tool.send_alert(f"🔴 Order failed for {ticker}: {e}")
                    new_approvals.append(approval)
            else:
                await alerts_tool.send_alert(
                    f"⚠️ Risk check failed for {ticker} post-approval: {risk_decision['reason']}"
                )

        write_json(CONTEXT_DIR / "pending_approvals.json", new_approvals)

        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[
                    types.Part(
                        text=f"Execution cycle complete. {executed_count} orders placed. Regime: {regime_str}"
                    )
                ],
            ),
        )
