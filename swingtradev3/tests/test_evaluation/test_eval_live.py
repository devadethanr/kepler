from __future__ import annotations

import pytest
import json
import time
from unittest.mock import patch
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent
from google.genai import types
from config import cfg

from tools.market.market_data import MarketDataTool
from tools.market.fundamental_data import FundamentalDataTool
from tools.market.news_search import NewsSearchTool
from agents.research.scorer_agent import ScorerAgent

@pytest.mark.asyncio
async def test_live_hallucination_check():
    """
    Live Evaluation: Fetches REAL data for a stock, scores it using the ScorerAgent, 
    and then uses an LLM-as-a-Judge to verify the ScorerAgent didn't hallucinate.
    """
    ticker = "RELIANCE"
    print(f"\n🚀 [LIVE EVAL] Starting the audit for {ticker}... buckle up!")
    
    # 1. Fetch REAL data
    print(f"🕵️ [LIVE EVAL] Step 1: Going on a data-hunting expedition...")
    with patch("config.cfg.trading.mode", type('MockMode', (), {'value': 'live'})()):
        market_tool = MarketDataTool()
        fund_tool = FundamentalDataTool()
        news_tool = NewsSearchTool()
        
        print(f"📊 [LIVE EVAL] Grabbing technicals for {ticker}... (this usually takes a few blinks)")
        tech_data = await market_tool.get_eod_data_async(ticker)
        print(f"📈 [LIVE EVAL] Technical data captured! Price is currently {tech_data.get('close')}")
        
        print(f"🏢 [LIVE EVAL] Digging into the fundamentals... (checking if they have more debt than a college student)")
        fund_data = fund_tool.get_fundamentals(ticker)
        print(f"💎 [LIVE EVAL] Fundamental data found! PE Ratio: {fund_data.get('pe_ratio')}")
        
        print(f"📰 [LIVE EVAL] Sweeping the internet for gossip/news on {ticker}...")
        news_data = news_tool.search_news(f"{ticker} stock news India last 7 days")
        print(f"🗞️ [LIVE EVAL] News sweep complete! Found {len(news_data.get('results', []))} headlines to analyze.")
    
    # 2. Run ScorerAgent with live context via Runner
    print(f"🧠 [LIVE EVAL] Step 2: Waking up the ScorerAgent's brain cells...")
    session_service = InMemorySessionService()
    scorer_agent = ScorerAgent()
    runner = Runner(
        app_name="research",
        agent=scorer_agent,
        session_service=session_service,
        auto_create_session=True
    )
    
    initial_state = {
        "qualified_stocks": [{"ticker": ticker, "signals": {"news": True}}],
        "stock_data": {
            ticker: {
                "technical": tech_data,
                "fundamentals": fund_data,
                "sentiment": news_data,
                "options": {},
                "timesfm": {}
            }
        }
    }
    
    await session_service.create_session(
        app_name="research",
        user_id="user_live",
        session_id="session_live",
        state=initial_state
    )
    
    print(f"🎲 [LIVE EVAL] Asking the ScorerAgent to grade {ticker}... (Thinking hard...)")
    async for event in runner.run_async(
        user_id="user_live",
        session_id="session_live",
        new_message=types.Content(role="user", parts=[types.Part(text=f"Score {ticker}")])
    ):
        pass
        
    session = await session_service.get_session(app_name="research", user_id="user_live", session_id="session_live")
    all_scored = session.state.get("scan_results", [])
    assert len(all_scored) == 1, f"🔥 Scoring failed for {ticker}. Scorer went on strike (Results empty)."
    scorer_output = all_scored[0]
    print(f"🎯 [LIVE EVAL] Scorer assigned a score of {scorer_output.get('score')}!")
    
    # 3. LLM-as-a-Judge (Hallucination Eval)
    print(f"👨‍⚖️ [LIVE EVAL] Step 3: Summoning the Hallucination Judge to audit the facts...")
    judge_llm = LlmAgent(
        name="HallucinationJudge",
        model=cfg.llm.adk.judge_model,
        instruction="""
        You are a factual auditor for an AI trading system.
        
        GOAL: Detect if the agent invented data that isn't in the 'Ground Truth'.
        
        STRICT DEFINITION OF HALLUCINATION:
        1. Inventing specific prices, earnings numbers, or news events not in the data.
        2. Saying a stock is "Above 200 EMA" when the data shows it is below.
        
        WHAT IS NOT A HALLUCINATION:
        1. A low score (e.g. 1.0). That is a valid analyst opinion.
        2. Negative reasoning (e.g. "Broken Structure"). That is valid risk management.
        3. Differences in technical interpretation (e.g. "Strong downtrend" vs "Choppy").
        
        Respond ONLY with JSON: 
        {"hallucination_detected": true/false, "explanation": "..."}
        """,
        description="Audit agent for factual grounding"
    )
    
    judge_runner = Runner(
        app_name="research",
        agent=judge_llm,
        session_service=InMemorySessionService(),
        auto_create_session=True
    )
    
    prompt = f"""
    ### GROUND TRUTH DATA:
    Technical Data: {json.dumps(tech_data, default=str)}
    News Articles: {json.dumps(news_data.get("results", []), default=str)}
    
    ### AGENT OUTPUT TO AUDIT:
    {json.dumps(scorer_output, default=str)}
    """
    
    print(f"🔦 [LIVE EVAL] Judge is shining a light on the Scorer's reasoning...")
    response_text = ""
    async for event in judge_runner.run_async(
        user_id="judge_user",
        session_id="judge_session",
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)])
    ):
        if event.is_final_response():
            content = event.content
            if hasattr(content, "parts") and content.parts:
                response_text = content.parts[0].text or ""
            else:
                response_text = str(content)
            
    # Parse JSON
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
        
    start = response_text.find("{")
    end = response_text.rfind("}")
    if start != -1 and end != -1:
        response_text = response_text[start:end+1]
        
    judge_result = json.loads(response_text)
    assert judge_result["hallucination_detected"] is False, f"🚨 HALLUCINATION DETECTED! Judge says: {judge_result.get('explanation')}"
    print(f"✨ [LIVE EVAL] Audit Complete! Scorer reasoning for {ticker} is 100% FACTUAL. No hallucinations found.")
