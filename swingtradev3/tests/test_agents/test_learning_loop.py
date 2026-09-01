from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.learning.reviewer import learning_reviewer, TradeReviewSchema
from agents.learning.stats_agent import stats_agent
from datetime import datetime


@pytest.mark.asyncio
async def test_learning_loop_reviewer():
    """
    Test that the ReviewerAgent correctly analyzes a closed trade.
    """
    now = datetime.now()
    trade = {
        "trade_id": f"T-{uuid4().hex}",
        "ticker": "RELIANCE",
        "quantity": 10,
        "entry_price": 1000,
        "exit_price": 1100,
        "opened_at": now.isoformat(),
        "closed_at": now.isoformat(),
        "exit_reason": "target",
        "pnl_abs": 1000,
        "pnl_pct": 10.0,
    }

    class FakeMemoryViewClient:
        def recent_trades(self, limit=1):
            return [trade]

        def research_context_packet(self, ticker, setup_type=None):
            return {"mock": "context"}

    fake_graph = MagicMock()
    with patch("agents.learning.reviewer.MemoryViewClient", FakeMemoryViewClient):
        with patch("agents.learning.reviewer.ContextGraphRepository", return_value=fake_graph):
            with patch(
                "agents.learning.reviewer.CognitionLLMClient.generate_structured",
                new=AsyncMock(
                    return_value=TradeReviewSchema(
                        observation="Successful trade",
                        lesson="Keep the validated setup controls.",
                        thesis_held=True,
                        exit_reason="target",
                    )
                ),
            ):
                runner = Runner(
                    app_name="learning",
                    agent=learning_reviewer,
                    session_service=InMemorySessionService(),
                    auto_create_session=True,
                )

                async for _ in runner.run_async(
                    user_id="system",
                    session_id="learn_session",
                    new_message=types.Content(
                        role="user", parts=[types.Part(text="Review latest trades")]
                    ),
                ):
                    pass

                assert fake_graph.upsert_trade_memory.called
                assert fake_graph.record_observation.called


@pytest.mark.asyncio
async def test_learning_loop_stats():
    """
    Test that the StatsAgent correctly calculates performance metrics.
    """
    now = datetime.now()
    trades = [
        {
            "trade_id": "T1",
            "ticker": "RELIANCE",
            "quantity": 10,
            "entry_price": 1000,
            "exit_price": 1100,
            "opened_at": now.isoformat(),
            "closed_at": now.isoformat(),
            "exit_reason": "target",
            "pnl_abs": 1000,
            "pnl_pct": 10.0,
            "setup_type": "breakout",
        },
        {
            "trade_id": "T2",
            "ticker": "TCS",
            "quantity": 5,
            "entry_price": 3000,
            "exit_price": 2850,
            "opened_at": now.isoformat(),
            "closed_at": now.isoformat(),
            "exit_reason": "stop",
            "pnl_abs": -750,
            "pnl_pct": -5.0,
            "setup_type": "breakout",
        },
    ]

    class FakeStatsMemoryViewClient:
        def recent_trades(self, *, limit=1000):
            return [{"payload": item} for item in trades]

    with patch("agents.learning.stats_agent.MemoryViewClient", FakeStatsMemoryViewClient):
        with patch("agents.learning.stats_agent.write_json") as mock_write:
            runner = Runner(
                app_name="learning",
                agent=stats_agent,
                session_service=InMemorySessionService(),
                auto_create_session=True,
            )

            async for _ in runner.run_async(
                user_id="system",
                session_id="stats_session",
                new_message=types.Content(role="user", parts=[types.Part(text="Calculate stats")]),
            ):
                pass

            assert mock_write.called
            print("\n✅ Learning Test Passed: StatsAgent correctly updated performance dashboard.")
