from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from config import cfg
from cognition.slow_brain.evidence_assembler import EvidenceAssembler
from cognition.slow_brain.final_intent_judge import FinalIntentJudge
from cognition.slow_brain.portfolio_risk_judge import PortfolioRiskJudge
from cognition.slow_brain.regime_synthesizer import RegimeSynthesizer
from cognition.slow_brain.skeptic_agent import SkepticAgent
from cognition.slow_brain.thesis_agent import ThesisAgent
from cognition.slow_brain.universe_funnel import UniverseFunnel
from cognition.types import (
    CandidateContextV1,
    FinalIntentDecision,
    PortfolioFitReport,
    SkepticReport,
    SlowBrainRunResult,
    ThesisReport,
)
from intent_ids import approval_id as build_approval_id
from intent_ids import entry_intent_id as build_entry_intent_id
from intent_ids import order_intent_id as build_order_intent_id
from memory.db import session_scope
from memory.repository import MemoryRepository
from models import PendingApproval


IST = ZoneInfo("Asia/Kolkata")
SOURCE = "phase13_slow_brain"


class SlowBrainOrchestrator:
    """Run the bounded Phase 13 slow-brain desk over scanner candidates."""

    def __init__(
        self,
        *,
        regime_synthesizer: RegimeSynthesizer | None = None,
        universe_funnel: UniverseFunnel | None = None,
        evidence_assembler: EvidenceAssembler | None = None,
        thesis_agent: ThesisAgent | None = None,
        skeptic_agent: SkepticAgent | None = None,
        portfolio_judge: PortfolioRiskJudge | None = None,
        final_judge: FinalIntentJudge | None = None,
    ) -> None:
        self._regime_synthesizer = regime_synthesizer or RegimeSynthesizer()
        self._universe_funnel = universe_funnel or UniverseFunnel()
        self._evidence_assembler = evidence_assembler or EvidenceAssembler()
        self._thesis_agent = thesis_agent or ThesisAgent()
        self._skeptic_agent = skeptic_agent or SkepticAgent()
        self._portfolio_judge = portfolio_judge or PortfolioRiskJudge()
        self._final_judge = final_judge or FinalIntentJudge()

    async def run(
        self,
        session_state: dict[str, Any],
        *,
        run_id: str | None = None,
        analyzed_at: datetime | None = None,
        persist: bool = True,
    ) -> SlowBrainRunResult:
        started_at = analyzed_at.astimezone(IST) if analyzed_at else datetime.now(IST)
        scan_date = started_at.date().isoformat()
        run_id = run_id or f"slow-brain:{scan_date}:{started_at.strftime('%H%M%S')}"

        if persist:
            with session_scope() as session:
                MemoryRepository(session).upsert_cognition_run(
                    run_id=run_id,
                    phase="phase_13",
                    status="started",
                    started_at=started_at,
                    payload={"scan_date": scan_date},
                    source=SOURCE,
                )

        regime = self._regime_synthesizer.synthesize(session_state)
        scan_results = _source_scan_results(session_state)
        funnel = self._universe_funnel.select(
            run_id=run_id,
            scan_results=scan_results,
            regime=regime,
        )

        decisions: list[FinalIntentDecision] = []
        approval_candidates: list[dict[str, Any]] = []
        stock_data = dict(session_state.get("stock_data") or {})

        if persist:
            self._persist_run_report(
                run_id=run_id,
                agent_name="regime_synthesizer",
                ticker=None,
                payload=regime.model_dump(mode="json"),
                status="ok",
            )
            self._persist_run_report(
                run_id=run_id,
                agent_name="universe_funnel",
                ticker=None,
                payload=funnel.model_dump(mode="json"),
                status="ok",
            )

        for candidate in funnel.candidates:
            context = self._evidence_assembler.assemble(
                run_id=run_id,
                scan_date=scan_date,
                candidate=candidate,
                stock_data=dict(stock_data.get(candidate.ticker) or {}),
                regime=regime,
            )
            thesis = await self._thesis_agent.analyze(context=context, regime=regime)
            skeptic = await self._skeptic_agent.analyze(context=context, thesis=thesis)
            portfolio = self._portfolio_judge.judge(
                context=context,
                thesis=thesis,
                skeptic=skeptic,
            )
            self._attach_report_ids(run_id, context, thesis, skeptic, portfolio)
            decision = await self._final_judge.decide(
                context=context,
                regime=regime,
                thesis=thesis,
                skeptic=skeptic,
                portfolio=portfolio,
            )
            decision.report_id = _report_id(run_id, candidate.ticker, "final_intent_judge")
            # Ensure all source report IDs are populated (LLM may not return them)
            decision.source_reports["thesis"] = thesis.report_id
            decision.source_reports["skeptic"] = skeptic.report_id
            decision.source_reports["portfolio"] = portfolio.report_id
            decision.source_reports["final"] = decision.report_id
            decisions.append(decision)

            if persist:
                self._persist_candidate_reports(
                    run_id=run_id,
                    context=context,
                    thesis=thesis,
                    skeptic=skeptic,
                    portfolio=portfolio,
                    decision=decision,
                )
                self._persist_entry_intent(decision=decision, context=context)

            if decision.actionable_for_approval:
                approval_candidates.append(
                    self._approval_payload_from_decision(
                        decision=decision,
                        context=context,
                        analyzed_at=started_at,
                    )
                )

        status = "completed"
        result = SlowBrainRunResult(
            run_id=run_id,
            status=status,
            regime=regime,
            funnel=funnel,
            decisions=decisions,
            approval_candidates=approval_candidates,
            diagnostics={
                "scan_candidates": len(scan_results),
                "funnel_candidates": len(funnel.candidates),
                "approval_candidates": len(approval_candidates),
            },
        )

        if persist:
            with session_scope() as session:
                MemoryRepository(session).upsert_cognition_run(
                    run_id=run_id,
                    phase="phase_13",
                    status=status,
                    started_at=started_at,
                    completed_at=datetime.now(IST),
                    payload=result.model_dump(mode="json"),
                    source=SOURCE,
                )
        return result

    def _attach_report_ids(
        self,
        run_id: str,
        context: CandidateContextV1,
        thesis: ThesisReport,
        skeptic: SkepticReport,
        portfolio: PortfolioFitReport,
    ) -> None:
        thesis.report_id = _report_id(run_id, context.ticker, "thesis_agent")
        skeptic.report_id = _report_id(run_id, context.ticker, "skeptic_agent")
        portfolio.report_id = _report_id(run_id, context.ticker, "portfolio_risk_judge")

    def _persist_candidate_reports(
        self,
        *,
        run_id: str,
        context: CandidateContextV1,
        thesis: ThesisReport,
        skeptic: SkepticReport,
        portfolio: PortfolioFitReport,
        decision: FinalIntentDecision,
    ) -> None:
        self._persist_run_report(
            run_id=run_id,
            agent_name="evidence_assembler",
            ticker=context.ticker,
            payload=context.model_dump(mode="json"),
            status="degraded" if context.degraded_reasons else "ok",
        )
        self._persist_run_report(
            run_id=run_id,
            agent_name="thesis_agent",
            ticker=context.ticker,
            payload=thesis.model_dump(mode="json"),
            status="ok",
            report_id=thesis.report_id,
        )
        self._persist_run_report(
            run_id=run_id,
            agent_name="skeptic_agent",
            ticker=context.ticker,
            payload=skeptic.model_dump(mode="json"),
            status="ok" if skeptic.verdict != "VETO" else "veto",
            report_id=skeptic.report_id,
        )
        self._persist_run_report(
            run_id=run_id,
            agent_name="portfolio_risk_judge",
            ticker=context.ticker,
            payload=portfolio.model_dump(mode="json"),
            status=portfolio.fit.lower(),
            report_id=portfolio.report_id,
        )
        self._persist_run_report(
            run_id=run_id,
            agent_name="final_intent_judge",
            ticker=context.ticker,
            payload=decision.model_dump(mode="json"),
            status=decision.entry_intent_status,
            report_id=decision.report_id,
        )

    def _persist_run_report(
        self,
        *,
        run_id: str,
        agent_name: str,
        ticker: str | None,
        payload: dict[str, Any],
        status: str,
        report_id: str | None = None,
    ) -> None:
        report_id = report_id or _report_id(run_id, ticker or "market", agent_name)
        with session_scope() as session:
            MemoryRepository(session).upsert_cognition_report(
                report_id=report_id,
                run_id=run_id,
                ticker=ticker,
                agent_name=agent_name,
                schema_version=str(payload.get("schema_version") or "v1"),
                status=status,
                payload=payload,
                source=SOURCE,
            )

    def _persist_entry_intent(
        self,
        *,
        decision: FinalIntentDecision,
        context: CandidateContextV1,
    ) -> None:
        payload = self._entry_intent_payload(decision=decision, context=context)
        entry_intent_id = build_entry_intent_id(payload)
        approval_id = build_approval_id(payload) if decision.actionable_for_approval else None
        order_intent_id = build_order_intent_id(payload) if decision.actionable_for_approval else None
        with session_scope() as session:
            MemoryRepository(session).upsert_entry_intent(
                entry_intent_id=entry_intent_id,
                ticker=decision.ticker,
                status=decision.entry_intent_status,
                approval_id=approval_id,
                order_intent_id=order_intent_id,
                payload={**payload, "entry_intent_id": entry_intent_id},
                source=SOURCE,
            )

    def _approval_payload_from_decision(
        self,
        *,
        decision: FinalIntentDecision,
        context: CandidateContextV1,
        analyzed_at: datetime,
    ) -> dict[str, Any]:
        base = self._entry_intent_payload(decision=decision, context=context)
        expires_at = analyzed_at + timedelta(hours=cfg.execution.approval_timeout_hours)
        pending = PendingApproval.model_validate(
            {
                **base,
                "approved": None,
                "execution_requested": False,
                "execution_request_id": None,
                "status": "pending",
                "created_at": analyzed_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        ).model_dump(mode="json")
        return pending

    def _entry_intent_payload(
        self,
        *,
        decision: FinalIntentDecision,
        context: CandidateContextV1,
    ) -> dict[str, Any]:
        return {
            "ticker": decision.ticker,
            "score": float(context.candidate.score),
            "setup_type": decision.setup_type,
            "entry_zone": decision.entry_zone.model_dump(mode="json"),
            "stop_price": decision.stop_price,
            "target_price": decision.target_price,
            "holding_days_expected": decision.holding_days_expected,
            "confidence_reasoning": decision.confidence_reasoning,
            "risk_flags": decision.risk_flags,
            "sector": context.candidate.sector,
            "research_date": context.scan_date,
            "skill_version": context.candidate.candidate_payload.get("skill_version"),
            "slow_brain_run_id": decision.run_id,
            "slow_brain_decision": decision.decision,
            "portfolio_fit": decision.portfolio_fit,
            "source_reports": decision.source_reports,
            "evidence_trace_ids": decision.evidence_trace_ids,
            "funnel_route": context.candidate.route,
        }


def _source_scan_results(session_state: dict[str, Any]) -> list[dict[str, Any]]:
    scan_results = list(session_state.get("scan_results") or [])
    shortlist = list(session_state.get("shortlist") or [])
    if not scan_results:
        return [dict(item) for item in shortlist if isinstance(item, dict)]
    by_ticker: dict[str, dict[str, Any]] = {}
    for item in [*scan_results, *shortlist]:
        if not isinstance(item, dict):
            continue
        ticker = str(item.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        current = by_ticker.get(ticker)
        if current is None or float(item.get("score") or 0) > float(current.get("score") or 0):
            by_ticker[ticker] = dict(item)
    return list(by_ticker.values())


def _report_id(run_id: str, ticker: str, agent_name: str) -> str:
    return f"{run_id}:{ticker}:{agent_name}"[:160]
