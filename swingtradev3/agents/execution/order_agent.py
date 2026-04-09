from __future__ import annotations

from typing import Any
import json

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.events import Event

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import AccountState
from tools.execution.risk_check import RiskCheckTool
from tools.execution.order_execution import OrderExecutionTool
from tools.execution.alerts import AlertsTool

class OrderExecutionAgent(BaseAgent):
    """
    Checks for human-approved trades in pending_approvals.json
    and executes them.
    """
    def __init__(self, name: str = "OrderExecutionAgent") -> None:
        super().__init__(name=name)
        self.risk_tool = RiskCheckTool()
        self.order_tool = OrderExecutionTool()
        self.alerts_tool = AlertsTool()

    async def _run_async_impl(self, ctx) -> Event:
        approvals = read_json(CONTEXT_DIR / "pending_approvals.json", [])
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            return Event(author=self.name, content={"msg": "No active state found, skipping execution"})
            
        state = AccountState.model_validate(state_payload)
        
        executed_count = 0
        new_approvals = []
        
        for approval in approvals:
            if not approval.get("approved"):
                new_approvals.append(approval)
                continue
                
            ticker = approval["ticker"]
            score = approval["score"]
            entry_price = approval["entry_zone"]["high"] # Conservative entry assumption
            stop_price = approval["stop_price"]
            target_price = approval["target_price"]
            
            # 1. Run check_risk tool
            risk_decision = self.risk_tool.check_risk(state, score, entry_price, stop_price, target_price)
            
            if risk_decision["approved"]:
                # 3. place_order and GTTs
                try:
                    result = await self.order_tool.place_order_async(
                        state=state,
                        ticker=ticker,
                        side="buy",
                        score=score,
                        price=entry_price,
                        stop_price=stop_price,
                        target_price=target_price
                    )
                    await self.alerts_tool.send_alert(f"🟢 Order placed for {ticker}: {result}")
                    executed_count += 1
                except Exception as e:
                    await self.alerts_tool.send_alert(f"🔴 Order failed for {ticker}: {e}")
                    new_approvals.append(approval) # Keep it to retry or manual fix
            else:
                await self.alerts_tool.send_alert(f"⚠️ Risk check failed for {ticker} post-approval: {risk_decision['reason']}")
                # We do not append it to new_approvals, it is discarded
                
        write_json(CONTEXT_DIR / "pending_approvals.json", new_approvals)
        
        return Event(
            author=self.name,
            content={"executed_count": executed_count, "remaining_pending": len(new_approvals)},
        )

order_agent = OrderExecutionAgent()
