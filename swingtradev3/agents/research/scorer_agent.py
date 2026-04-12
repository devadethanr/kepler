from __future__ import annotations

import json
from typing import AsyncGenerator

from google.adk.agents import LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import BaseModel, PrivateAttr

from config import cfg
from models import StockScore
from paths import STRATEGY_DIR
from llm_bridge import SmartRouter
from knowledge.wiki_renderer import get_stock_context, format_context_for_llm


class ScorerAgent(LlmAgent):
    """
    V2 ADK Scorer Agent.
    Scores stocks one-by-one with a universal smart router for fallback/retry.
    """
    _router: SmartRouter = PrivateAttr()

    def __init__(self, name: str = "ScorerAgent") -> None:
        super().__init__(name=name, model=cfg.llm.adk.research_model)
        self._router = SmartRouter(role="research")

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

        for stock in qualified_stocks:
            ticker = stock["ticker"]
            data = stock_data.get(ticker, {})
            if not data:
                continue

            prompt = f"Analyze and score this stock setup: {json.dumps(data, default=str)}"

            # Inline KG read: get historical context for comparative scoring
            kg_context = get_stock_context(ticker)
            system_instruction = self._build_system_instruction(ticker, kg_context)

            # Universal Fallback Call
            try:
                score_obj = await self._router.generate_structured(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    response_model=StockScore
                )
                score_obj.ticker = ticker # Anchor
                final_scores.append(score_obj)
                
                # Progress yield
                yield Event(
                    author=self.name,
                    content=types.Content(role="assistant", parts=[types.Part(text=f"Analyzed {ticker}: Score {score_obj.score}")])
                )
            except Exception as e:
                print(f"FAILED to score {ticker} after all fallbacks: {e}")

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

    def _build_system_instruction(self, ticker: str, kg_context=None) -> str:
        skill_md = self._load_skill_md()
        
        # Build historical context section
        history_section = ""
        if kg_context and kg_context.has_history:
            history_section = f"""
        HISTORICAL CONTEXT (from Knowledge Graph):
        {format_context_for_llm(kg_context)}
        
        Use this context to make COMPARATIVE judgments. What has materially changed
        since the last scan? Is the setup improving or degrading?
        """
        
        return f"""
        You are a professional equity research analyst.
        Analyze the provided data block for {ticker} and return a StockScore JSON object.
        
        CRITICAL RULES:
        1. Base analysis ONLY on provided data. DO NOT use external training data.
        2. Current Price for {ticker} is in the 'technical' block. Use it for entry zones.
        {history_section}
        TRADING PHILOSOPHY:
        {skill_md}
        """

    def _load_skill_md(self) -> str:
        skill_path = STRATEGY_DIR / "SKILL.md"
        if skill_path.exists():
            return skill_path.read_text()
        return "Trend following and risk management."
