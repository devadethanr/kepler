from __future__ import annotations

from typing import Any

from cognition.types import (
    CandidateContextV1,
    EvidenceTraceItem,
    RegimeSynthesis,
    UniverseFunnelCandidate,
)
from memory_views import MemoryViewClient


class EvidenceAssembler:
    """Build compact per-candidate evidence packets from approved read paths."""

    def __init__(self, memory_views: MemoryViewClient | None = None) -> None:
        self._memory_views = memory_views or MemoryViewClient()

    def assemble(
        self,
        *,
        run_id: str,
        scan_date: str,
        candidate: UniverseFunnelCandidate,
        stock_data: dict[str, Any],
        regime: RegimeSynthesis,
    ) -> CandidateContextV1:
        degraded: list[str] = []
        memory_packet: dict[str, Any] = {}
        try:
            memory_packet = self._memory_views.research_context_packet(
                candidate.ticker,
                setup_type=candidate.setup_type,
            )
        except Exception as exc:
            degraded.append(f"memory_packet_unavailable:{exc.__class__.__name__}")

        evidence_trace = self._build_evidence_trace(candidate, stock_data, memory_packet)
        portfolio_snapshot = dict(memory_packet.get("portfolio_risk") or {})
        open_positions = list(memory_packet.get("open_positions") or [])
        effective_policy = dict(memory_packet.get("effective_policy") or {})
        if not memory_packet:
            degraded.append("phase12_memory_views_degraded")

        return CandidateContextV1(
            run_id=run_id,
            ticker=candidate.ticker,
            scan_date=scan_date,
            candidate=candidate,
            stock_data=dict(stock_data),
            memory_packet=memory_packet,
            evidence_trace=evidence_trace,
            portfolio_snapshot=portfolio_snapshot,
            open_positions=open_positions,
            effective_policy=effective_policy,
            regime=regime,
            degraded_reasons=degraded,
        )

    def _build_evidence_trace(
        self,
        candidate: UniverseFunnelCandidate,
        stock_data: dict[str, Any],
        memory_packet: dict[str, Any],
    ) -> list[EvidenceTraceItem]:
        ticker = candidate.ticker
        items: list[EvidenceTraceItem] = [
            EvidenceTraceItem(
                evidence_id=f"{ticker}:scan_candidate",
                source_type="scanner",
                summary=f"{candidate.setup_type} score {candidate.score}",
                payload=candidate.candidate_payload,
            )
        ]

        for index, article in enumerate(list(stock_data.get("news") or [])[:5], start=1):
            if not isinstance(article, dict):
                continue
            title = str(article.get("title") or article.get("headline") or "news")
            items.append(
                EvidenceTraceItem(
                    evidence_id=f"{ticker}:news:{index}",
                    source_type="news",
                    summary=title[:240],
                    url=article.get("url") or article.get("canonical_url"),
                    payload=dict(article),
                )
            )

        stock_graph = dict(memory_packet.get("stock") or {})
        for index, evidence in enumerate(list(stock_graph.get("evidence") or [])[:5], start=1):
            if not isinstance(evidence, dict):
                continue
            items.append(
                EvidenceTraceItem(
                    evidence_id=str(evidence.get("id") or f"{ticker}:graph:{index}"),
                    source_type=str(evidence.get("source_type") or "context_graph"),
                    summary=str(evidence.get("summary") or evidence.get("label") or "graph evidence"),
                    url=evidence.get("url"),
                    payload=dict(evidence),
                )
            )

        if memory_packet.get("similar_trades"):
            items.append(
                EvidenceTraceItem(
                    evidence_id=f"{ticker}:similar_trades",
                    source_type="memory_view",
                    summary=f"{len(memory_packet['similar_trades'])} similar trade(s) available",
                    payload={"similar_trades": memory_packet["similar_trades"][:5]},
                )
            )
        return items

