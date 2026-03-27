from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.llm.prompt_builder import PromptBuilder
from swingtradev3.llm.router import LLMRouter
from swingtradev3.models import AccountState, ResearchDecision, StatsSnapshot
from swingtradev3.tools import (
    RESEARCH_TOOL_REGISTRY,
    RESEARCH_TOOL_SCHEMAS,
    TOOL_REGISTRY,
)


class ToolExecutor:
    def __init__(
        self,
        router: LLMRouter | None = None,
        prompt_builder: PromptBuilder | None = None,
        mode: str | None = None,
        tool_registry: dict[str, Any] | None = None,
        research_tool_schemas: list[dict[str, Any]] | None = None,
    ) -> None:
        self.router = router or LLMRouter()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.mode = mode or cfg.trading.mode.value
        self.tool_registry = tool_registry or RESEARCH_TOOL_REGISTRY
        self.research_tool_schemas = research_tool_schemas or RESEARCH_TOOL_SCHEMAS

    async def score_stock(
        self,
        ticker: str,
        stock_context: dict[str, Any],
        state: AccountState,
        stats: StatsSnapshot,
        skill_version: str,
        allow_tool_calls: bool = True,
    ) -> ResearchDecision:
        messages = self.prompt_builder.build_research_messages(
            stock_context, state, stats
        )
        payload: dict[str, Any] | None = None
        tools = self.research_tool_schemas if allow_tool_calls else None
        attempts = cfg.llm.max_tool_calls_per_stock + 1 if allow_tool_calls else 1
        for _ in range(attempts):
            payload = await self.router.complete(
                "research", messages=messages, tools=tools
            )
            if not allow_tool_calls:
                break
            tool_calls = self.router.extract_tool_calls(payload)
            if not tool_calls:
                break
            messages.extend(self._tool_messages(payload, tool_calls))
        if payload is None:
            raise RuntimeError(f"No research payload generated for {ticker}")

        text = self.router.extract_text(payload)
        try:
            decoded = self._decode_json_text(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Research model returned non-JSON output for {ticker}: {text}"
            ) from exc
        decoded["ticker"] = ticker
        decoded["research_date"] = date.today().isoformat()
        decoded["skill_version"] = skill_version
        decoded.setdefault("current_price", stock_context.get("close"))
        decoded.setdefault("sector", stock_context.get("sector"))
        decoded["setup_type"] = self._normalize_setup_type(
            decoded.get("setup_type", "skip")
        )
        return ResearchDecision.model_validate(decoded)

    def _normalize_setup_type(self, value: str) -> str:
        value_lower = value.lower().strip()
        if "breakout" in value_lower:
            return "breakout"
        if "pullback" in value_lower or "pull" in value_lower:
            return "pullback"
        if "earning" in value_lower:
            return "earnings_play"
        if "sector" in value_lower:
            return "sector_rotation"
        return "skip"

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

    def available_research_tools(self) -> list[str]:
        return list(self.tool_registry)

    def _tool_messages(
        self,
        payload: dict[str, Any],
        tool_calls: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        response = payload.get("response", {})
        choices = response.get("choices", [])
        assistant_message = choices[0].get("message", {}) if choices else {}
        messages: list[dict[str, Any]] = [
            {
                "role": "assistant",
                "content": assistant_message.get("content") or "",
                "tool_calls": tool_calls,
            }
        ]
        for item in tool_calls:
            function = item.get("function", {})
            name = function.get("name")
            if name not in self.tool_registry:
                raise RuntimeError(f"Unknown research tool requested: {name}")
            raw_arguments = function.get("arguments") or "{}"
            arguments = (
                json.loads(raw_arguments)
                if isinstance(raw_arguments, str)
                else raw_arguments
            )
            result = self.tool_registry[name](**arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item.get("id"),
                    "name": name,
                    "content": json.dumps(result, default=str),
                }
            )
        return messages

    @staticmethod
    def _decode_json_text(text: str) -> dict[str, Any]:
        candidate = text.strip()
        if candidate.startswith("```"):
            fenced = re.search(
                r"```(?:json)?\s*(\{.*\})\s*```", candidate, flags=re.DOTALL
            )
            if fenced:
                candidate = fenced.group(1).strip()
        try:
            decoded = json.loads(candidate)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            decoded = json.loads(candidate[start : end + 1])
            if isinstance(decoded, dict):
                return decoded
        raise json.JSONDecodeError("No JSON object found", text, 0)
