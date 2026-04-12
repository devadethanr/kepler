from __future__ import annotations

import json
from typing import Any, AsyncGenerator
from datetime import datetime

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from paths import CONTEXT_DIR
from storage import read_json, write_json
from models import TradeObservation

class TradeReviewerAgent(BaseAgent):
    """
    Reviews closed trades and extracts lessons using LLM.
    """
    def __init__(self, name: str = "TradeReviewer") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        if not trades:
            yield Event(author=self.name, content=types.Content(role="assistant", parts=[types.Part(text="No trades to review")]))
            return
            
        observations = read_json(CONTEXT_DIR / "trade_observations.json", [])
        latest_trade = trades[-1]
        
        reviewer_llm = LlmAgent(
            name=f"ReviewerLLM_{latest_trade.get('ticker')}",
            model=cfg.llm.adk.learning_model,
            instruction="""
            Review this closed trade. 
            1. Compare outcome vs original thesis.
            2. Was the entry well-timed?
            3. Did the stop-loss work correctly?
            Output JSON with {"observation": "...", "thesis_held": bool, "exit_reason": "..."}
            """,
            description="Reviews a single closed trade"
        )
        
        prompt = json.dumps(latest_trade, default=str)
        ctx.user_content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        response_text = ""
        async for event in reviewer_llm.run_async(ctx):
            if event.is_final_response():
                # Handle both raw strings and types.Content objects
                content = event.content
                if hasattr(content, "parts") and content.parts:
                    response_text = content.parts[0].text or ""
                else:
                    response_text = str(content)
            yield event
                
        if response_text:
            try:
                content_str = response_text
                if "```json" in content_str:
                    content_str = content_str.split("```json")[1].split("```")[0]
                elif "```" in content_str:
                    content_str = content_str.split("```")[1].split("```")[0]
                
                start = content_str.find("{")
                end = content_str.rfind("}")
                if start != -1 and end != -1:
                    content_str = content_str[start:end+1]
                    
                parsed = json.loads(content_str)
                obs = TradeObservation(
                    trade_id=latest_trade.get("trade_id", "unknown"),
                    ticker=latest_trade.get("ticker", "unknown"),
                    observation=parsed.get("observation", "Reviewed trade."),
                    thesis_held=parsed.get("thesis_held", False),
                    exit_reason=parsed.get("exit_reason", latest_trade.get("exit_reason", "unknown")),
                    created_at=datetime.utcnow()
                )
                observations.append(obs.model_dump(mode="json"))
                write_json(CONTEXT_DIR / "trade_observations.json", observations)
                yield Event(
                    author=self.name, 
                    content=types.Content(role="assistant", parts=[types.Part(text=f"Trade {latest_trade.get('trade_id')} review saved.")])
                )
            except Exception as e:
                yield Event(
                    author=self.name, 
                    content=types.Content(role="assistant", parts=[types.Part(text=f"Failed to parse LLM observation: {e}")])
                )

learning_reviewer = TradeReviewerAgent()
