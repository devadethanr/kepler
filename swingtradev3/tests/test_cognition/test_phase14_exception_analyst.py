from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from api.tasks.event_bus import BusEvent, EventType
from cognition.intraday.exception_analyst import ExceptionAnalyst, PHASE
from cognition.intraday.types import ExceptionCase
from cognition.llm_client import CognitionLLMClient
from memory.db import session_scope
from memory.repository import MemoryRepository

IST = ZoneInfo("Asia/Kolkata")


def test_exception_classifier_ignores_routine_position_news() -> None:
    event = BusEvent(
        type=EventType.NEWS_BREAK,
        source="intraday_news",
        payload={"ticker": "SBIN", "headlines": [{"category": "earnings"}]},
    )

    assert ExceptionAnalyst(llm_client=CognitionLLMClient(enabled=False)).classify_event(event) is None


def test_exception_classifier_accepts_explicit_corporate_action_surprise() -> None:
    event = BusEvent(
        type=EventType.NEWS_BREAK,
        source="intraday_news",
        payload={
            "ticker": "SBIN",
            "surprise": True,
            "headlines": [{"category": "corporate_action"}],
        },
    )

    case = ExceptionAnalyst(llm_client=CognitionLLMClient(enabled=False)).classify_event(event)

    assert case is not None
    assert case.kind == "corporate_action_surprise"
    assert case.ticker == "SBIN"


@pytest.mark.asyncio
async def test_exception_fallback_is_advisory_and_persisted(monkeypatch) -> None:
    case = ExceptionCase(
        case_id=f"unit:{datetime.now(IST).strftime('%H%M%S%f')}",
        kind="broker_inconsistency",
        severity="critical",
        source="unit_test",
        ticker="SBIN",
        summary="Broker position differs from Postgres position.",
        evidence=[{"broker_quantity": 0, "postgres_quantity": 10}],
    )

    class FakeGraph:
        def record_observation(self, **kwargs):
            return "observation:test"

        def close(self):
            return None

    monkeypatch.setattr(
        "cognition.intraday.exception_analyst.ContextGraphRepository",
        FakeGraph,
    )
    analyst = ExceptionAnalyst(llm_client=CognitionLLMClient(enabled=False))

    advice = await analyst.analyze(case)

    assert advice.advisory_only is True
    assert advice.advisory_action == "alert_operator"
    assert advice.deterministic_policy_hook is None
    with session_scope() as session:
        repo = MemoryRepository(session)
        run = repo.get_cognition_run(f"exception:{case.case_id}")
        reports = repo.list_cognition_reports(run_id=f"exception:{case.case_id}")
    assert run is not None
    assert run["phase"] == PHASE
    assert run["status"] == "completed"
    assert reports[0]["payload"]["advisory_only"] is True


def test_phase14_run_filter_does_not_mix_slow_brain_runs() -> None:
    with session_scope() as session:
        runs = MemoryRepository(session).list_cognition_runs(limit=50, phase=PHASE)

    assert all(run["phase"] == PHASE for run in runs)
