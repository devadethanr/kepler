from __future__ import annotations

from typing import AsyncGenerator
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import AccountState
from tools.execution.gtt_manager import GTTManager
from tools.execution.alerts import AlertsTool

IST = ZoneInfo("Asia/Kolkata")


def _is_market_hours() -> bool:
    """Check if current time is within market hours (9:15 - 15:30 IST)."""
    now = datetime.now(IST).time()
    return dt_time(9, 15) <= now <= dt_time(15, 30)


def _enforce_market_hours() -> bool:
    return cfg.trading.mode.value == "live"


class PositionChecker(BaseAgent):
    def __init__(self, name: str = "PositionChecker") -> None:
        super().__init__(name=name)
        
    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        # Market hours guard
        if _enforce_market_hours() and not _is_market_hours():
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="Outside market hours — skipping")]))
            return

        # Activity manager tracking
        try:
            from api.tasks.activity_manager import activity_manager
            await activity_manager.start_activity(self.name, "Checking GTT health")
        except Exception:
            pass

        gtt_manager = GTTManager()
        alerts_tool = AlertsTool()
        
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="No active state")]))
            return
            
        state = AccountState.model_validate(state_payload)
        triggered_events = []
        
        # 1. Check GTT health and detect triggers
        for pos in state.positions:
            oco_gtt_id = pos.oco_gtt_id or pos.stop_gtt_id or pos.target_gtt_id
            if not oco_gtt_id:
                continue
            gtt = await gtt_manager.get_gtt_async(oco_gtt_id)
            if gtt is None or gtt.status == "cancelled":
                await alerts_tool.send_system_status(
                    f"⚠️ Protection GTT missing or cancelled for {pos.ticker}. Manual intervention required.",
                    is_warning=True,
                )
            elif gtt.status in {"triggered", "triggered_stop"}:
                pnl_pct = ((pos.stop_price / pos.entry_price) - 1) * 100
                triggered_events.append({
                    "type": "stop_hit",
                    "ticker": pos.ticker,
                    "entry_price": pos.entry_price,
                    "stop_price": pos.stop_price,
                    "pnl_pct": round(pnl_pct, 2),
                })
            elif gtt.status in {"triggered_target"}:
                pnl_pct = ((pos.target_price / pos.entry_price) - 1) * 100
                triggered_events.append({
                    "type": "target_hit",
                    "ticker": pos.ticker,
                    "entry_price": pos.entry_price,
                    "target_price": pos.target_price,
                    "pnl_pct": round(pnl_pct, 2),
                })

        # 2. Emit events for any triggers
        if triggered_events:
            try:
                from api.tasks.event_bus import event_bus, BusEvent, EventType
                for trigger in triggered_events:
                    event_type = EventType.STOP_HIT if trigger["type"] == "stop_hit" else EventType.TARGET_HIT
                    await event_bus.publish(BusEvent(
                        type=event_type,
                        payload=trigger,
                        source="position_checker",
                    ))
            except Exception as e:
                print(f"PositionChecker: event bus publish failed: {e}")

        # Activity complete
        try:
            from api.tasks.activity_manager import activity_manager
            await activity_manager.complete_activity(self.name, {"checked": len(state.positions), "triggered": len(triggered_events)})
        except Exception:
            pass

        yield Event(
            author=self.name, 
            content=types.Content(role="assistant", parts=[types.Part(text=f"Checked GTT health for {len(state.positions)} positions, {len(triggered_events)} triggers")])
        )

class StopTrailAgent(BaseAgent):
    def __init__(self, name: str = "StopTrailAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        # Market hours guard
        if _enforce_market_hours() and not _is_market_hours():
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="Outside market hours — skipping")]))
            return

        # Activity tracking
        try:
            from api.tasks.activity_manager import activity_manager
            await activity_manager.start_activity(self.name, "Trailing stops")
        except Exception:
            pass

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
            oco_gtt_id = pos.oco_gtt_id or pos.stop_gtt_id or pos.target_gtt_id
            
            # Simple trailing logic based on config
            if pnl_pct >= cfg.execution.trail_to_pct:
                new_stop = pos.entry_price * (1 + (cfg.execution.trail_stop_to_locked_profit_pct / 100))
                if new_stop > pos.stop_price and oco_gtt_id:
                    try:
                        await gtt_manager.modify_gtt_async(
                            oco_gtt_id,
                            new_stop,
                            ticker=pos.ticker,
                            target_price=pos.target_price,
                            quantity=pos.quantity
                        )
                        pos.stop_price = new_stop
                        modified_count += 1
                        await alerts_tool.send_alert(f"📈 Trailed stop for {pos.ticker} to {new_stop:.2f}")

                        # Emit trail event
                        try:
                            from api.tasks.event_bus import event_bus, BusEvent, EventType
                            await event_bus.publish(BusEvent(
                                type=EventType.STOP_TRAILED,
                                payload={"ticker": pos.ticker, "new_stop": new_stop, "pnl_pct": pnl_pct},
                                source="stop_trail_agent",
                            ))
                        except Exception:
                            pass

                    except Exception as e:
                        print(f"Failed to trail stop for {pos.ticker}: {e}")
            elif pnl_pct >= cfg.execution.trail_stop_at_pct:
                new_stop = pos.entry_price # breakeven
                if new_stop > pos.stop_price and oco_gtt_id:
                    try:
                        await gtt_manager.modify_gtt_async(
                            oco_gtt_id,
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

        # Activity complete
        try:
            from api.tasks.activity_manager import activity_manager
            await activity_manager.complete_activity(self.name, {"trailed": modified_count})
        except Exception:
            pass
            
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
