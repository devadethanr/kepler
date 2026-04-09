from __future__ import annotations

import json
from typing import Any
from datetime import datetime

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event

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

    async def _run_async_impl(self, ctx) -> Event:
        # Example implementation
        # A real implementation would parse context and trigger LlmAgent to analyze.
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        if not trades:
            return Event(author=self.name, content={"msg": "No trades to review"})
            
        # Select latest unreviewed trade
        # For simplicity, we just say we reviewed it.
        observations = read_json(CONTEXT_DIR / "trade_observations.json", [])
        
        # Suppose we analyze the last trade:
        latest_trade = trades[-1]
        
        # Setup LlmAgent to review
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
        
        response_event = None
        async for event in reviewer_llm.run_async(ctx, prompt):
            if event.is_final_response():
                response_event = event
                
        if response_event and response_event.content:
            try:
                # Naive JSON extraction
                content_str = response_event.content
                if "```json" in content_str:
                    content_str = content_str.split("```json")[1].split("```")[0]
                elif "```" in content_str:
                    content_str = content_str.split("```")[1].split("```")[0]
                    
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
                return Event(author=self.name, content={"msg": f"Trade {latest_trade.get('trade_id')} reviewed.", "observation": obs.model_dump(mode="json")})
            except Exception as e:
                return Event(author=self.name, content={"error": f"Failed to parse LLM observation: {e}"})
                
        return Event(author=self.name, content={"msg": "No response from ReviewerLLM"})

learning_reviewer = TradeReviewerAgent()
