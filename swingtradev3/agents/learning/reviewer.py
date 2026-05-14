from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from pydantic import BaseModel, PrivateAttr

from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory.repository import MemoryRepository
from models import TradeObservation
from llm_bridge import SmartRouter

IST = ZoneInfo("Asia/Kolkata")


class TradeReviewSchema(BaseModel):
    observation: str
    thesis_held: bool
    exit_reason: str


class TradeReviewerAgent(BaseAgent):
    """
    Reviews closed trades and extracts lessons using LLM with smart routing.
    """
    _router: SmartRouter = PrivateAttr()

    def __init__(self, name: str = "TradeReviewer") -> None:
        super().__init__(name=name)
        self._router = SmartRouter(role="learning")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        with session_scope() as session:
            trades = MemoryRepository(session).get_trades_payload()
        if not trades:
            yield Event(
                author=self.name,
                content=types.Content(role="assistant", parts=[types.Part(text="No trades to review")]),
            )
            return

        latest_trade = trades[-1]

        system_instruction = """
        Review this closed trade. 
        1. Compare outcome vs original thesis.
        2. Was the entry well-timed?
        3. Did the stop-loss work correctly?
        Output JSON with {"observation": "...", "thesis_held": bool, "exit_reason": "..."}
        """
        
        prompt = json.dumps(latest_trade, default=str)
        
        try:
            review = await self._router.generate_structured(
                prompt=prompt,
                system_instruction=system_instruction,
                response_model=TradeReviewSchema,
            )

            obs = TradeObservation(
                trade_id=latest_trade.get("trade_id", "unknown"),
                ticker=latest_trade.get("ticker", "unknown"),
                observation=review.observation,
                thesis_held=review.thesis_held,
                exit_reason=review.exit_reason,
                created_at=datetime.now(IST),
            )
            graph = ContextGraphRepository()
            graph.record_observation(
                observation_type="trade_review",
                ticker=obs.ticker,
                payload=obs.model_dump(mode="json"),
                source="trade_reviewer",
            )
            graph.close()

            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[
                        types.Part(
                            text=f"Trade {latest_trade.get('trade_id')} review saved."
                        )
                    ],
                ),
            )
        except Exception as e:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant", parts=[types.Part(text=f"Failed to review trade: {e}")]
                ),
            )


learning_reviewer = TradeReviewerAgent()
