from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from config import cfg
from llm_bridge import SmartRouter

T = TypeVar("T", bound=BaseModel)


class CognitionLLMClient:
    """Thin structured-output adapter for optional slow-brain local LLM calls."""

    def __init__(self, *, role: str = "research", enabled: bool | None = None) -> None:
        self.enabled = bool(cfg.llm.local.enabled if enabled is None else enabled)
        self._router = SmartRouter(role=role) if self.enabled else None
        if self._router is not None:
            self._router.chain = [
                {"provider": cfg.llm.local.provider, "model": cfg.llm.local.model}
            ]

    async def generate_structured(
        self,
        *,
        prompt: str,
        system_instruction: str,
        response_model: type[T],
        fallback_factory: Callable[[], T] | None = None,
    ) -> T:
        if not self.enabled or self._router is None:
            if fallback_factory is not None:
                return fallback_factory()
            raise RuntimeError("Local cognition LLM is disabled")
        try:
            return await self._router.generate_structured(
                prompt=prompt,
                system_instruction=system_instruction,
                response_model=response_model,
            )
        except Exception:
            if fallback_factory is not None:
                return fallback_factory()
            raise
