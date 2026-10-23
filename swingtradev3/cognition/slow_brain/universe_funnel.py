from __future__ import annotations

from typing import Any

from config import cfg
from cognition.types import RegimeSynthesis, UniverseFunnelCandidate, UniverseFunnelResult


def _score(item: dict[str, Any]) -> float:
    try:
        return float(item.get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


class UniverseFunnel:
    """Deterministic candidate reducer before expensive slow-brain debate."""

    def __init__(
        self,
        *,
        max_candidates: int | None = None,
        full_debate_candidates: int | None = None,
    ) -> None:
        self.max_candidates = max_candidates or int(cfg.research.slow_brain_max_candidates)
        self.full_debate_candidates = full_debate_candidates or int(
            cfg.research.slow_brain_full_debate_candidates
        )

    def select(
        self,
        *,
        run_id: str,
        scan_results: list[dict[str, Any]],
        regime: RegimeSynthesis,
    ) -> UniverseFunnelResult:
        min_score = float(cfg.research.slow_brain_min_score)
        sector_cap = max(1, int(cfg.research.max_same_sector_positions))
        unique: dict[str, dict[str, Any]] = {}
        skipped: list[UniverseFunnelCandidate] = []

        for item in scan_results:
            ticker = str(item.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            score = _score(item)
            if score < min_score:
                skipped.append(
                    UniverseFunnelCandidate(
                        ticker=ticker,
                        score=score,
                        setup_type=str(item.get("setup_type") or "unknown"),
                        sector=item.get("sector"),
                        route="skip",
                        reason=f"score_below_slow_brain_min:{min_score}",
                        candidate_payload=dict(item),
                    )
                )
                continue
            if ticker not in unique or score > _score(unique[ticker]):
                unique[ticker] = dict(item)

        ordered = sorted(
            unique.values(),
            key=lambda item: (
                -_score(item),
                str(item.get("sector") or "Unknown"),
                str(item.get("ticker") or ""),
            ),
        )

        selected: list[UniverseFunnelCandidate] = []
        sector_counts: dict[str, int] = {}
        for item in ordered:
            ticker = str(item.get("ticker") or "").strip().upper()
            sector = str(item.get("sector") or "Unknown")
            if sector_counts.get(sector, 0) >= sector_cap:
                skipped.append(
                    UniverseFunnelCandidate(
                        ticker=ticker,
                        score=_score(item),
                        setup_type=str(item.get("setup_type") or "unknown"),
                        sector=sector,
                        route="skip",
                        reason=f"sector_cap:{sector}",
                        candidate_payload=dict(item),
                    )
                )
                continue
            if len(selected) >= self.max_candidates:
                skipped.append(
                    UniverseFunnelCandidate(
                        ticker=ticker,
                        score=_score(item),
                        setup_type=str(item.get("setup_type") or "unknown"),
                        sector=sector,
                        route="skip",
                        reason="slow_brain_candidate_limit",
                        candidate_payload=dict(item),
                    )
                )
                continue
            route = "full_debate" if len(selected) < self.full_debate_candidates else "lightweight"
            selected.append(
                UniverseFunnelCandidate(
                    ticker=ticker,
                    score=_score(item),
                    setup_type=str(item.get("setup_type") or "unknown"),
                    sector=sector,
                    route=route,
                    reason=f"{regime.regime}_regime_score_rank",
                    candidate_payload=dict(item),
                )
            )
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        return UniverseFunnelResult(
            run_id=run_id,
            candidates=selected,
            skipped=skipped,
            full_debate_count=sum(1 for item in selected if item.route == "full_debate"),
        )

