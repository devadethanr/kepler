from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from api.tasks.event_bus import BusEvent, EventType
from cognition.intraday.types import ExceptionAdvice, ExceptionCase, ExceptionKind
from cognition.llm_client import CognitionLLMClient
from config import cfg
from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory.repository import MemoryRepository

IST = ZoneInfo("Asia/Kolkata")
PHASE = "phase_14_intraday_exception"
AGENT_NAME = "exception_analyst"


class ExceptionAnalyst:
    """Advisory-only reasoning for a small allow-list of abnormal events."""

    def __init__(self, llm_client: CognitionLLMClient | None = None) -> None:
        self._llm = llm_client or CognitionLLMClient(role="learning")
        self._settings = cfg.learning.exception_reasoning

    def classify_event(self, event: BusEvent) -> ExceptionCase | None:
        payload = dict(event.payload or {})
        kind: ExceptionKind | None = None
        if event.type == EventType.VIX_SPIKE:
            kind = "major_gap_or_shock"
        elif event.type == EventType.REGIME_CHANGE and bool(
            payload.get("unexpected") and payload.get("affects_positions")
        ):
            kind = "unexpected_regime_break"
        elif event.type == EventType.NEWS_BREAK and self._is_corporate_action_surprise(payload):
            kind = "corporate_action_surprise"
        elif event.type == EventType.ERROR and str(payload.get("anomaly_kind") or "") == (
            "broker_inconsistency"
        ):
            kind = "broker_inconsistency"
        if kind is None or kind not in set(self._settings.allowed_kinds):
            return None
        return ExceptionCase(
            case_id=f"event:{event.id}",
            kind=kind,
            severity=self._severity(payload),
            source=event.source,
            ticker=self._ticker(payload),
            detected_at=self._as_ist(event.timestamp),
            summary=str(payload.get("summary") or payload.get("reason") or event.type.value),
            evidence=[payload],
        )

    async def analyze(self, case: ExceptionCase) -> ExceptionAdvice:
        run_id = f"exception:{case.case_id}"
        with session_scope() as session:
            repo = MemoryRepository(session)
            existing = repo.get_cognition_run(run_id)
            if existing and existing.get("status") == "completed":
                reports = repo.list_cognition_reports(run_id=run_id, limit=1)
                if reports:
                    return ExceptionAdvice.model_validate(reports[0]["payload"])
            repo.upsert_cognition_run(
                run_id=run_id,
                phase=PHASE,
                status="started",
                started_at=datetime.now(IST),
                payload={"case": case.model_dump(mode="json")},
                source=AGENT_NAME,
            )

        advice = await self._llm.generate_structured(
            prompt=self._prompt(case),
            system_instruction=(
                "You are a cautious NSE intraday exception analyst. Analyze only the supplied "
                "abnormal event. Your output is advisory and must not claim that any order, "
                "position, kill switch, or policy was changed. Prefer operator review when facts "
                "are incomplete. Return only the ExceptionAdvice JSON schema."
            ),
            response_model=ExceptionAdvice,
            fallback_factory=lambda: self._fallback(case),
        )
        advice = advice.model_copy(
            update={
                "case_id": case.case_id,
                "kind": case.kind,
                "risk_level": case.severity,
                "advisory_only": True,
                "generated_at": datetime.now(IST),
            }
        )
        self._persist(case, advice, run_id)
        return advice

    async def scan_open_incidents(self) -> list[ExceptionAdvice]:
        if not self._settings.enabled:
            return []
        with session_scope() as session:
            incidents = MemoryRepository(session).list_failure_incidents(status="open")
        results: list[ExceptionAdvice] = []
        for incident in incidents:
            case = self._case_from_incident(incident)
            if case is None:
                continue
            with session_scope() as session:
                existing = MemoryRepository(session).get_cognition_run(
                    f"exception:{case.case_id}"
                )
            if existing and existing.get("status") == "completed":
                continue
            results.append(await self.analyze(case))
            if len(results) >= int(self._settings.max_cases_per_cycle):
                break
        return results

    def _case_from_incident(self, incident: dict[str, Any]) -> ExceptionCase | None:
        incident_id = str(incident.get("incident_id") or "unknown")
        payload = dict(incident.get("payload") or {})
        haystack = json.dumps({"incident_id": incident_id, **payload}, default=str).lower()
        kind: ExceptionKind | None = None
        if any(token in haystack for token in ("reconcile", "broker", "position_mismatch")):
            kind = "broker_inconsistency"
        elif any(token in haystack for token in ("corporate_action", "split", "bonus")):
            kind = "corporate_action_surprise"
        elif any(token in haystack for token in ("vix", "gap", "shock")):
            kind = "major_gap_or_shock"
        elif "regime_break" in haystack:
            kind = "unexpected_regime_break"
        if kind is None or kind not in set(self._settings.allowed_kinds):
            return None
        return ExceptionCase(
            case_id=f"incident:{incident_id}",
            kind=kind,
            severity=self._severity({**payload, "severity": incident.get("severity")}),
            source="failure_incident_scan",
            ticker=self._ticker(payload),
            summary=str(payload.get("reason") or payload.get("detail") or incident_id),
            evidence=[{"incident_id": incident_id, **payload}],
        )

    def _prompt(self, case: ExceptionCase) -> str:
        bounded = case.model_copy(
            update={"evidence": case.evidence[: int(self._settings.max_evidence_items)]}
        )
        return json.dumps(bounded.model_dump(mode="json"), default=str)[: int(
            self._settings.max_prompt_chars
        )]

    def _persist(self, case: ExceptionCase, advice: ExceptionAdvice, run_id: str) -> None:
        report_id = f"{run_id}:{AGENT_NAME}"
        now = datetime.now(IST)
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_cognition_report(
                report_id=report_id,
                run_id=run_id,
                ticker=case.ticker,
                agent_name=AGENT_NAME,
                schema_version="phase14.v1",
                status="completed",
                payload=advice.model_dump(mode="json"),
                source=AGENT_NAME,
            )
            repo.upsert_cognition_run(
                run_id=run_id,
                phase=PHASE,
                status="completed",
                completed_at=now,
                payload={
                    "case": case.model_dump(mode="json"),
                    "advice": advice.model_dump(mode="json"),
                },
                source=AGENT_NAME,
            )
            repo.append_execution_event(
                event_type="intraday_exception_advice_created",
                entity_type="cognition_run",
                entity_id=run_id,
                source=AGENT_NAME,
                payload={
                    "ticker": case.ticker,
                    "kind": case.kind,
                    "risk_level": advice.risk_level,
                    "advisory_action": advice.advisory_action,
                    "advisory_only": True,
                },
            )
        try:
            graph = ContextGraphRepository()
            graph.record_observation(
                observation_type="intraday_exception_advice",
                ticker=case.ticker,
                payload={
                    "observation_id": report_id,
                    "timestamp": now.isoformat(),
                    "case": case.model_dump(mode="json"),
                    "advice": advice.model_dump(mode="json"),
                },
                source=AGENT_NAME,
            )
            graph.close()
        except Exception:
            pass

    @staticmethod
    def _fallback(case: ExceptionCase) -> ExceptionAdvice:
        action = "alert_operator" if case.severity == "critical" else "review_position"
        return ExceptionAdvice(
            case_id=case.case_id,
            kind=case.kind,
            risk_level=case.severity,
            advisory_action=action,
            summary=case.summary,
            rationale="Abnormal event requires deterministic checks and operator review.",
            immediate_checks=[
                "Verify broker and Postgres state agree.",
                "Review affected positions and protective orders.",
                "Do not route a new order from this advisory.",
            ],
            confidence_score=5,
        )

    @staticmethod
    def _is_corporate_action_surprise(payload: dict[str, Any]) -> bool:
        if not payload.get("surprise"):
            return False
        if str(payload.get("category") or "").lower() == "corporate_action":
            return True
        return any(
            str(item.get("category") or "").lower() == "corporate_action"
            for item in payload.get("headlines", [])
            if isinstance(item, dict)
        )

    @staticmethod
    def _severity(payload: dict[str, Any]) -> str:
        return "critical" if str(payload.get("severity") or "").lower() == "critical" else "warning"

    @staticmethod
    def _ticker(payload: dict[str, Any]) -> str | None:
        ticker = str(payload.get("ticker") or "").strip().upper()
        return ticker or None

    @staticmethod
    def _as_ist(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=IST)
        return value.astimezone(IST)
