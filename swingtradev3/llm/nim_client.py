from __future__ import annotations

import os
from typing import Any, AsyncIterator


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
        stream: bool = False,
    ) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("NIM_API_KEY is not configured")

        import requests

        invoke_url = f"{self.base_url.rstrip('/v1')}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream" if stream else "application/json",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 1.0,
            "stream": stream,
        }

        if stream:
            response = requests.post(
                invoke_url, headers=headers, json=payload, stream=True
            )
            response.raise_for_status()

            async def event_stream() -> AsyncIterator[dict[str, Any]]:
                for line in response.iter_lines():
                    if line:
                        decoded = line.decode("utf-8")
                        if decoded.startswith("data: "):
                            data = decoded[6:]
                            if data == "[DONE]":
                                break
                            import json

                            yield json.loads(data)

            return event_stream()
        else:
            response = requests.post(invoke_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
