from __future__ import annotations

import pytest

from cognition.slow_brain.final_intent_judge import FinalIntentJudge
from cognition.types import (
    CandidateContextV1,
    PortfolioFitReport,
    SkepticReport,
    ThesisReport,
    UniverseFunnelCandidate,
)


@pytest.fixture(autouse=True)
def disable_local_llm(monkeypatch):
    async def mock_generate_structured(
        self, *, prompt, system_instruction, response_model, fallback_factory=None
    ):
        return fallback_factory()

    monkeypatch.setattr(
        "cognition.llm_client.CognitionLLMClient.generate_structured", mock_generate_structured
    )
    yield


def _context(target: float = 140.0) -> CandidateContextV1:
    return CandidateContextV1(
        run_id="phase13-final",
        ticker="SBIN",
        scan_date="2026-05-17",
        candidate=UniverseFunnelCandidate(
            ticker="SBIN",
            score=8.5,
            setup_type="breakout",
            candidate_payload={
                "ticker": "SBIN",
                "score": 8.5,
                "setup_type": "breakout",
                "entry_zone": {"low": 100.0, "high": 105.0},
                "stop_price": 95.0,
                "target_price": target,
                "holding_days_expected": 8,
                "risk_flags": [],
            },
        ),
    )


@pytest.mark.asyncio
async def test_final_intent_judge_accepts_breakout_trigger_when_rr_passes():
    decision = await FinalIntentJudge().decide(
        context=_context(),
        regime=_context().regime,
        thesis=ThesisReport(ticker="SBIN", confidence_score=8, report_id="thesis"),
        skeptic=SkepticReport(ticker="SBIN", verdict="PASS", report_id="skeptic"),
        portfolio=PortfolioFitReport(ticker="SBIN", fit="ACCEPTABLE", report_id="portfolio"),
    )

    assert decision.decision == "BUY_ONLY_ABOVE_TRIGGER"
    assert decision.actionable_for_approval is True


@pytest.mark.asyncio
async def test_final_intent_judge_waits_when_rr_is_poor():
    context = _context(target=112.0)
    decision = await FinalIntentJudge().decide(
        context=context,
        regime=context.regime,
        thesis=ThesisReport(ticker="SBIN", confidence_score=8),
        skeptic=SkepticReport(ticker="SBIN", verdict="PASS"),
        portfolio=PortfolioFitReport(ticker="SBIN", fit="ACCEPTABLE"),
    )

    assert decision.decision == "WAIT_FOR_PULLBACK"
    assert "poor_current_rr" in decision.risk_flags


@pytest.mark.asyncio
async def test_final_intent_judge_rejects_skeptic_veto():
    context = _context()
    decision = await FinalIntentJudge().decide(
        context=context,
        regime=context.regime,
        thesis=ThesisReport(ticker="SBIN", confidence_score=8),
        skeptic=SkepticReport(ticker="SBIN", verdict="VETO", risks=["invalid_stop_above_entry"]),
        portfolio=PortfolioFitReport(ticker="SBIN", fit="REJECT"),
    )

    assert decision.decision == "AVOID_NO_TRADE"
    assert decision.entry_intent_status == "rejected"


@pytest.mark.asyncio
async def test_final_intent_judge_clamps_more_aggressive_model_output():
    context = _context(target=112.0)
    judge = FinalIntentJudge()
    baseline = await judge.decide(
        context=context,
        regime=context.regime,
        thesis=ThesisReport(ticker="SBIN", confidence_score=8),
        skeptic=SkepticReport(ticker="SBIN", verdict="PASS"),
        portfolio=PortfolioFitReport(ticker="SBIN", fit="ACCEPTABLE"),
    )
    proposed = baseline.model_copy(
        update={
            "decision": "BUY_NOW",
            "ticker": "WRONG",
            "run_id": "invented",
            "stop_price": 0.0,
            "target_price": 9999.0,
            "confidence_score": 10,
        }
    )

    bounded = judge._apply_deterministic_boundary(proposed=proposed, baseline=baseline)

    assert bounded.decision == "WAIT_FOR_PULLBACK"
    assert bounded.ticker == "SBIN"
    assert bounded.run_id == context.run_id
    assert bounded.stop_price == 95.0
    assert bounded.target_price == 112.0
    assert bounded.confidence_score <= baseline.confidence_score
