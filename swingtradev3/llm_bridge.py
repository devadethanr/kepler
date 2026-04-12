from __future__ import annotations

import json
import asyncio
from typing import Any, Type, TypeVar, AsyncGenerator
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from google.adk.models.registry import LLMRegistry
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from google.genai.errors import ServerError

from config import cfg
from health_manager import update_service_status

T = TypeVar("T", bound=BaseModel)

class SmartRouter:
    """
    Universal LLM Router with built-in retries and provider fallbacks.
    Logic: Try NIM (via OpenAI prefix) -> Fallback to Gemini if needed.
    """
    def __init__(self, role: str = "research"):
        self.role = role
        # Get fallback chain from config
        self.chain = cfg.llm.fallback_chain
        if not self.chain:
            # Hardcoded defaults if config is empty
            self.chain = [
                {"provider": "openai", "model": cfg.llm.adk.research_model},
                {"provider": "gemini", "model": "gemini-2.0-flash"}
            ]

    @retry(
        retry=retry_if_exception_type(ServerError),
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
                # Map provider names to health_manager keys
                service_key = "nvidia_nim" if "meta" in model_str else "google_gemini"
                update_service_status(service_key, True)
                return response_text
            
            raise ValueError("Empty response from model")
            
        except Exception as e:
            # Log failure but the @retry decorator will handle the re-attempt if it's a ServerError
            raise e

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
                service_key = "nvidia_nim" if provider == "nim" else "google_gemini"
                update_service_status(service_key, False, str(e))
                last_error = e
                continue # Try next in chain
        
        raise RuntimeError(f"All LLM providers in fallback chain failed. Last error: {last_error}")
