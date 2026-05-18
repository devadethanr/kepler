from __future__ import annotations

from cognition.slow_brain.portfolio_risk_judge import PortfolioRiskJudge
from cognition.types import CandidateContextV1, ThesisReport, SkepticReport, UniverseFunnelCandidate


def test_portfolio_risk_judge_rejects_duplicate_open_position():
    context = CandidateContextV1(
        run_id="phase13-risk",
        ticker="SBIN",
        scan_date="2026-05-17",
        candidate=UniverseFunnelCandidate(ticker="SBIN", sector="Bank"),
        open_positions=[{"ticker": "SBIN", "sector": "Bank"}],
        portfolio_snapshot={"drawdown_pct": 0.0, "weekly_loss_pct": 0.0},
        effective_policy={"new_entries_enabled": True},
    )

    report = PortfolioRiskJudge().judge(
        context=context,
        thesis=ThesisReport(ticker="SBIN", confidence_score=8),
        skeptic=SkepticReport(ticker="SBIN", verdict="PASS"),
    )

    assert report.fit == "REJECT"
    assert "duplicate_position" in report.risk_flags

