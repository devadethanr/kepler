from __future__ import annotations

from swingtradev3.llm.tool_executor import ToolExecutor
from swingtradev3.paths import CONTEXT_DIR, STRATEGY_DIR


class LessonGenerator:
    def __init__(self, executor: ToolExecutor | None = None) -> None:
        self.executor = executor or ToolExecutor()

    async def generate(self) -> str:
        trades_payload = (CONTEXT_DIR / "trades.json").read_text(encoding="utf-8")
        observations_payload = (CONTEXT_DIR / "trade_observations.json").read_text(encoding="utf-8")
        stats_payload = (CONTEXT_DIR / "stats.json").read_text(encoding="utf-8")
        lessons = await self.executor.generate_lessons(trades_payload, observations_payload, stats_payload)
        (STRATEGY_DIR / "SKILL.md.staging").write_text(lessons, encoding="utf-8")
        return lessons
