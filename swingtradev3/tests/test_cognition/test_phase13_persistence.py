from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from cognition.slow_brain.evidence_assembler import EvidenceAssembler
from cognition.slow_brain.orchestrator import SlowBrainOrchestrator
from cognition.slow_brain.regime_synthesizer import RegimeSynthesizer
from memory.db import session_scope
from memory.repository import MemoryRepository


IST = ZoneInfo("Asia/Kolkata")


class FakeMemoryViews:
    def regime_snapshot_context(self, limit=3):
        return []

    def research_context_packet(self, ticker, *, setup_type=None):
        return {
            "ticker": ticker,
            "portfolio_risk": {"cash_inr": 100000.0, "drawdown_pct": 0.0, "weekly_loss_pct": 0.0},
            "open_positions": [],
            "effective_policy": {"new_entries_enabled": True},
            "stock": {"evidence": []},
            "similar_trades": [],
        }


@pytest.mark.asyncio
async def test_phase13_wait_decision_persists_entry_intent_without_approval():
    run_id = f"phase13-persist-wait:{datetime.now(IST).strftime('%H%M%S%f')}"
    state = {
        "regime": {"regime": "bull", "confidence": 0.8},
        "scan_results": [
            {
                "ticker": "PH13WAIT",
                "score": 8.0,
                "setup_type": "breakout",
                "entry_zone": {"low": 100.0, "high": 105.0},
                "stop_price": 95.0,
                "target_price": 112.0,
                "holding_days_expected": 5,
                "risk_flags": [],
                "sector": "Test",
                "research_date": "2026-05-17",
                "skill_version": run_id,
            }
        ],
        "stock_data": {},
    }
    memory_views = FakeMemoryViews()

    result = await SlowBrainOrchestrator(
        regime_synthesizer=RegimeSynthesizer(memory_views=memory_views),
        evidence_assembler=EvidenceAssembler(memory_views=memory_views),
    ).run(state, run_id=run_id, persist=True)

    assert result.approval_candidates == []
    assert result.decisions[0].entry_intent_status == "watching"

    with session_scope() as session:
        repo = MemoryRepository(session)
        run = repo.get_cognition_run(run_id)
        reports = repo.list_cognition_reports(run_id=run_id)
        intents = [
            item
            for item in repo.list_entry_intents()
            if item["ticker"] == "PH13WAIT"
            and item["payload"].get("slow_brain_run_id") == run_id
        ]

    assert run is not None
    assert run["status"] == "completed"
    assert {report["agent_name"] for report in reports} >= {
        "evidence_assembler",
        "thesis_agent",
        "skeptic_agent",
        "portfolio_risk_judge",
        "final_intent_judge",
    }
    assert intents
    assert intents[0]["status"] == "watching"
    assert intents[0]["approval_id"] is None


def test_phase13_repository_persists_session_plan():
    plan_id = f"session-plan:test:{datetime.now(IST).strftime('%H%M%S%f')}"
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_session_execution_plan(
            plan_id=plan_id,
            trading_date="2026-05-17",
            status="ready",
            payload={"plan_id": plan_id, "status": "ready"},
            source="test_phase13",
        )

    with session_scope() as session:
        latest = MemoryRepository(session).latest_session_execution_plan(
            trading_date="2026-05-17",
        )

    assert latest is not None
    assert latest["plan_id"] == plan_id
    assert latest["status"] == "ready"

