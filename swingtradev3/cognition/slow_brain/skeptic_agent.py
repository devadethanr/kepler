from __future__ import annotations

import json

from config import cfg
from cognition.llm_client import CognitionLLMClient
from cognition.types import CandidateContextV1, SkepticReport, ThesisReport


class SkepticAgent:
    """Attack the candidate thesis with structured veto or caution flags."""

    agent_name = "skeptic_agent"

    def __init__(self, llm_client: CognitionLLMClient | None = None) -> None:
        self._llm = llm_client or CognitionLLMClient()

    async def analyze(
        self,
        *,
        context: CandidateContextV1,
        thesis: ThesisReport,
    ) -> SkepticReport:
        def fallback() -> SkepticReport:
            return self._fallback(context=context, thesis=thesis)

        return await self._llm.generate_structured(
            prompt=json.dumps(
                {
                    "candidate": context.candidate.model_dump(mode="json"),
                    "thesis": thesis.model_dump(mode="json"),
                    "degraded_reasons": context.degraded_reasons,
                },
                default=str,
            ),
            system_instruction=(
                "You are a skeptical NSE swing-trading risk reviewer. "
                "Return a SkepticReport JSON object with only provided evidence."
            ),
            response_model=SkepticReport,
            fallback_factory=fallback,
        )

    def _fallback(self, *, context: CandidateContextV1, thesis: ThesisReport) -> SkepticReport:
        payload = context.candidate.candidate_payload
        risks = [str(flag) for flag in payload.get("risk_flags") or []]
        entry_zone = dict(payload.get("entry_zone") or {})
        entry_high = _to_float(entry_zone.get("high") or entry_zone.get("low"))
        stop = _to_float(payload.get("stop_price"))
        target = _to_float(payload.get("target_price"))

        rr = None
        if entry_high is not None and stop is not None and target is not None:
            risk = entry_high - stop
            reward = target - entry_high
            if risk > 0:
                rr = reward / risk
            else:
                risks.append("invalid_stop_above_entry")

        if rr is not None and rr < float(cfg.risk.min_rr_ratio):
            risks.append(f"rr_below_min:{rr:.2f}")

        if context.degraded_reasons:
            risks.extend(context.degraded_reasons)

        severe = {"invalid_stop_above_entry", "position_size_zero", "suspended", "illiquid"}
        verdict = "VETO" if any(str(risk) in severe for risk in risks) else "PASS"
        if verdict != "VETO" and risks:
            verdict = "CAUTION"
        penalty = min(len(risks) * 2, 8)
        return SkepticReport(
            ticker=context.ticker,
            verdict=verdict,
            critique=(
                "No material objection found."
                if not risks
                else "Risks need operator review: " + ", ".join(risks[:5])
            ),
            risks=risks,
            confidence_penalty=penalty,
            source="deterministic",
        )


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
