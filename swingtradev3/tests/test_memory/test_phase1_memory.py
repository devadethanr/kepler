from __future__ import annotations

from copy import deepcopy

from memory.db import session_scope
from memory.models import (
    AccountStateRow,
    ApprovalRow,
    AuthSessionRow,
    EntryIntentRow,
    ExecutionEventRow,
    OrderIntentRow,
    TradeRow,
)
from models import PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"
TRADES_PATH = CONTEXT_DIR / "trades.json"
APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"
KITE_SESSION_PATH = CONTEXT_DIR / "auth" / "kite_session.json"


def test_managed_state_round_trips_through_postgres():
    original_state = deepcopy(read_json(STATE_PATH, {}))
    updated_state = {
        **original_state,
        "cash_inr": 81234.5,
        "realized_pnl": 3210.0,
        "positions": [
            {
                "ticker": "INFY",
                "quantity": 3,
                "entry_price": 1500.0,
                "current_price": 1522.0,
                "stop_price": 1450.0,
                "target_price": 1600.0,
                "opened_at": "2026-04-17T09:20:00",
                "entry_order_id": "order-infy-1",
                "oco_gtt_id": None,
                "thesis_score": 7.9,
                "research_date": "2026-04-16",
                "skill_version": "phase1-test",
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    }

    try:
        write_json(STATE_PATH, updated_state)

        round_trip = read_json(STATE_PATH, {})
        assert round_trip["cash_inr"] == 81234.5
        assert round_trip["positions"][0]["ticker"] == "INFY"

        with session_scope() as session:
            row = session.get(AccountStateRow, "primary")
            assert row is not None
            assert row.cash_inr == 81234.5
            assert row.payload["positions"][0]["ticker"] == "INFY"
    finally:
        write_json(STATE_PATH, original_state)


def test_managed_approvals_and_auth_session_project_from_postgres():
    original_approvals = deepcopy(read_json(APPROVALS_PATH, []))
    original_session = deepcopy(read_json(KITE_SESSION_PATH, {}))

    approval_payload = [
        {
            "ticker": "TCS",
            "score": 8.4,
            "setup_type": "breakout",
            "entry_zone": {"low": 4000.0, "high": 4010.0},
            "stop_price": 3920.0,
            "target_price": 4200.0,
            "holding_days_expected": 8,
            "confidence_reasoning": "Phase 1 bridge test",
            "risk_flags": [],
            "sector": "IT",
            "approved": True,
            "execution_requested": True,
            "execution_request_id": "req-phase1",
            "created_at": "2026-04-17T08:55:00",
            "expires_at": "2026-04-17T12:55:00",
            "research_date": "2026-04-16",
            "skill_version": "phase1-test",
        }
    ]
    session_payload = {
        "api_key": "phase1-api-key",
        "access_token": "phase1-access-token",
        "public_token": "phase1-public-token",
        "user_id": "AB1234",
        "created_at": "2026-04-17T08:00:00",
        "raw_session": {},
    }

    try:
        write_json(APPROVALS_PATH, approval_payload)
        write_json(KITE_SESSION_PATH, session_payload)

        approvals = read_json(APPROVALS_PATH, [])
        auth_session = read_json(KITE_SESSION_PATH, {})
        assert approvals[0]["ticker"] == "TCS"
        assert approvals[0]["execution_request_id"] == "req-phase1"
        assert auth_session["access_token"] == "phase1-access-token"

        with session_scope() as session:
            approval = PendingApproval.model_validate(approval_payload[0])
            approval_row = session.get(ApprovalRow, approval.approval_id)
            entry_intent_row = session.get(EntryIntentRow, approval.entry_intent_id)
            order_intent_row = session.get(OrderIntentRow, approval.order_intent_id)
            auth_row = session.get(AuthSessionRow, "kite")
            assert approval_row is not None
            assert approval_row.entry_intent_id == approval.entry_intent_id
            assert approval_row.order_intent_id == approval.order_intent_id
            assert approval_row.execution_requested is True
            assert entry_intent_row is not None
            assert order_intent_row is not None
            assert auth_row is not None
            assert auth_row.access_token == "phase1-access-token"
    finally:
        write_json(APPROVALS_PATH, original_approvals)
        if original_session:
            write_json(KITE_SESSION_PATH, original_session)


def test_trades_are_imported_and_execution_events_are_recorded():
    original_trades = deepcopy(read_json(TRADES_PATH, []))
    trade_payload = [
        {
            "trade_id": "trade-phase1-1",
            "ticker": "HDFCBANK",
            "quantity": 5,
            "entry_price": 1700.0,
            "exit_price": 1760.0,
            "opened_at": "2026-04-10T09:20:00",
            "closed_at": "2026-04-15T14:55:00",
            "exit_reason": "target_hit",
            "pnl_abs": 300.0,
            "pnl_pct": 3.53,
            "setup_type": "pullback",
            "thesis_reasoning": "Phase 1 migration test",
            "research_date": "2026-04-09",
            "skill_version": "phase1-test",
            "risk_flags": [],
        }
    ]

    try:
        write_json(TRADES_PATH, trade_payload)
        trades = read_json(TRADES_PATH, [])
        assert trades[0]["trade_id"] == "trade-phase1-1"

        with session_scope() as session:
            trade_row = session.get(TradeRow, "trade-phase1-1")
            event_count = session.query(ExecutionEventRow).count()
            assert trade_row is not None
            assert trade_row.ticker == "HDFCBANK"
            assert event_count > 0
    finally:
        write_json(TRADES_PATH, original_trades)
