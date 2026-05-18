from __future__ import annotations

from cognition.slow_brain.evidence_assembler import EvidenceAssembler
from cognition.types import RegimeSynthesis, UniverseFunnelCandidate


class BrokenMemoryViews:
    def research_context_packet(self, *_args, **_kwargs):
        raise RuntimeError("down")


def test_evidence_assembler_degrades_when_memory_views_fail():
    context = EvidenceAssembler(memory_views=BrokenMemoryViews()).assemble(
        run_id="phase13-evidence",
        scan_date="2026-05-17",
        candidate=UniverseFunnelCandidate(
            ticker="SBIN",
            score=8,
            setup_type="breakout",
            candidate_payload={"ticker": "SBIN", "score": 8},
        ),
        stock_data={"news": [{"title": "SBIN breaks resistance", "url": "https://example.test"}]},
        regime=RegimeSynthesis(regime="bull"),
    )

    assert context.degraded_reasons
    assert context.evidence_trace[0].evidence_id == "SBIN:scan_candidate"
    assert any(item.source_type == "news" for item in context.evidence_trace)

