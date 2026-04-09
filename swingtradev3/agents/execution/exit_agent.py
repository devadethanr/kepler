from __future__ import annotations

from typing import Any
import json

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import AccountState
from tools.execution.alerts import AlertsTool


class ExitAgent(BaseAgent):
    """
    Evaluates open positions for exit intelligence (e.g., momentum decay, time-based exit).
    """
    def __init__(self, name: str = "ExitAgent") -> None:
        super().__init__(name=name)
        self.alerts_tool = AlertsTool()

    async def _run_async_impl(self, ctx) -> Event:
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            return Event(author=self.name, content={"msg": "No active state"})
            
        state = AccountState.model_validate(state_payload)
        
        if not state.positions:
            return Event(author=self.name, content={"msg": "No open positions to evaluate"})
            
        # Example of dynamic exit intelligence evaluation
        for pos in state.positions:
            # We would use LlmAgent to evaluate exit signals here
            # using recent OHLCV, volume, news, etc.
            
            # Simple placeholder logic
            # e.g., if price hasn't moved in 10 days
            pass
            
        return Event(author=self.name, content={"msg": "Exit intelligence evaluated", "positions_count": len(state.positions)})

exit_agent = ExitAgent()
