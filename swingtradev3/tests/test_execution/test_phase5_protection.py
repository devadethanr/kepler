from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from execution.protection_manager import ProtectionManager
from execution.trailing_engine import TrailingEngine
from memory.db import session_scope
from memory.models import ProtectiveTriggerRow, TradeRow
from memory.repositories import MemoryRepository
from models import AccountState, GTTOrder, PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"


def _state_with_position(ticker: str, *, oco_gtt_id: str | None = None) -> dict[str, object]:
    return AccountState(
        cash_inr=100000.0,
        positions=[
            {
                "ticker": ticker,
                "quantity": 5,
                "entry_price": 1000.0,
                "current_price": 1000.0,
                "stop_price": 980.0,
                "target_price": 1080.0,
                "opened_at": "2026-04-18T09:20:00",
                "entry_order_id": "entry-order-1",
                "oco_gtt_id": oco_gtt_id,
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    ).model_dump(mode="json")


def _store_protected_order_intent(ticker: str) -> PendingApproval:
    approval = PendingApproval.model_validate(
        {
            "ticker": ticker,
            "score": 8.8,
            "setup_type": "breakout",
            "entry_zone": {"low": 995.0, "high": 1000.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 8,
            "confidence_reasoning": "Phase 5 position",
            "risk_flags": [],
            "approved": True,
            "execution_requested": True,
            "created_at": "2026-04-18T08:50:00",
            "expires_at": "2026-04-18T12:50:00",
        }
    )
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=str(approval.order_intent_id),
            ticker=ticker,
            status="protected",
            approval_id=approval.approval_id,
            entry_intent_id=approval.entry_intent_id,
            broker_order_id="entry-order-1",
            broker_tag="STV3PHASE5TEST",
            payload={**approval.model_dump(mode="json"), "broker_order_id": "entry-order-1"},
            source="test_phase5",
        )
    return approval


@pytest.mark.asyncio
async def test_watchdog_recovers_cancelled_protection():
    ticker = f"INF{uuid4().hex[:5]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    _store_protected_order_intent(ticker)

    try:
        write_json(STATE_PATH, _state_with_position(ticker, oco_gtt_id="111"))
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id="111",
                position_id=ticker,
                ticker=ticker,
                status="cancelled",
                payload={"ticker": ticker, "recovery_attempts": 0},
                source="test_phase5",
            )

        manager = ProtectionManager(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        manager.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="111",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="cancelled",
            )
        )
        manager.gtt_manager.place_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="222",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="active",
            )
        )

        result = await manager.run_watchdog()

        assert result["recovered"] == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["oco_gtt_id"] == "222"
        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, "222")
        assert trigger_row is not None
        assert trigger_row.status == "active"
        assert trigger_row.payload["recovery_reason"] == "cancelled"
    finally:
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_watchdog_treats_trigger_as_advisory_until_exit_fill():
    ticker = f"REL{uuid4().hex[:5]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    _store_protected_order_intent(ticker)

    try:
        write_json(STATE_PATH, _state_with_position(ticker, oco_gtt_id="333"))
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id="exit-order-open",
                exchange_order_id="exchange-exit-open",
                ticker=ticker,
                order_intent_id=None,
                status="open",
                broker_tag=None,
                payload={"status": "OPEN", "filled_quantity": 0, "pending_quantity": 5},
                source="test_phase5",
            )

        manager = ProtectionManager(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        manager.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="333",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="triggered",
                triggered_leg="stop",
                exit_order_id="exit-order-open",
                exit_order_status="open",
            )
        )

        result = await manager.run_watchdog()

        assert result["triggered"] == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["ticker"] == ticker
        assert state["positions"][0]["lifecycle_state"] == "closing"
        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, "333")
        assert trigger_row is not None
        assert trigger_row.status == "exit_order_open"
        assert trigger_row.payload["exit_order_id"] == "exit-order-open"
    finally:
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_watchdog_marks_operator_intervention_after_repeated_recovery_failures():
    ticker = f"AXB{uuid4().hex[:5]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    _store_protected_order_intent(ticker)

    try:
        write_json(STATE_PATH, _state_with_position(ticker, oco_gtt_id="334"))
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id="334",
                position_id=ticker,
                ticker=ticker,
                status="cancelled",
                payload={"ticker": ticker, "recovery_attempts": 0},
                source="test_phase5",
            )

        manager = ProtectionManager(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        manager.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="334",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="cancelled",
            )
        )
        manager.gtt_manager.place_gtt_async = AsyncMock(side_effect=RuntimeError("broker unavailable"))

        for _ in range(4):
            await manager.run_watchdog()

        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["lifecycle_state"] == "operator_intervention"
        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, "334")
        assert trigger_row is not None
        assert trigger_row.status == "recreate_required"
        assert "exceeded threshold" in trigger_row.payload["operator_detail"]
        assert trigger_row.payload["last_recovery_error"] == "broker unavailable"
    finally:
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_watchdog_closes_position_after_confirmed_exit_fill():
    ticker = f"TCS{uuid4().hex[:4]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    _store_protected_order_intent(ticker)

    try:
        write_json(STATE_PATH, _state_with_position(ticker, oco_gtt_id="444"))
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id="exit-order-complete",
                exchange_order_id="exchange-exit-complete",
                ticker=ticker,
                order_intent_id=None,
                status="complete",
                broker_tag=None,
                payload={"status": "COMPLETE", "filled_quantity": 5, "pending_quantity": 0},
                source="test_phase5",
            )
            repo.upsert_broker_fill(
                fill_id="trade-exit-complete",
                broker_order_id="exit-order-complete",
                order_intent_id=None,
                ticker=ticker,
                quantity=5,
                fill_price=1075.0,
                payload={"trade_id": "trade-exit-complete"},
                source="test_phase5",
            )

        manager = ProtectionManager(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        manager.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="444",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="triggered",
                triggered_leg="target",
                exit_order_id="exit-order-complete",
                exit_order_status="complete",
            )
        )

        result = await manager.run_watchdog()

        assert result["closed"] == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"] == []
        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, "444")
            trade_row = session.query(TradeRow).filter_by(ticker=ticker).one()
        assert trigger_row is not None
        assert trigger_row.status == "exit_filled"
        assert trade_row.exit_reason == "gtt_target"
        assert trade_row.exit_price == 1075.0
    finally:
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_trailing_engine_uses_live_quote_with_hysteresis_and_cooldown():
    ticker = f"WIP{uuid4().hex[:5]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))

    try:
        write_json(STATE_PATH, _state_with_position(ticker, oco_gtt_id="555"))
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_protective_trigger(
                protective_trigger_id="555",
                position_id=ticker,
                ticker=ticker,
                status="active",
                payload={
                    "ticker": ticker,
                    "stop_price": 980.0,
                    "target_price": 1080.0,
                    "last_modified_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                },
                source="test_phase5",
            )

        engine = TrailingEngine(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        engine.gtt_manager.modify_gtt_async = AsyncMock()

        first = await engine.run_once(quote_provider=lambda _ticker: {"last_price": 1100.0})
        second = await engine.run_once(quote_provider=lambda _ticker: {"last_price": 1100.0})

        assert first["modified"] == 1
        assert second["modified"] == 0
        assert engine.gtt_manager.modify_gtt_async.await_count == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["current_price"] == 1100.0
        assert state["positions"][0]["stop_price"] == 1050.0
        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, "555")
        assert trigger_row is not None
        assert trigger_row.payload["stop_price"] == 1050.0
        assert int(trigger_row.payload["modification_count"]) == 1
    finally:
        write_json(STATE_PATH, original_state)
