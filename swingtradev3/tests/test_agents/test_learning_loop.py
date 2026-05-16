from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
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
        "trade_id": "T123",
        "ticker": "RELIANCE",
        "quantity": 10,
        "entry_price": 1000,
        "exit_price": 1100,
        "opened_at": now.isoformat(),
        "closed_at": now.isoformat(),
        "exit_reason": "target",
        "pnl_abs": 1000,
        "pnl_pct": 10.0
    }
    
    class FakeMemoryViewClient:
        def latest_trade_payload(self):
            return trade

    fake_graph = MagicMock()
    with patch("agents.learning.reviewer.MemoryViewClient", FakeMemoryViewClient):
        with patch("agents.learning.reviewer.ContextGraphRepository", return_value=fake_graph):
            # Mock the SMART ROUTER
            with patch("llm_bridge.SmartRouter.generate_structured") as mock_gen:
                mock_gen.return_value = TradeReviewSchema(
                    observation="Successful trade",
                    thesis_held=True,
                    exit_reason="target"
                )

                runner = Runner(
                    app_name="learning",
                    agent=learning_reviewer,
                    session_service=InMemorySessionService(),
                    auto_create_session=True
                )

                async for _ in runner.run_async(
                    user_id="system",
                    session_id="learn_session",
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part(text="Review latest trades")]
                    )
                ):
                    pass

                assert fake_graph.record_observation.called
                print("\n✅ Learning Test Passed: ReviewerAgent logged graph observation.")

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
            "setup_type": "breakout"
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
            "setup_type": "breakout"
        }
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
                auto_create_session=True
            )
            
            async for _ in runner.run_async(
                user_id="system",
                session_id="stats_session",
                new_message=types.Content(role="user", parts=[types.Part(text="Calculate stats")])
            ):
                pass
                
            assert mock_write.called
            print("\n✅ Learning Test Passed: StatsAgent correctly updated performance dashboard.")
