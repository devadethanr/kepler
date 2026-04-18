from __future__ import annotations

from google.adk.agents import LlmAgent

from config import cfg

from agents.learning.lesson_agent import lesson_agent
from agents.learning.reviewer import learning_reviewer
from agents.research.pipeline import research_pipeline

root_agent = LlmAgent(
    name="TradingCoordinator",
    model=cfg.llm.adk.root_model,
    instruction="""
    You are the coordinator of an autonomous swing trading system for Indian equities.
    Your job is to orchestrate research and learning agents.

    When asked to scan: delegate to ResearchPipeline.
    When asked to review trades: delegate to LearningReviewer.
    When asked for status: return current state from session.state.

    Always enforce risk management rules. Never allow trades that exceed
    max_risk_pct_per_trade or max_drawdown_pct.
    """,
    description="Main coordinator of the swing trading system",
    sub_agents=[
        research_pipeline,
        learning_reviewer,
        lesson_agent,
    ],
)
