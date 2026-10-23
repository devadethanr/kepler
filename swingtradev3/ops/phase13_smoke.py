from __future__ import annotations

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from cognition.pre_market.session_planner import SessionPlanner
from cognition.slow_brain.orchestrator import SlowBrainOrchestrator


IST = ZoneInfo("Asia/Kolkata")


def _sample_state() -> dict[str, object]:
    return {
        "regime": {"regime": "bull", "confidence": 0.7, "summary": "Smoke-test regime"},
        "scan_results": [
            {
                "ticker": "SBIN",
                "score": 8.2,
                "setup_type": "breakout",
                "entry_zone": {"low": 820.0, "high": 825.0},
                "stop_price": 800.0,
                "target_price": 880.0,
                "holding_days_expected": 8,
                "confidence_reasoning": "Smoke candidate",
                "risk_flags": [],
                "sector": "Financials",
                "research_date": datetime.now(IST).date().isoformat(),
                "skill_version": "phase13-smoke",
            }
        ],
        "stock_data": {"SBIN": {"news": []}},
    }


async def _run() -> None:
    result = await SlowBrainOrchestrator().run(
        _sample_state(),
        run_id=f"slow-brain-smoke:{datetime.now(IST).strftime('%Y%m%d%H%M%S')}",
        persist=False,
    )
    plan = SessionPlanner().build_plan(
        approvals=result.approval_candidates,
        apply=False,
        persist=False,
    )
    print(
        json.dumps(
            {
                "slow_brain_status": result.status,
                "decisions": [decision.model_dump(mode="json") for decision in result.decisions],
                "approval_candidates": len(result.approval_candidates),
                "session_plan_status": plan.status,
                "session_plan_items": [item.model_dump(mode="json") for item in plan.items],
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    asyncio.run(_run())

