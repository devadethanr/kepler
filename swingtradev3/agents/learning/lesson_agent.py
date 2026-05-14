from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from pydantic import BaseModel, PrivateAttr

from config import cfg
from context_graph.context_builder import ContextBuilder
from context_graph.repository import ContextGraphRepository
from llm_bridge import SmartRouter
from memory.db import session_scope
from memory.repository import MemoryRepository
from paths import STRATEGY_DIR

IST = ZoneInfo("Asia/Kolkata")


class SkillEdit(BaseModel):
    section: str
    proposed_edit: str
    reasoning: str
    trade_ids: list[str]


class LessonResponse(BaseModel):
    edits: list[SkillEdit]


class LessonAgent(BaseAgent):
    """
    Reviews closed trades monthly and proposes SKILL.md edits with smart routing.
    """
    _router: SmartRouter = PrivateAttr()

    def __init__(self, name: str = "LessonAgent") -> None:
        super().__init__(name=name)
        self._router = SmartRouter(role="learning")

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        with session_scope() as session:
            trades = MemoryRepository(session).get_trades_payload()
        if len(trades) < cfg.learning.min_trades_for_lesson:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text="Not enough trades for lesson generation")],
                ),
            )
            return

        observations = ContextBuilder().get_recent_observations(limit=50)
        skill_path = STRATEGY_DIR / "SKILL.md"
        current_skill = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

        system_instruction = """
        Monthly review of all closed trades.
        1. Find patterns in winners and losers.
        2. Propose max 3 specific SKILL.md edits with evidence.
        3. Cite specific trade IDs.
        Output JSON list of edits in an 'edits' key.
        """

        prompt = (
            f"Trades: {json.dumps(trades, default=str)}\n\n"
            f"Observations: {json.dumps(observations, default=str)}\n\n"
            f"Current SKILL.md: {current_skill}"
        )

        try:
            lesson_result = await self._router.generate_structured(
                prompt=prompt,
                system_instruction=system_instruction,
                response_model=LessonResponse,
            )

            # Write to staging
            staging_path = STRATEGY_DIR / "SKILL.md.staging"
            staging_content = "# Proposed SKILL.md Edits\n\n"
            for edit in lesson_result.edits:
                staging_content += f"## Section: {edit.section}\n"
                staging_content += f"**Proposed Edit:** {edit.proposed_edit}\n"
                staging_content += f"**Reasoning:** {edit.reasoning}\n"
                staging_content += f"**Trade IDs:** {', '.join(edit.trade_ids)}\n\n"

            staging_path.write_text(staging_content, encoding="utf-8")

            graph = ContextGraphRepository()
            for index, edit in enumerate(lesson_result.edits, start=1):
                graph.upsert_lesson(
                    lesson_id=f"{datetime.now(IST).date().isoformat()}:{index}",
                    lesson_text=edit.proposed_edit,
                    category=edit.section,
                    observation_ids=edit.trade_ids,
                    payload=edit.model_dump(mode="json"),
                    observed_at=datetime.now(IST),
                    source="lesson_agent",
                )
            graph.close()

            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[
                        types.Part(
                            text=(
                                "Monthly analysis complete. "
                                f"{len(lesson_result.edits)} lessons proposed in SKILL.md.staging."
                            )
                        )
                    ],
                ),
            )
        except Exception as e:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="assistant",
                    parts=[types.Part(text=f"Failed to generate lessons: {e}")],
                ),
            )


lesson_agent = LessonAgent()
