from __future__ import annotations

import os
from typing import Any


class NIMClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("NIM_API_KEY")
        self.base_url = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("NIM_API_KEY is not configured")
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for NIM access") from exc

        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or [],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.model_dump()
