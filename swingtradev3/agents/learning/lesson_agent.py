from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event
from google.genai import types

from config import cfg
from paths import CONTEXT_DIR, STRATEGY_DIR
from storage import read_json, write_json


class LessonAgent(BaseAgent):
    """
    Reviews closed trades monthly and proposes SKILL.md edits.
    """
    def __init__(self, name: str = "LessonAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        if len(trades) < cfg.learning.min_trades_for_lesson:
            yield Event(
                author=self.name, 
                content=types.Content(role="assistant", parts=[types.Part(text="Not enough trades for lesson generation")])
            )
            return
            
        observations = read_json(CONTEXT_DIR / "trade_observations.json", [])
        
        skill_path = STRATEGY_DIR / "SKILL.md"
        current_skill = skill_path.read_text() if skill_path.exists() else ""
        
        lesson_llm = LlmAgent(
            name="LessonLLM",
            model=cfg.llm.adk.learning_model,
            instruction="""
            Monthly review of all closed trades.
            1. Find patterns in winners and losers.
            2. Propose max 3 specific SKILL.md edits with evidence.
            3. Cite specific trade IDs.
            Output JSON list of edits: [{"section": "...", "proposed_edit": "...", "reasoning": "...", "trade_ids": ["..."]}]
            """,
            description="Generates lessons from closed trades"
        )
        
        prompt = f"Trades: {json.dumps(trades, default=str)}\n\nObservations: {json.dumps(observations, default=str)}\n\nCurrent SKILL.md: {current_skill}"
        ctx.user_content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )
        
        response_text = ""
        async for event in lesson_llm.run_async(ctx):
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
                    
                parsed_edits = json.loads(content_str)
                
                # Write to staging
                staging_path = STRATEGY_DIR / "SKILL.md.staging"
                staging_content = "# Proposed SKILL.md Edits\n\n"
                for edit in parsed_edits:
                    staging_content += f"## Section: {edit.get('section')}\n"
                    staging_content += f"**Proposed Edit:** {edit.get('proposed_edit')}\n"
                    staging_content += f"**Reasoning:** {edit.get('reasoning')}\n"
                    staging_content += f"**Trade IDs:** {', '.join(edit.get('trade_ids', []))}\n\n"
                    
                staging_path.write_text(staging_content)
                
                yield Event(
                    author=self.name, 
                    content=types.Content(role="assistant", parts=[types.Part(text=f"Monthly analysis complete. {len(parsed_edits)} lessons proposed in SKILL.md.staging.")])
                )
            except Exception as e:
                yield Event(
                    author=self.name, 
                    content=types.Content(role="assistant", parts=[types.Part(text=f"Failed to parse lessons: {e}")])
                )

lesson_agent = LessonAgent()
