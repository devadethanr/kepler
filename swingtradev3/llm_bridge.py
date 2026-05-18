from __future__ import annotations

from typing import Any, Type, TypeVar
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import httpx
from google.adk.models.registry import LLMRegistry
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from google.genai.errors import ServerError

from config import cfg
from health_manager import update_service_status

T = TypeVar("T", bound=BaseModel)


def _provider_health_key(provider: str) -> str:
    if provider == cfg.llm.local.provider:
        return "local_llm"
    if provider in ("openai", "nim"):
        return "nvidia_nim"
    return "google_gemini"


def _response_format_for_model(response_model: Type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": response_model.__name__,
            "strict": True,
            "schema": response_model.model_json_schema(),
        },
    }


class SmartRouter:
    """
    Universal LLM Router with built-in retries and provider fallbacks.
    Logic: Try NIM (via OpenAI prefix) -> Fallback to Gemini if needed.
    """
    def __init__(self, role: str = "research"):
        self.role = role
        self.chain = list(cfg.llm.fallback_chain)
        if cfg.llm.local.enabled:
            local_entry = {"provider": cfg.llm.local.provider, "model": cfg.llm.local.model}
            has_local = any(
                (entry.provider if hasattr(entry, "provider") else entry.get("provider"))
                == cfg.llm.local.provider
                for entry in self.chain
            )
            if not has_local:
                self.chain.insert(0, local_entry)
        if not self.chain:
            # Hardcoded defaults if config is empty
            self.chain = [
                {"provider": "openai", "model": cfg.llm.adk.research_model},
                {"provider": "gemini", "model": "gemini-2.0-flash"}
            ]

    @retry(
        retry=retry_if_exception_type((ServerError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _attempt_call(self, model_str: str, provider: str, llm_request: LlmRequest) -> str:
        """Single attempt at an LLM call with retry on 503/500 errors."""
        try:
            llm = LLMRegistry.new_llm(model_str)
            response_text = ""
            
            async for response in llm.generate_content_async(llm_request):
                if response.content and response.content.parts:
                    response_text = response.content.parts[0].text or ""
            
            if response_text:
                # Update health manager on success
                # Map provider names to health_manager keys using provider param
                update_service_status(_provider_health_key(provider), True)
                return response_text
            
            raise ValueError("Empty response from model")
            
        except Exception as e:
            # Log failure but the @retry decorator will handle the re-attempt if it's a ServerError
            raise e

    @retry(
        retry=retry_if_exception_type((httpx.HTTPStatusError, ValueError)),
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _attempt_local_structured(
        self,
        *,
        model: str,
        prompt: str,
        system_instruction: str,
        response_model: Type[T],
    ) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for local llama.cpp access") from exc

        client = AsyncOpenAI(
            api_key=cfg.llm.local.api_key,
            base_url=cfg.llm.local.base_url,
            timeout=cfg.llm.local.timeout_seconds,
            max_retries=cfg.llm.local.max_retries,
        )
        payload: dict[str, Any] = {
            "model": model or cfg.llm.local.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": cfg.llm.local.max_tokens,
        }
        if cfg.llm.local.structured_output:
            payload["response_format"] = _response_format_for_model(response_model)

        response = await client.chat.completions.create(**payload)
        content = response.choices[0].message.content if response.choices else ""
        if not content:
            raise ValueError("Empty content from local llama.cpp response")
        update_service_status("local_llm", True)
        return content

    async def generate_structured(
        self, 
        prompt: str, 
        system_instruction: str, 
        response_model: Type[T]
    ) -> T:
        """
        Runs through the fallback chain until a successful structured response is received.
        """
        last_error = None
        
        for entry in self.chain:
            # entry might be a dict or a Pydantic model (LLMFallbackConfig)
            provider = entry.provider if hasattr(entry, "provider") else entry.get("provider")
            model_name = entry.model if hasattr(entry, "model") else entry.get("model")
            
            if not model_name:
                continue

            full_model_str = model_name

            if provider == cfg.llm.local.provider:
                try:
                    raw_json = await self._attempt_local_structured(
                        model=full_model_str,
                        prompt=prompt,
                        system_instruction=system_instruction,
                        response_model=response_model,
                    )
                    return response_model.model_validate_json(raw_json)
                except Exception as e:
                    print(f"DEBUG ROUTER: {full_model_str} failed: {e}")
                    update_service_status("local_llm", False, str(e))
                    last_error = e
                    continue

            llm_request = LlmRequest(
                model=full_model_str,
                contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_model,
                    temperature=0.1
                )
            )

            try:
                print(f"DEBUG ROUTER: Attempting {full_model_str} (Provider: {provider})...")
                # Attempt with built-in tenacity retry
                raw_json = await self._attempt_call(full_model_str, provider, llm_request)
                
                # Parse and validate
                return response_model.model_validate_json(raw_json)
                
            except Exception as e:
                print(f"DEBUG ROUTER: {full_model_str} failed: {e}")
                # Update health manager
                update_service_status(_provider_health_key(provider), False, str(e))
                last_error = e
                continue # Try next in chain
        
        raise RuntimeError(f"All LLM providers in fallback chain failed. Last error: {last_error}")
