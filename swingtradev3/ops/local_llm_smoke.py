from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from config import cfg


class LocalLLMSmokeDecision(BaseModel):
    decision: Literal["WAIT", "AVOID_NO_TRADE"]
    confidence_score: int = Field(ge=0, le=10)
    reason: str


def _urlopen_json(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _models_url() -> str:
    return f"{cfg.llm.local.base_url.rstrip('/')}/models"


def _schema_response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "local_llm_smoke_decision",
            "strict": True,
            "schema": LocalLLMSmokeDecision.model_json_schema(),
        },
    }


async def _run_structured_smoke() -> LocalLLMSmokeDecision:
    client = AsyncOpenAI(
        api_key=cfg.llm.local.api_key,
        base_url=cfg.llm.local.base_url,
        timeout=cfg.llm.local.timeout_seconds,
        max_retries=cfg.llm.local.max_retries,
    )
    response = await client.chat.completions.create(
        model=cfg.llm.local.model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only valid JSON matching the schema. Use only the provided data. "
                    "Do not reveal chain of thought."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Given no live market data is provided, choose WAIT or AVOID_NO_TRADE. "
                    "Keep the reason short."
                ),
            },
        ],
        temperature=0,
        top_p=1,
        max_tokens=min(cfg.llm.local.max_tokens, 240),
        response_format=_schema_response_format(),
    )
    content = response.choices[0].message.content if response.choices else ""
    if not content:
        raise RuntimeError("local llama.cpp returned empty message.content")
    return LocalLLMSmokeDecision.model_validate_json(content)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the host llama.cpp server.")
    parser.add_argument("--health-only", action="store_true")
    args = parser.parse_args()

    timeout = min(cfg.llm.local.timeout_seconds, 3.0)
    print(f"local_llm.enabled={cfg.llm.local.enabled}")
    print(f"health_url={cfg.llm.local.health_url}")
    print(f"base_url={cfg.llm.local.base_url}")
    print(f"model={cfg.llm.local.model}")

    health = _urlopen_json(cfg.llm.local.health_url, timeout=timeout)
    print(f"health={health}")

    models = _urlopen_json(_models_url(), timeout=timeout)
    model_ids = [item.get("id") or item.get("model") or item.get("name") for item in models.get("data", [])]
    if not model_ids and isinstance(models.get("models"), list):
        model_ids = [item.get("model") or item.get("name") for item in models["models"]]
    print(f"models={model_ids}")

    if args.health_only:
        return 0
    if not cfg.llm.local.enabled:
        print("LOCAL_LLM_ENABLED=false; enable it before running the structured smoke.")
        return 1

    decision = asyncio.run(_run_structured_smoke())
    print(decision.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
