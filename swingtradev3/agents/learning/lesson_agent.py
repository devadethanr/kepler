from __future__ import annotations

import json
from typing import Any

from google.adk.agents import LlmAgent, BaseAgent
from google.adk.events import Event

from config import cfg
from paths import CONTEXT_DIR, STRATEGY_DIR
from storage import read_json, write_json


class LessonAgent(BaseAgent):
    """
    Reviews closed trades monthly and proposes SKILL.md edits.
    """
    def __init__(self, name: str = "LessonAgent") -> None:
        super().__init__(name=name)

    async def _run_async_impl(self, ctx) -> Event:
        trades = read_json(CONTEXT_DIR / "trades.json", [])
        if len(trades) < cfg.learning.min_trades_for_lesson:
            return Event(author=self.name, content={"msg": "Not enough trades for lesson generation"})
            
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
        
        response_event = None
        async for event in lesson_llm.run_async(ctx, prompt):
            if event.is_final_response():
                response_event = event
                
        if response_event and response_event.content:
            try:
                content_str = response_event.content
                if "```json" in content_str:
                    content_str = content_str.split("```json")[1].split("```")[0]
                elif "```" in content_str:
                    content_str = content_str.split("```")[1].split("```")[0]
                    
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
                
                return Event(author=self.name, content={"msg": "Lessons generated", "edits": parsed_edits})
            except Exception as e:
                return Event(author=self.name, content={"error": f"Failed to parse lessons: {e}"})
                
        return Event(author=self.name, content={"msg": "No response from LessonLLM"})

lesson_agent = LessonAgent()
