from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from config import LocalLLMConfig, cfg
from llm.router import LLMRouter
from llm_bridge import SmartRouter, _response_format_for_model


class TinyDecision(BaseModel):
    decision: str


def test_local_llm_config_applies_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_ENABLED", "true")
    monkeypatch.setenv("LLAMA_CPP_MODEL", "local-qwen.gguf")
    monkeypatch.setenv("LLAMA_CPP_BASE_URL", "http://host.docker.internal:8090/v1")
    monkeypatch.setenv("LLAMA_CPP_HEALTH_URL", "http://host.docker.internal:8090/health")
    monkeypatch.setenv("LLAMA_CPP_MAX_TOKENS", "777")

    local = LocalLLMConfig.model_validate({"enabled": False, "model": "from-yaml.gguf"})

    assert local.enabled is True
    assert local.model == "local-qwen.gguf"
    assert local.base_url == "http://host.docker.internal:8090/v1"
    assert local.health_url == "http://host.docker.internal:8090/health"
    assert local.max_tokens == 777


def test_llm_router_treats_llama_cpp_as_local_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    router = LLMRouter()

    monkeypatch.setattr(cfg.llm.local, "enabled", False)
    assert router._provider_has_credentials("llama_cpp") is False

    monkeypatch.setattr(cfg.llm.local, "enabled", True)
    assert router._provider_has_credentials("llama_cpp") is True


@pytest.mark.asyncio
async def test_llm_router_calls_host_llama_openai_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    router = LLMRouter()
    captured: dict[str, Any] = {}

    monkeypatch.setattr(cfg.llm.local, "base_url", "http://host.docker.internal:8090/v1")
    monkeypatch.setattr(cfg.llm.local, "api_key", "not-needed")

    async def fake_openai_call(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"provider": kwargs["provider"], "response": {"choices": []}}

    monkeypatch.setattr(router, "_call_openai_compatible", fake_openai_call)

    await router._call_provider(
        provider="llama_cpp",
        model="local-qwen.gguf",
        messages=[{"role": "user", "content": "hello"}],
        tools=None,
        temperature=0,
        max_tokens=64,
        response_format={"type": "json_object"},
    )

    assert captured["provider"] == "llama_cpp"
    assert captured["base_url"] == "http://host.docker.internal:8090/v1"
    assert captured["api_key"] == "not-needed"
    assert captured["model"] == "local-qwen.gguf"
    assert captured["response_format"] == {"type": "json_object"}


def test_local_structured_response_format_uses_pydantic_schema() -> None:
    response_format = _response_format_for_model(TinyDecision)

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "TinyDecision"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["properties"]["decision"]["type"] == "string"


@pytest.mark.asyncio
async def test_smart_router_prefers_and_validates_local_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cfg.llm.local, "enabled", True)
    monkeypatch.setattr(cfg.llm.local, "model", "local-qwen.gguf")
    monkeypatch.setattr(cfg.llm, "fallback_chain", [])

    router = SmartRouter(role="research")
    assert router.chain[0]["provider"] == "llama_cpp"

    async def fake_local_structured(**_kwargs: Any) -> str:
        return '{"decision": "WAIT"}'

    monkeypatch.setattr(router, "_attempt_local_structured", fake_local_structured)

    decision = await router.generate_structured(
        prompt="Use only provided data.",
        system_instruction="Return JSON.",
        response_model=TinyDecision,
    )

    assert decision == TinyDecision(decision="WAIT")
