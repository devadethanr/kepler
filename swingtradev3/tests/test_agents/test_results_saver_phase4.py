from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from agents.research.pipeline import ResultsSaverAgent
from memory.db import session_scope
from memory.repository import MemoryRepository
from paths import CONTEXT_DIR
from storage import read_json, write_json


APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"


def test_results_saver_drops_shortlist_tickers_outside_configured_universe():
    agent = ResultsSaverAgent()

    approvals = agent._build_pending_approvals(
        shortlist=[
            {"ticker": "RELIANCE", "score": 8.1},
            {"ticker": "SBI2C16E", "score": 8.6},
        ],
        scan_date="2026-05-14",
        analyzed_at=datetime(2026, 5, 14, 18, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )

    assert [item["ticker"] for item in approvals] == ["RELIANCE"]


def test_results_saver_preserves_slow_brain_identity_and_audit_fields():
    agent = ResultsSaverAgent()

    approvals = agent._build_pending_approvals(
        shortlist=[
            {
                "ticker": "RELIANCE",
                "score": 8.1,
                "setup_type": "breakout",
                "entry_zone": {"low": 1000.0, "high": 1010.0},
                "stop_price": 980.0,
                "target_price": 1100.0,
                "holding_days_expected": 7,
                "confidence_reasoning": "slow brain final",
                "approval_id": "approval:RELIANCE:slow",
                "entry_intent_id": "entry-intent:RELIANCE:slow",
                "order_intent_id": "order-intent:RELIANCE:slow",
                "slow_brain_run_id": "slow-brain:test",
                "slow_brain_decision": "BUY_ONLY_ABOVE_TRIGGER",
                "portfolio_fit": "ACCEPTABLE",
                "source_reports": {"final": "report-final"},
                "evidence_trace_ids": ["e1"],
                "funnel_route": "full_debate",
            }
        ],
        scan_date="2026-05-14",
        analyzed_at=datetime(2026, 5, 14, 18, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
    )

    assert approvals[0]["approval_id"] == "approval:RELIANCE:slow"
    assert approvals[0]["entry_intent_id"] == "entry-intent:RELIANCE:slow"
    assert approvals[0]["slow_brain_run_id"] == "slow-brain:test"
    assert approvals[0]["source_reports"] == {"final": "report-final"}


@pytest.mark.asyncio
async def test_results_saver_persists_candidate_identity_into_memory():
    original_approvals = deepcopy(read_json(APPROVALS_PATH, []))
    research_dir = CONTEXT_DIR / "research" / date.today().isoformat()
    scan_result_path = research_dir / "scan_result.json"
    original_scan_result = scan_result_path.read_text(encoding="utf-8") if scan_result_path.exists() else None

    ctx = SimpleNamespace(
        session=SimpleNamespace(
            state={
                "regime": {"regime": "bull"},
                "qualified_stocks": [{"ticker": "RELIANCE"}],
                "shortlist": [
                    {
                        "ticker": "RELIANCE",
                        "score": 8.9,
                        "setup_type": "breakout",
                        "entry_zone": {"low": 1000.0, "high": 1010.0},
                        "stop_price": 980.0,
                        "target_price": 1080.0,
                        "holding_days_expected": 7,
                        "confidence_reasoning": "Phase 4 proposal lineage",
                        "risk_flags": [],
                        "sector": "energy",
                        "research_date": "2026-04-18",
                        "skill_version": "phase4-test",
                    }
                ],
                "stock_data": {},
                "scan_results": [],
            }
        )
    )

    try:
        agent = ResultsSaverAgent()
        async for _ in agent._run_async_impl(ctx):
            pass

        approvals = read_json(APPROVALS_PATH, [])
        approval = next(
            item for item in approvals if item.get("ticker") == "RELIANCE" and item.get("skill_version") == "phase4-test"
        )
        assert approval["approval_id"]
        assert approval["entry_intent_id"]
        assert approval["order_intent_id"]

        with session_scope() as session:
            repo = MemoryRepository(session)
            entry_intent = repo.get_entry_intent(str(approval["entry_intent_id"]))
            order_intent = repo.get_order_intent(str(approval["order_intent_id"]))

        assert entry_intent is not None
        assert entry_intent["status"] == "awaiting_approval"
        assert order_intent is not None
        assert order_intent["status"] == "awaiting_approval"
        assert order_intent["approval_id"] == approval["approval_id"]
    finally:
        write_json(APPROVALS_PATH, original_approvals)
        with session_scope() as session:
            MemoryRepository(session).replace_pending_approvals(
                original_approvals,
                source="test_results_saver_restore",
            )
        if original_scan_result is None:
            if scan_result_path.exists():
                scan_result_path.unlink()
            if research_dir.exists():
                try:
                    research_dir.rmdir()
                except OSError:
                    pass
        else:
            scan_result_path.write_text(original_scan_result, encoding="utf-8")
