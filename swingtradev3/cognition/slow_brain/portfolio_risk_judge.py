from __future__ import annotations

from config import cfg
from cognition.types import CandidateContextV1, PortfolioFitReport, SkepticReport, ThesisReport


class PortfolioRiskJudge:
    """Deterministic portfolio-aware gate before final intent creation."""

    agent_name = "portfolio_risk_judge"

    def judge(
        self,
        *,
        context: CandidateContextV1,
        thesis: ThesisReport,
        skeptic: SkepticReport,
    ) -> PortfolioFitReport:
        del thesis
        ticker = context.ticker
        reasons: list[str] = []
        risk_flags: list[str] = []
        open_positions = list(context.open_positions or [])

        if any(str(position.get("ticker") or "").upper() == ticker for position in open_positions):
            reasons.append("ticker_already_open")
            risk_flags.append("duplicate_position")

        max_positions = int(getattr(cfg.trading, "max_positions", 0) or 0)
        if max_positions > 0 and len(open_positions) >= max_positions:
            reasons.append("max_positions_reached")
            risk_flags.append("portfolio_full")

        sector = context.candidate.sector or "Unknown"
        sector_count = sum(
            1 for position in open_positions if str(position.get("sector") or "Unknown") == sector
        )
        if sector_count >= int(cfg.research.max_same_sector_positions):
            reasons.append(f"sector_exposure_cap:{sector}")
            risk_flags.append("sector_concentration")

        snapshot = dict(context.portfolio_snapshot or {})
        drawdown = _to_float(snapshot.get("drawdown_pct")) or 0.0
        weekly_loss = _to_float(snapshot.get("weekly_loss_pct")) or 0.0
        if drawdown >= float(cfg.risk.max_drawdown_pct):
            reasons.append("max_drawdown_reached")
            risk_flags.append("drawdown_block")
        if weekly_loss >= float(cfg.risk.max_weekly_loss_pct):
            reasons.append("max_weekly_loss_reached")
            risk_flags.append("weekly_loss_block")

        policy = dict(context.effective_policy or {})
        if policy and not bool(policy.get("new_entries_enabled", True)):
            reasons.append("effective_policy_blocks_new_entries")
            risk_flags.append("policy_block_new_entries")

        if skeptic.verdict == "VETO":
            reasons.append("skeptic_veto")
            risk_flags.extend(skeptic.risks)

        if any(flag in risk_flags for flag in {"duplicate_position", "portfolio_full"}):
            fit = "REJECT"
        elif any(flag.endswith("_block") for flag in risk_flags) or skeptic.verdict == "VETO":
            fit = "REJECT"
        elif risk_flags:
            fit = "DOWNGRADE"
        else:
            fit = "ACCEPTABLE"

        return PortfolioFitReport(
            ticker=ticker,
            fit=fit,
            reasons=reasons or ["portfolio_fit_ok"],
            risk_flags=sorted(set(risk_flags)),
            sector_exposure_count=sector_count,
            recommended_risk_pct=float(cfg.risk.max_risk_pct_per_trade),
            source="deterministic",
        )


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

