from __future__ import annotations

import pytest
import json
import uuid
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.research.scorer_agent import ScorerAgent

@pytest.mark.asyncio
async def test_scorer_rejects_bad_fundamentals():
    """
    Mock Evaluation: We provide terrible fundamentals and a bearish trend.
    """
    session_service = InMemorySessionService()
    agent = ScorerAgent()
    runner = Runner(
        app_name="research", # MUST MATCH AGENT APP NAME
        agent=agent,
        session_service=session_service,
        auto_create_session=True
    )
    
    u_id = f"user_{uuid.uuid4().hex[:8]}"
    s_id = f"sess_{uuid.uuid4().hex[:8]}"
    
    initial_state = {
        "qualified_stocks": [{"ticker": "TERRIBLE", "signals": {"news": False}}],
        "stock_data": {
            "TERRIBLE": {
                "technical": {"close": 100, "ema_200": 150, "above_200ema": False, "rsi_14": 25, "volume_ratio": 0.4},
                "fundamentals": {"pe_ratio": 300, "debt_equity": 5.5, "promoter_pledge_pct": 75.0, "revenue_growth_pct": -10.0},
                "sentiment": {"sentiment_score": -0.8, "sentiment_label": "bearish", "catalyst_type": ["regulatory"]},
                "options": {"pcr": 0.4, "pcr_signal": "bearish"},
                "timesfm": {"forecast_direction": "down", "forecast_pct_change": -15.0}
            }
        }
    }
    
    await session_service.create_session(
        app_name="research",
        user_id=u_id,
        session_id=s_id,
        state=initial_state
    )
    
    async for event in runner.run_async(
        user_id=u_id,
        session_id=s_id,
        new_message=types.Content(role="user", parts=[types.Part(text="Score stocks")])
    ):
        pass
        
    session = await session_service.get_session(app_name="research", user_id=u_id, session_id=s_id)
    shortlist = session.state.get("shortlist", [])
    assert len(shortlist) == 0
    print(f"\n✅ Mock Evaluation Passed: Scorer correctly excluded terrible stock from shortlist.")

@pytest.mark.asyncio
async def test_scorer_accepts_perfect_setup():
    """
    Mock Evaluation: We provide perfect fundamentals and a bullish trend.
    """
    session_service = InMemorySessionService()
    agent = ScorerAgent()
    runner = Runner(
        app_name="research", # MUST MATCH AGENT APP NAME
        agent=agent,
        session_service=session_service,
        auto_create_session=True
    )
    
    u_id = f"user_{uuid.uuid4().hex[:8]}"
    s_id = f"sess_{uuid.uuid4().hex[:8]}"
    
    initial_state = {
        "qualified_stocks": [{"ticker": "PERFECT", "signals": {"news": True, "fii": True}}],
        "stock_data": {
            "PERFECT": {
                "technical": {
                    "close": 150, "ema_200": 100, "above_200ema": True, 
                    "rsi_14": 62, "volume_ratio": 3.5, "trend_strong": True,
                    "support_level": 145, "resistance_level": 180
                },
                "fundamentals": {
                    "pe_ratio": 12, "debt_equity": 0.05, "promoter_pledge_pct": 0.0, 
                    "eps_growth_3yr_pct": 35.0, "revenue_growth_pct": 25.0,
                    "roe_pct": 22.0, "sector": "Quality Compounders"
                },
                "sentiment": {
                    "sentiment_score": 0.95, "sentiment_label": "bullish", 
                    "catalyst_type": ["earnings_beat", "new_contract", "upgrade"],
                    "summary": "Record quarterly profits and massive new government contract signed."
                },
                "options": {"pcr": 1.6, "pcr_signal": "strong_bullish"},
                "timesfm": {"forecast_direction": "up", "forecast_pct_change": 12.0}
            }
        }
    }
    
    await session_service.create_session(
        app_name="research",
        user_id=u_id,
        session_id=s_id,
        state=initial_state
    )
    
    response_text = ""
    async for event in runner.run_async(
        user_id=u_id,
        session_id=s_id,
        new_message=types.Content(role="user", parts=[types.Part(text="Score stocks")])
    ):
        if event.is_final_response():
            content = event.content
            if hasattr(content, "parts") and content.parts:
                response_text = content.parts[0].text or ""
            else:
                response_text = str(content)
    
    if response_text:
        print(f"\nRAW AI RESPONSE:\n{response_text}\n")
        
    session = await session_service.get_session(app_name="research", user_id=u_id, session_id=s_id)
    all_scored = session.state.get("scan_results", [])
    
    if not all_scored:
        print(f"DEBUG: Final session state keys: {list(session.state.keys())}")
        
    assert len(all_scored) == 1
    stock_res = all_scored[0]
    assert stock_res["score"] >= 7.0
    print(f"\n✅ Mock Evaluation Passed: Scorer assigned high score {stock_res['score']} to perfect stock.")
