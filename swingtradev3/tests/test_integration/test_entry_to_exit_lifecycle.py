from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from execution.coordinator import ExecutionCoordinator
from memory.db import session_scope
from memory.models import ProtectiveTriggerRow, TradeRow
from memory.repository import MemoryRepository
from models import AccountState, GTTOrder, PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"


def _intent_payload(ticker: str, order_intent_id: str) -> dict[str, object]:
    now = datetime.now()
    return PendingApproval.model_validate(
        {
            "ticker": ticker,
            "score": 8.9,
            "setup_type": "breakout",
            "entry_zone": {"low": 1000.0, "high": 1010.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 7,
            "confidence_reasoning": "Phase 9 lifecycle setup",
            "risk_flags": [],
            "sector": "IT",
            "approved": True,
            "order_intent_id": order_intent_id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=4)).isoformat(),
            "execution_requested": True,
            "execution_request_id": order_intent_id.rsplit(":", 1)[-1],
        }
    ).model_dump(mode="json")


def _store_order_intent(order_intent_id: str, ticker: str, payload: dict[str, object]) -> None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status="submitted",
            approval_id=str(payload.get("approval_id")),
            entry_intent_id=str(payload.get("entry_intent_id")),
            broker_order_id=str(payload.get("broker_order_id")),
            broker_tag=str(payload.get("broker_tag")),
            payload=dict(payload),
            source="test_phase9_lifecycle",
        )


@pytest.mark.asyncio
async def test_entry_fill_arms_stop_and_confirmed_stop_exit_closes_trade():
    ticker = f"LCY{uuid4().hex[:5]}".upper()
    order_intent_id = f"order-intent:{ticker}:entry-to-exit"
    broker_order_id = f"entry-{uuid4().hex[:8]}"
    exit_order_id = f"exit-{uuid4().hex[:8]}"
    gtt_id = f"gtt-{uuid4().hex[:8]}"
    payload = {
        **_intent_payload(ticker, order_intent_id),
        "broker_order_id": broker_order_id,
        "broker_tag": "STV3LIFECYCLE",
        "requested_quantity": 5,
    }
    original_state = deepcopy(read_json(STATE_PATH, {}))

    try:
        write_json(STATE_PATH, AccountState(cash_inr=250000.0, positions=[]).model_dump(mode="json"))
        _store_order_intent(order_intent_id, ticker, payload)
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id=broker_order_id,
                exchange_order_id=f"exchange-{uuid4().hex[:8]}",
                ticker=ticker,
                order_intent_id=order_intent_id,
                status="complete",
                broker_tag=str(payload["broker_tag"]),
                payload={
                    "order_id": broker_order_id,
                    "status": "COMPLETE",
                    "tradingsymbol": ticker,
                    "quantity": 5,
                    "filled_quantity": 5,
                    "pending_quantity": 0,
                    "average_price": 1000.0,
                },
                source="test_phase9_lifecycle",
            )
            repo.upsert_broker_fill(
                fill_id=f"entry-trade-{uuid4().hex[:8]}",
                broker_order_id=broker_order_id,
                order_intent_id=order_intent_id,
                ticker=ticker,
                quantity=5,
                fill_price=1000.0,
                payload={"side": "entry"},
                source="test_phase9_lifecycle",
            )

        coordinator = ExecutionCoordinator(
            alerts_tool=MagicMock(send_alert=AsyncMock()),
            gtt_manager=MagicMock(),
        )
        coordinator.gtt_manager.place_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id=gtt_id,
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="active",
            )
        )

        entry_result = await coordinator.reconcile_order_intent(order_intent_id)

        assert entry_result == "advanced"
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["entry_order_id"] == broker_order_id
        assert state["positions"][0]["oco_gtt_id"] == gtt_id

        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id=exit_order_id,
                exchange_order_id=f"exchange-{uuid4().hex[:8]}",
                ticker=ticker,
                order_intent_id=None,
                status="open",
                broker_tag=None,
                payload={"status": "OPEN", "filled_quantity": 0, "pending_quantity": 5},
                source="test_phase9_lifecycle",
            )

        coordinator.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id=gtt_id,
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="triggered",
                triggered_leg="stop",
                exit_order_id=exit_order_id,
                exit_order_status="open",
            )
        )

        open_result = await coordinator.protection_manager.run_watchdog()

        assert open_result["triggered"] == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["lifecycle_state"] == "closing"
        with session_scope() as session:
            trigger = session.get(ProtectiveTriggerRow, gtt_id)
        assert trigger is not None
        assert trigger.status == "exit_order_open"

        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id=exit_order_id,
                exchange_order_id=f"exchange-{uuid4().hex[:8]}",
                ticker=ticker,
                order_intent_id=None,
                status="complete",
                broker_tag=None,
                payload={"status": "COMPLETE", "filled_quantity": 5, "pending_quantity": 0},
                source="test_phase9_lifecycle",
            )
            repo.upsert_broker_fill(
                fill_id=f"exit-trade-{uuid4().hex[:8]}",
                broker_order_id=exit_order_id,
                order_intent_id=None,
                ticker=ticker,
                quantity=5,
                fill_price=980.0,
                payload={"side": "exit"},
                source="test_phase9_lifecycle",
            )

        coordinator.gtt_manager.get_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id=gtt_id,
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="triggered",
                triggered_leg="stop",
                exit_order_id=exit_order_id,
                exit_order_status="complete",
            )
        )

        close_result = await coordinator.protection_manager.run_watchdog()

        assert close_result["closed"] == 1
        state = read_json(STATE_PATH, {})
        assert state["positions"] == []
        with session_scope() as session:
            trigger = session.get(ProtectiveTriggerRow, gtt_id)
            trade = session.query(TradeRow).filter_by(ticker=ticker).one()
        assert trigger is not None
        assert trigger.status == "exit_filled"
        assert trade.exit_reason == "gtt_stop"
        assert trade.exit_price == 980.0
    finally:
        write_json(STATE_PATH, original_state)
