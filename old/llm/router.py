from __future__ import annotations

import json
import os
from typing import Any

from swingtradev3.config import cfg
from swingtradev3.llm.nim_client import NIMClient


class LLMRouter:
    def __init__(self, nim_client: NIMClient | None = None) -> None:
        self.nim_client = nim_client or NIMClient()

    def _provider_has_credentials(self, provider: str) -> bool:
        env_map = {
            "nim": "NIM_API_KEY",
            "groq": "GROQ_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }
        env_name = env_map.get(provider)
        return bool(env_name and os.getenv(env_name))

    async def _call_openai_compatible(
        self,
        provider: str,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for LLM access") from exc
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or [],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {"provider": provider, "response": response.model_dump()}

    async def _call_provider(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        if provider == "nim":
            return {
                "provider": provider,
                "response": await self.nim_client.chat_completion(
                    model=model,
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ),
            }
        if provider == "groq":
            return await self._call_openai_compatible(
                provider=provider,
                base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                api_key=os.getenv("GROQ_API_KEY", ""),
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == "gemini":
            return await self._call_openai_compatible(
                provider=provider,
                base_url=os.getenv(
                    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
                ),
                api_key=os.getenv("GEMINI_API_KEY", ""),
                model=model,
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        if provider == "anthropic":
            try:
                import anthropic
            except ImportError as exc:
                raise RuntimeError("anthropic package is required for Anthropic fallback") from exc
            client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            prompt = "\n\n".join(message["content"] for message in messages if isinstance(message.get("content"), str))
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return {"provider": provider, "response": {"content": response.model_dump()}}
        raise RuntimeError(f"Unsupported provider: {provider}")

    async def complete(
        self,
        role: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        role_cfg = getattr(cfg.llm.roles, role)
        attempts = [{"provider": role_cfg.provider, "model": role_cfg.model}] + [
            item.model_dump() for item in cfg.llm.fallback_chain
        ]
        failures: list[str] = []
        for attempt in attempts:
            provider = attempt["provider"]
            model = attempt["model"]
            if not self._provider_has_credentials(provider):
                failures.append(f"{provider}:missing_credentials")
                continue
            try:
                return await self._call_provider(
                    provider=provider,
                    model=model,
                    messages=messages,
                    tools=tools,
                    temperature=role_cfg.temperature,
                    max_tokens=role_cfg.max_tokens,
                )
            except Exception as exc:
                failures.append(f"{provider}:{exc}")
        raise RuntimeError(f"No LLM provider succeeded for role={role}: {'; '.join(failures)}")

    @staticmethod
    def extract_text(payload: dict[str, Any]) -> str:
        response = payload.get("response", {})
        choices = response.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                text_parts = [item.get("text", "") for item in content if isinstance(item, dict)]
                return "".join(text_parts)
        content = response.get("content")
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif "content" in block:
                        text_parts.append(json.dumps(block["content"]))
            return "".join(text_parts)
        return json.dumps(response)

    @staticmethod
    def extract_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = payload.get("response", {})
        choices = response.get("choices", [])
        if not choices:
            return []
        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        return [item for item in tool_calls if isinstance(item, dict)]
