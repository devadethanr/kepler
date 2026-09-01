from __future__ import annotations

import json

from config import cfg
from cognition.llm_client import CognitionLLMClient
from cognition.types import (
    CandidateContextV1,
    EntryZoneModel,
    FinalIntentDecision,
    PortfolioFitReport,
    RegimeSynthesis,
    SkepticReport,
    ThesisReport,
)


class FinalIntentJudge:
    """Create the final structured entry-intent decision."""

    agent_name = "final_intent_judge"

    def __init__(self, llm_client: CognitionLLMClient | None = None) -> None:
        self._llm = llm_client or CognitionLLMClient()

    async def decide(
        self,
        *,
        context: CandidateContextV1,
        regime: RegimeSynthesis,
        thesis: ThesisReport,
        skeptic: SkepticReport,
        portfolio: PortfolioFitReport,
    ) -> FinalIntentDecision:
        baseline = self._fallback(
            context=context,
            regime=regime,
            thesis=thesis,
            skeptic=skeptic,
            portfolio=portfolio,
        )

        proposed = await self._llm.generate_structured(
            prompt=json.dumps(
                {
                    "candidate": context.candidate.model_dump(mode="json"),
                    "regime": regime.model_dump(mode="json"),
                    "thesis": thesis.model_dump(mode="json"),
                    "skeptic": skeptic.model_dump(mode="json"),
                    "portfolio": portfolio.model_dump(mode="json"),
                    "risk_rules": {"min_rr_ratio": cfg.risk.min_rr_ratio},
                },
                default=str,
            ),
            system_instruction=(
                "You are the final cautious NSE swing-trading intent judge. "
                "Return a FinalIntentDecision JSON object. Do not size positions."
            ),
            response_model=FinalIntentDecision,
            fallback_factory=lambda: baseline,
        )
        return self._apply_deterministic_boundary(
            proposed=proposed,
            baseline=baseline,
        )

    @staticmethod
    def _apply_deterministic_boundary(
        *,
        proposed: FinalIntentDecision,
        baseline: FinalIntentDecision,
    ) -> FinalIntentDecision:
        """Allow a model to be more conservative, never more permissive than code."""
        rank = {
            "AVOID_NO_TRADE": 0,
            "WAIT_FOR_PULLBACK": 1,
            "BUY_ONLY_ABOVE_TRIGGER": 2,
            "BUY_NOW": 3,
        }
        model_is_no_more_aggressive = rank[proposed.decision] <= rank[baseline.decision]
        decision = proposed.decision if model_is_no_more_aggressive else baseline.decision
        bias = proposed.bias if model_is_no_more_aggressive else baseline.bias
        reason = proposed.confidence_reasoning.strip() or baseline.confidence_reasoning
        if not model_is_no_more_aggressive:
            reason = f"Deterministic gate: {baseline.confidence_reasoning}"

        return baseline.model_copy(
            update={
                "decision": decision,
                "bias": bias,
                "confidence_score": min(
                    proposed.confidence_score,
                    baseline.confidence_score,
                ),
                "confidence_reasoning": reason,
                "risk_flags": sorted(set([*baseline.risk_flags, *proposed.risk_flags])),
            }
        )

    def _fallback(
        self,
        *,
        context: CandidateContextV1,
        regime: RegimeSynthesis,
        thesis: ThesisReport,
        skeptic: SkepticReport,
        portfolio: PortfolioFitReport,
    ) -> FinalIntentDecision:
        payload = context.candidate.candidate_payload
        entry_zone_payload = dict(payload.get("entry_zone") or {})
        entry_zone = EntryZoneModel(
            low=_to_float(entry_zone_payload.get("low")) or 0.0,
            high=_to_float(entry_zone_payload.get("high")) or 0.0,
        )
        stop = _to_float(payload.get("stop_price")) or 0.0
        target = _to_float(payload.get("target_price")) or 0.0
        score = min(10, max(0, thesis.confidence_score - skeptic.confidence_penalty))
        risk_flags = sorted(
            set(
                [*context.candidate.candidate_payload.get("risk_flags", [])]
                + skeptic.risks
                + portfolio.risk_flags
                + regime.risk_flags
            )
        )
        rr = _risk_reward(entry_zone.high or entry_zone.low, stop, target)

        if skeptic.verdict == "VETO" or portfolio.fit == "REJECT":
            decision = "AVOID_NO_TRADE"
            reason = "Rejected by skeptic or portfolio risk gate."
            bias = "NEUTRAL"
        elif rr is None or rr < float(cfg.risk.min_rr_ratio):
            decision = "WAIT_FOR_PULLBACK"
            reason = "Valid idea, but current assumptions fail minimum risk-reward."
            bias = "BULLISH"
            risk_flags.append("poor_current_rr")
        elif score < int(cfg.research.slow_brain_min_confidence_score):
            decision = "WAIT_FOR_PULLBACK"
            reason = "Setup needs stronger confirmation before approval."
            bias = "MIXED"
        elif portfolio.fit == "DOWNGRADE":
            decision = "WAIT_FOR_PULLBACK"
            reason = "Portfolio fit is downgraded; keep intent in watching state."
            bias = "BULLISH"
        elif "breakout" in context.candidate.setup_type.lower():
            decision = "BUY_ONLY_ABOVE_TRIGGER"
            reason = "Breakout setup requires trigger confirmation."
            bias = "BULLISH"
        else:
            decision = "BUY_NOW"
            reason = "Setup passes thesis, skeptic, portfolio, and RR checks."
            bias = "BULLISH"

        evidence_ids = [item.evidence_id for item in context.evidence_trace]
        return FinalIntentDecision(
            ticker=context.ticker,
            decision=decision,
            confidence_score=score,
            setup_type=context.candidate.setup_type,
            bias=bias,
            entry_zone=entry_zone,
            stop_price=stop,
            target_price=target,
            holding_days_expected=int(payload.get("holding_days_expected") or 0),
            confidence_reasoning=reason,
            risk_flags=sorted(set(risk_flags)),
            source_reports={
                "thesis": thesis.report_id,
                "skeptic": skeptic.report_id,
                "portfolio": portfolio.report_id,
            },
            evidence_trace_ids=evidence_ids,
            portfolio_fit=portfolio.fit,
            run_id=context.run_id,
        )


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _risk_reward(entry: float, stop: float, target: float) -> float | None:
    risk = entry - stop
    reward = target - entry
    if risk <= 0:
        return None
    return reward / risk
