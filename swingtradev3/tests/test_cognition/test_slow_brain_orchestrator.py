from __future__ import annotations

import pytest

from cognition.slow_brain.evidence_assembler import EvidenceAssembler
from cognition.slow_brain.final_intent_judge import FinalIntentJudge
from cognition.slow_brain.orchestrator import SlowBrainOrchestrator
from cognition.slow_brain.regime_synthesizer import RegimeSynthesizer
from cognition.slow_brain.skeptic_agent import SkepticAgent
from cognition.slow_brain.thesis_agent import ThesisAgent
from cognition.llm_client import CognitionLLMClient


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


def _state(target: float = 140.0) -> dict[str, object]:
    return {
        "regime": {"regime": "bull", "confidence": 0.8},
        "scan_results": [
            {
                "ticker": "SBIN",
                "score": 8.5,
                "setup_type": "breakout",
                "entry_zone": {"low": 100.0, "high": 105.0},
                "stop_price": 95.0,
                "target_price": target,
                "holding_days_expected": 8,
                "confidence_reasoning": "test",
                "risk_flags": [],
                "sector": "Bank",
                "research_date": "2026-05-17",
                "skill_version": "phase13-test",
            }
        ],
        "stock_data": {"SBIN": {"news": [{"title": "SBIN news"}]}},
    }


def _orchestrator(memory_views: FakeMemoryViews) -> SlowBrainOrchestrator:
    llm = CognitionLLMClient(enabled=False)
    return SlowBrainOrchestrator(
        regime_synthesizer=RegimeSynthesizer(memory_views=memory_views),
        evidence_assembler=EvidenceAssembler(memory_views=memory_views),
        thesis_agent=ThesisAgent(llm_client=llm),
        skeptic_agent=SkepticAgent(llm_client=llm),
        final_judge=FinalIntentJudge(llm_client=llm),
    )


@pytest.mark.asyncio
async def test_slow_brain_orchestrator_produces_actionable_approval_candidate():
    memory_views = FakeMemoryViews()
    result = await _orchestrator(memory_views).run(
        _state(),
        run_id="phase13-orchestrator-actionable",
        persist=False,
    )

    assert result.status == "completed"
    assert result.decisions[0].decision == "BUY_ONLY_ABOVE_TRIGGER"
    assert len(result.approval_candidates) == 1
    assert result.approval_candidates[0]["slow_brain_run_id"] == result.run_id


@pytest.mark.asyncio
async def test_slow_brain_orchestrator_wait_for_pullback_has_no_approval_candidate():
    memory_views = FakeMemoryViews()
    result = await _orchestrator(memory_views).run(
        _state(target=112.0),
        run_id="phase13-orchestrator-wait",
        persist=False,
    )

    assert result.decisions[0].decision == "WAIT_FOR_PULLBACK"
    assert result.approval_candidates == []
