from __future__ import annotations

from typing import Any

from cognition.types import RegimeSynthesis
from memory_views import MemoryViewClient


class RegimeSynthesizer:
    """Condense scanner and memory-view regime context into one bounded summary."""

    def __init__(self, memory_views: MemoryViewClient | None = None) -> None:
        self._memory_views = memory_views or MemoryViewClient()

    def synthesize(self, session_state: dict[str, Any]) -> RegimeSynthesis:
        raw_regime = dict(session_state.get("regime") or {})
        regime = str(raw_regime.get("regime") or raw_regime.get("market_regime") or "neutral")
        risk_flags = list(raw_regime.get("risk_flags") or [])
        context = []
        try:
            context = self._memory_views.regime_snapshot_context(limit=3)
        except Exception:
            risk_flags.append("regime_context_degraded")

        if context:
            latest = context[0]
            context_summary = str(latest.get("summary") or latest.get("regime") or "")
        else:
            context_summary = ""

        summary = str(raw_regime.get("summary") or context_summary or f"Regime is {regime}.")
        confidence = float(raw_regime.get("confidence") or raw_regime.get("score") or 0.0)
        if confidence > 1:
            confidence = min(confidence / 10.0, 1.0)
        return RegimeSynthesis(
            regime=regime,
            confidence=round(max(confidence, 0.0), 2),
            summary=summary,
            risk_flags=sorted(set(str(flag) for flag in risk_flags if flag)),
            source="deterministic",
        )

