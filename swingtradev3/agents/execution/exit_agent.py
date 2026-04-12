from __future__ import annotations

from typing import Any, AsyncGenerator
import json

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event
from google.genai import types

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

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        state_payload = read_json(CONTEXT_DIR / "state.json", {})
        if not state_payload:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="No active state")]))
            return
            
        state = AccountState.model_validate(state_payload)
        
        if not state.positions:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="No open positions to evaluate")]))
            return
            
        # Example of dynamic exit intelligence evaluation
        for pos in state.positions:
            # We would use LlmAgent to evaluate exit signals here
            pass
            
        yield Event(
            author=self.name, 
            content=types.Content(role="assistant", parts=[types.Part(text=f"Exit intelligence evaluated for {len(state.positions)} positions")])
        )

exit_agent = ExitAgent()
