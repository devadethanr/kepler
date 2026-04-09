from __future__ import annotations

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

    async def _run_async_impl(self, ctx) -> Event:
        regime_data = detect_regime()
        ctx.session.state["regime"] = regime_data
        return Event(
            author=self.name,
            content=regime_data,
        )
