from __future__ import annotations

import json
from typing import AsyncGenerator

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from pydantic import BaseModel

from config import cfg
from models import StockScore
from paths import STRATEGY_DIR


class ScorerAgent(LlmAgent):
    """
    V2 ADK Scorer Agent.
    Scores stocks one-by-one with strict data grounding.
    """
    def __init__(self, name: str = "ScorerAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        qualified_stocks = ctx.session.state.get("qualified_stocks", [])
        stock_data = ctx.session.state.get("stock_data", {})
        
        if not qualified_stocks:
            yield Event(
                author=self.name, 
                content=types.Content(
                    role="assistant", 
                    parts=[types.Part(text="No qualified stocks to score.")]
                )
            )
            return

        final_scores: list[StockScore] = []
        model = self.canonical_model

        for stock in qualified_stocks:
            ticker = stock["ticker"]
            data = stock_data.get(ticker, {})
            if not data:
                continue

            # ONE-BY-ONE SCORING: Direct model call for maximum focus
            prompt = f"""
            ### DATA FOR {ticker}:
            {json.dumps(data, indent=2, default=str)}
            
            ### TASK:
            Analyze ONLY the numbers above for {ticker}.
            If a value is missing (null), you must not invent it.
            Assign a score based on the SKILL.md rules.
            """
            
            llm_request = LlmRequest(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=self._build_system_instruction(ticker),
                    response_mime_type="application/json",
                    response_schema=StockScore,
                    temperature=0.1
                )
            )
            
            async for response in model.generate_content_async(llm_request):
                if response.content and response.content.parts:
                    text = response.content.parts[0].text
                    if text:
                        try:
                            # Direct Pydantic validation of the structured output
                            score_obj = StockScore.model_validate_json(text)
                            # Anchor the ticker to ensure no INFY/TCS leakage
                            score_obj.ticker = ticker
                            final_scores.append(score_obj)
                        except Exception as e:
                            print(f"Error parsing {ticker} response: {e}")

        # PERSISTENCE
        shortlist = [s.model_dump() for s in final_scores if s.score >= 7.0]
        all_scored = [s.model_dump() for s in final_scores]
        
        actions = EventActions(state_delta={
            "scan_results": all_scored,
            "shortlist": shortlist
        })
        
        yield Event(
            author=self.name,
            actions=actions,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=f"Scoring completed. {len(shortlist)} shortlisted from {len(all_scored)} scored.")]
            )
        )

    def _build_system_instruction(self, ticker: str) -> str:
        skill_md = self._load_skill_md()
        return f"""
        You are a professional equity research analyst.
        Analyze the provided data block for {ticker} and return a StockScore JSON object.
        
        CRITICAL RULES:
        1. Base analysis ONLY on provided data. DO NOT use external training data.
        2. If data is missing (null/empty), you MUST acknowledge it. Do not invent EPS or Debt numbers.
        3. Current Price for {ticker} is provided in the 'technical' block. Use it for entry zones.
        
        TRADING PHILOSOPHY:
        {skill_md}
        """

    def _load_skill_md(self) -> str:
        skill_path = STRATEGY_DIR / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return "Trend following and risk management."
