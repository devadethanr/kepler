from __future__ import annotations

import json
from datetime import date
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.llm.prompt_builder import PromptBuilder
from swingtradev3.llm.router import LLMRouter
from swingtradev3.models import AccountState, ResearchDecision, StatsSnapshot
from swingtradev3.tools import TOOL_REGISTRY


class ToolExecutor:
    def __init__(
        self,
        router: LLMRouter | None = None,
        prompt_builder: PromptBuilder | None = None,
        mode: str | None = None,
    ) -> None:
        self.router = router or LLMRouter()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.mode = mode or cfg.trading.mode.value

    async def score_stock(
        self,
        ticker: str,
        stock_context: dict[str, Any],
        state: AccountState,
        stats: StatsSnapshot,
        skill_version: str,
    ) -> ResearchDecision:
        messages = self.prompt_builder.build_research_messages(stock_context, state, stats)
        payload = await self.router.complete("research", messages=messages)
        text = self.router.extract_text(payload)
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Research model returned non-JSON output for {ticker}: {text}") from exc
        decoded["ticker"] = ticker
        decoded["research_date"] = date.today().isoformat()
        decoded["skill_version"] = skill_version
        decoded.setdefault("current_price", stock_context.get("close"))
        decoded.setdefault("sector", stock_context.get("sector"))
        return ResearchDecision.model_validate(decoded)

    async def generate_lessons(
        self,
        trades_payload: str,
        observations_payload: str,
        stats_payload: str,
    ) -> str:
        messages = self.prompt_builder.build_analyst_messages(
            trades_payload=trades_payload,
            observations_payload=observations_payload,
            stats_payload=stats_payload,
        )
        payload = await self.router.complete("analyst", messages=messages)
        return self.router.extract_text(payload)

    def available_tools(self) -> list[str]:
        return list(TOOL_REGISTRY)
