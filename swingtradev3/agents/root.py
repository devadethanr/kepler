from __future__ import annotations

from google.adk.agents import LlmAgent

from config import cfg

# Assuming research_pipeline is available
from agents.research.pipeline import research_pipeline

# The execution and learning agents will be added in Phase 3
root_agent = LlmAgent(
    name="TradingCoordinator",
    model=cfg.llm.adk.root_model,
    instruction="""
    You are the coordinator of an autonomous swing trading system for Indian equities.
    Your job is to orchestrate research, execution, and learning agents.

    When asked to scan: delegate to ResearchPipeline.
    When asked to monitor positions: delegate to ExecutionMonitor.
    When asked to review trades: delegate to LearningReviewer.
    When asked for status: return current state from session.state.

    Always enforce risk management rules. Never allow trades that exceed
    max_risk_pct_per_trade or max_drawdown_pct.
    """,
    description="Main coordinator of the swing trading system",
    sub_agents=[
        research_pipeline,
        # execution_monitor,
        # order_agent,
        # learning_reviewer,
        # lesson_agent,
    ],
)
