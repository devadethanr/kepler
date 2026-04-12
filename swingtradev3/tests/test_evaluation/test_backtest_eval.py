from __future__ import annotations

import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import patch

from backtest.engine import BacktestEngine, BacktestState
from agents.research.pipeline import research_pipeline
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

class ADKBacktestEngine(BacktestEngine):
    """
    An enhanced BacktestEngine that uses the actual ADK research_pipeline
    to generate signals instead of hardcoded rules.
    """
    async def _check_signals_adk(self, ctx, ticker: str, df: pd.DataFrame, day_idx: int):
        # 1. Prepare context for the agent from historical data row
        row = df.iloc[day_idx]
        
        # We manually populate the session state
        ctx.session.state["qualified_stocks"] = [{"ticker": ticker, "signals": {"backtest": True}}]
        ctx.session.state["stock_data"] = {
            ticker: {
                "technical": row.to_dict(),
                "fundamentals": {"pe_ratio": 15, "debt_equity": 0.2}, 
                "sentiment": {"sentiment_score": 0.5},
                "options": {},
                "timesfm": {}
            }
        }
        
        # 2. Run the actual ADK scorer part of the pipeline
        from agents.research.scorer_agent import ScorerAgent
        scorer = ScorerAgent()
        
        async for event in scorer._run_async_impl(ctx):
            pass
            
        return ctx.session.state.get("shortlist", [])

@pytest.mark.asyncio
async def test_backtest_integration_with_adk():
    """
    Evaluation: Verifies that the Backtest engine can successfully 
    interface with the ADK agent logic to score trades.
    """
    engine = ADKBacktestEngine()
    
    ticker = "RELIANCE"
    dates = pd.date_range("2026-01-01", periods=100, freq="B")
    data = pd.DataFrame({
        "date": dates,
        "open": [100 + i for i in range(100)],
        "high": [105 + i for i in range(100)],
        "low": [95 + i for i in range(100)],
        "close": [102 + i for i in range(100)],
        "volume": [1000000 for _ in range(100)]
    })
    data.name = ticker
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.session = type('MockSession', (), {'state': {}, 'id': 'backtest_session'})()
            self.user_content = None
            
    ctx = MockContext()
    
    # Test if we can get a signal using ADK logic for day 70
    with patch("google.adk.agents.LlmAgent.run_async") as mock_run:
        from unittest.mock import MagicMock
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = '{"score": 8.5, "setup_type": "breakout", "entry_zone": {"low": 170, "high": 175}, "stop_price": 160, "target_price": 200, "reasoning": "Strong trend"}'
        
        async def mock_gen(*args, **kwargs):
            yield mock_event
        mock_run.return_value = mock_gen()
        
        signals = await engine._check_signals_adk(ctx, ticker, data, 70)
        
        assert len(signals) == 1
        assert signals[0]["ticker"] == ticker
        assert signals[0]["score"] == 8.5
        print(f"\n✅ Backtest Evaluation Passed: Backtest engine successfully invoked ADK ScorerAgent.")
