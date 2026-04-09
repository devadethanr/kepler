from __future__ import annotations

import asyncio

from swingtradev3.llm.tool_executor import ToolExecutor
from swingtradev3.models import AccountState, StatsSnapshot


def test_decode_json_text_accepts_fenced_json() -> None:
    decoded = ToolExecutor._decode_json_text(
        """```json
{"score": 8.4, "setup_type": "breakout", "entry_zone": {"low": 100, "high": 101}, "stop_price": 95, "target_price": 110, "holding_days_expected": 10, "confidence_reasoning": "ok", "risk_flags": []}
```"""
    )

    assert decoded["score"] == 8.4


def test_decode_json_text_extracts_json_from_extra_text() -> None:
    decoded = ToolExecutor._decode_json_text(
        'Here is the result:\n{"score": 8.1, "setup_type": "pullback", "entry_zone": {"low": 99, "high": 100}, "stop_price": 95, "target_price": 108, "holding_days_expected": 12, "confidence_reasoning": "ok", "risk_flags": []}\nEnd.'
    )

    assert decoded["setup_type"] == "pullback"


class StubRouter:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_tools: list[object] = []

    async def complete(
        self,
        role: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        self.calls += 1
        self.seen_tools.append(tools)
        if tools is None:
            return {
                "response": {
                    "choices": [
                        {
                            "message": {
                                "content": '{"score": 8.2, "setup_type": "breakout", "entry_zone": {"low": 100, "high": 101}, "stop_price": 95, "target_price": 110, "holding_days_expected": 10, "confidence_reasoning": "prefetched", "risk_flags": []}'
                            }
                        }
                    ]
                }
            }
        if self.calls == 1:
            return {
                "response": {
                    "choices": [
                        {
                            "message": {
                                "content": "",
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "get_fundamentals",
                                            "arguments": '{"ticker":"INFY"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            }
        return {
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": '{"score": 8.9, "setup_type": "breakout", "entry_zone": {"low": 100, "high": 101}, "stop_price": 95, "target_price": 110, "holding_days_expected": 10, "confidence_reasoning": "tool-backed", "risk_flags": []}'
                        }
                    }
                ]
            }
        }

    @staticmethod
    def extract_text(payload: dict[str, object]) -> str:
        return payload["response"]["choices"][0]["message"]["content"]  # type: ignore[index]

    @staticmethod
    def extract_tool_calls(payload: dict[str, object]) -> list[dict[str, object]]:
        return payload["response"]["choices"][0]["message"].get("tool_calls", [])  # type: ignore[index]


class StubPromptBuilder:
    def build_research_messages(
        self,
        stock_context: dict[str, object],
        state: AccountState,
        stats: StatsSnapshot,
    ) -> list[dict[str, str]]:
        return [{"role": "system", "content": "stub"}, {"role": "user", "content": "stub"}]


def test_score_stock_supports_tool_call_loop() -> None:
    tool_executor = ToolExecutor(
        router=StubRouter(),
        prompt_builder=StubPromptBuilder(),
        tool_registry={"get_fundamentals": lambda ticker: {"ticker": ticker, "sector": "Technology"}},
        research_tool_schemas=[],
    )

    decision = asyncio.run(
        tool_executor.score_stock(
            ticker="INFY",
            stock_context={"close": 100.0, "sector": "Technology"},
            state=AccountState(),
            stats=StatsSnapshot(),
            skill_version="test123",
        )
    )

    assert decision.ticker == "INFY"
    assert decision.score == 8.9
    assert decision.confidence_reasoning == "tool-backed"


def test_score_stock_can_disable_tool_calls() -> None:
    router = StubRouter()
    tool_executor = ToolExecutor(
        router=router,
        prompt_builder=StubPromptBuilder(),
        tool_registry={"get_fundamentals": lambda ticker: {"ticker": ticker, "sector": "Technology"}},
        research_tool_schemas=[{"type": "function", "function": {"name": "get_fundamentals"}}],
    )

    decision = asyncio.run(
        tool_executor.score_stock(
            ticker="INFY",
            stock_context={"close": 100.0, "sector": "Technology"},
            state=AccountState(),
            stats=StatsSnapshot(),
            skill_version="test123",
            allow_tool_calls=False,
        )
    )

    assert decision.ticker == "INFY"
    assert router.calls == 1
    assert router.seen_tools == [None]
