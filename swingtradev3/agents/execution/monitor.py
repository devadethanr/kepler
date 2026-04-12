from __future__ import annotations

from typing import Any, AsyncGenerator
import json
from datetime import datetime

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import AccountState, CorporateAction
from tools.execution.gtt_manager import GTTManager
from tools.execution.alerts import AlertsTool
from data.corporate_actions import CorporateActionsStore

class PositionChecker(BaseAgent):
    def __init__(self, name: str = "PositionChecker") -> None:
        super().__init__(name=name)
        
    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        gtt_manager = GTTManager()
        alerts_tool = AlertsTool()
        
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="No active state")]))
            return
            
        state = AccountState.model_validate(state_payload)
        
        # 1. Check GTT health
        for pos in state.positions:
            if pos.stop_gtt_id:
                gtt = await gtt_manager.get_gtt_async(pos.stop_gtt_id)
                if gtt is None or gtt.status == "cancelled":
                    await alerts_tool.send_system_status(f"⚠️ GTT missing or cancelled for {pos.ticker}. Manual intervention required.", is_warning=True)
                    
            if pos.target_gtt_id:
                gtt = await gtt_manager.get_gtt_async(pos.target_gtt_id)
                if gtt is None or gtt.status == "cancelled":
                    await alerts_tool.send_system_status(f"⚠️ Target GTT missing or cancelled for {pos.ticker}.", is_warning=True)
                    
        yield Event(
            author=self.name, 
            content=types.Content(role="assistant", parts=[types.Part(text=f"Checked GTT health for {len(state.positions)} positions")])
        )

class StopTrailAgent(BaseAgent):
    def __init__(self, name: str = "StopTrailAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        gtt_manager = GTTManager()
        alerts_tool = AlertsTool()
        
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload or not cfg.execution.enable_trailing:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="Trailing disabled or no state")]))
            return
            
        state = AccountState.model_validate(state_payload)
        modified_count = 0
        
        for pos in state.positions:
            if not pos.current_price:
                continue
                
            pnl_pct = ((pos.current_price / pos.entry_price) - 1) * 100
            
            # Simple trailing logic based on config
            if pnl_pct >= cfg.execution.trail_to_pct:
                new_stop = pos.entry_price * (1 + (cfg.execution.trail_stop_to_locked_profit_pct / 100))
                if new_stop > pos.stop_price and pos.stop_gtt_id:
                    try:
                        await gtt_manager.modify_gtt_async(
                            pos.stop_gtt_id,
                            new_stop,
                            ticker=pos.ticker,
                            target_price=pos.target_price,
                            quantity=pos.quantity
                        )
                        pos.stop_price = new_stop
                        modified_count += 1
                        await alerts_tool.send_alert(f"📈 Trailed stop for {pos.ticker} to {new_stop:.2f}")
                    except Exception as e:
                        print(f"Failed to trail stop for {pos.ticker}: {e}")
            elif pnl_pct >= cfg.execution.trail_stop_at_pct:
                new_stop = pos.entry_price # breakeven
                if new_stop > pos.stop_price and pos.stop_gtt_id:
                    try:
                        await gtt_manager.modify_gtt_async(
                            pos.stop_gtt_id,
                            new_stop,
                            ticker=pos.ticker,
                            target_price=pos.target_price,
                            quantity=pos.quantity
                        )
                        pos.stop_price = new_stop
                        modified_count += 1
                        await alerts_tool.send_alert(f"📈 Moved stop to breakeven for {pos.ticker}: {new_stop:.2f}")
                    except Exception as e:
                        print(f"Failed to move stop to breakeven for {pos.ticker}: {e}")
                        
        if modified_count > 0:
            write_json(CONTEXT_DIR / "state.json", state.model_dump(mode="json"))
            
        yield Event(
            author=self.name, 
            content=types.Content(role="assistant", parts=[types.Part(text=f"Trailed {modified_count} stops")])
        )

execution_monitor = SequentialAgent(
    name="ExecutionMonitor",
    sub_agents=[
        PositionChecker(),
        StopTrailAgent()
    ],
    description="Monitors live positions, verifies GTTs, and trails stops."
)
