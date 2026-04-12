from __future__ import annotations

from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.events import Event

from tools.analysis.regime_detection import detect_regime

class RegimeAgent(BaseAgent):
    """
    Market regime detection agent.
    Runs first in the pipeline to determine market conditions.
    """

    def __init__(self, name: str = "RegimeAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        from google.genai import types
        regime_data = detect_regime()
        ctx.session.state["regime"] = regime_data
        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Market regime detected: {regime_data.get('regime')}")]
            ),
        )
