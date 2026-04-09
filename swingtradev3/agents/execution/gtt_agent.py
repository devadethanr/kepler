from __future__ import annotations

from typing import Any

from google.adk.agents import BaseAgent
from google.adk.events import Event

from tools.execution.gtt_manager import GTTManager


class GttAgent(BaseAgent):
    """
    Manages GTT lifecycle independently, acting as an executor for GTT modifications.
    """
    def __init__(self, name: str = "GttAgent") -> None:
        super().__init__(name=name)
        self.gtt_manager = GTTManager()

    async def _run_async_impl(self, ctx) -> Event:
        # Example logic: GTT modification requested by another agent
        # Normally would extract the requested action from context
        action = ctx.session.state.get("gtt_action")
        
        if action == "modify":
            # await self.gtt_manager.modify_gtt_async(...)
            pass
        elif action == "cancel":
            # await self.gtt_manager.cancel_gtt_async(...)
            pass
            
        return Event(author=self.name, content={"msg": "GTT action completed"})

gtt_agent = GttAgent()
