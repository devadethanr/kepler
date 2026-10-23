from __future__ import annotations

import json

from cognition.llm_client import CognitionLLMClient
from cognition.types import CandidateContextV1, RegimeSynthesis, ThesisReport


class ThesisAgent:
    """Construct the strongest structured long thesis for a candidate."""

    agent_name = "thesis_agent"

    def __init__(self, llm_client: CognitionLLMClient | None = None) -> None:
        self._llm = llm_client or CognitionLLMClient()

    async def analyze(
        self,
        *,
        context: CandidateContextV1,
        regime: RegimeSynthesis,
    ) -> ThesisReport:
        def fallback() -> ThesisReport:
            return self._fallback(context=context, regime=regime)

        return await self._llm.generate_structured(
            prompt=json.dumps(
                {
                    "candidate": context.candidate.model_dump(mode="json"),
                    "evidence": [item.model_dump(mode="json") for item in context.evidence_trace],
                    "regime": regime.model_dump(mode="json"),
                },
                default=str,
            ),
            system_instruction=(
                "You are a cautious NSE cash-equity swing-trading thesis analyst. "
                "Use only the provided packet and return a ThesisReport JSON object. "
                "Do not calculate position size."
            ),
            response_model=ThesisReport,
            fallback_factory=fallback,
        )

    def _fallback(self, *, context: CandidateContextV1, regime: RegimeSynthesis) -> ThesisReport:
        candidate = context.candidate
        payload = candidate.candidate_payload
        catalysts = [
            str(key)
            for key, enabled in dict(payload.get("signals") or {}).items()
            if bool(enabled)
        ]
        for evidence in context.evidence_trace:
            if evidence.source_type in {"news", "context_graph"} and len(catalysts) < 5:
                catalysts.append(evidence.summary)

        score = int(round(max(0.0, min(float(candidate.score), 10.0))))
        quality = "high" if score >= 8 else "medium" if score >= 7 else "low"
        stop = payload.get("stop_price")
        invalidation = [f"Daily close below stop {stop}"] if stop else ["Setup loses structure"]
        return ThesisReport(
            ticker=candidate.ticker,
            setup_quality=quality,
            thesis=(
                f"{candidate.ticker} has a {candidate.setup_type} setup with score "
                f"{candidate.score:.1f} in {regime.regime} regime."
            ),
            catalysts=catalysts[:5],
            invalidation=invalidation,
            confidence_score=score,
            source="deterministic",
        )
