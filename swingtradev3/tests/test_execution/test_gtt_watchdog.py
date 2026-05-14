from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from execution.operator_controls import read_block_new_entries
from execution.protection_manager import ProtectionManager
from memory.db import session_scope
from memory.models import ProtectiveTriggerRow
from memory.repository import MemoryRepository
from models import AccountState, GTTOrder, PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"


def _state_with_unprotected_position(ticker: str) -> dict[str, object]:
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
                "sector": "IT",
                "pending_corporate_action": {},
            }
        ],
    ).model_dump(mode="json")


def _store_order_intent(ticker: str) -> PendingApproval:
    approval = PendingApproval.model_validate(
        {
            "ticker": ticker,
            "score": 8.8,
            "setup_type": "breakout",
            "entry_zone": {"low": 995.0, "high": 1000.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 8,
            "confidence_reasoning": "Phase 9 rejected GTT setup",
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
            status="protection_pending",
            approval_id=approval.approval_id,
            entry_intent_id=approval.entry_intent_id,
            broker_order_id="entry-order-1",
            broker_tag="STV3PHASE9GTT",
            payload={**approval.model_dump(mode="json"), "broker_order_id": "entry-order-1"},
            source="test_phase9_gtt",
        )
    return approval


@pytest.mark.asyncio
async def test_rejected_gtt_arm_blocks_entries_and_requires_operator_intervention():
    ticker = f"GTR{uuid4().hex[:5]}".upper()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    approval = _store_order_intent(ticker)

    try:
        write_json(STATE_PATH, _state_with_unprotected_position(ticker))
        manager = ProtectionManager(
            gtt_manager=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
        )
        manager.gtt_manager.place_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="rejected-arm-gtt",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="rejected",
            )
        )

        result = await manager.arm_for_order_intent(str(approval.order_intent_id))

        assert result == "failed"
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["oco_gtt_id"] == "rejected-arm-gtt"
        assert state["positions"][0]["lifecycle_state"] == "operator_intervention"
        block = read_block_new_entries() or {}
        assert "gtt_rejected" in block.get("active_reasons", [])
        with session_scope() as session:
            repo = MemoryRepository(session)
            trigger = session.get(ProtectiveTriggerRow, "rejected-arm-gtt")
            order_intent = repo.get_order_intent(str(approval.order_intent_id))
        assert trigger is not None
        assert trigger.status == "rejected"
        assert order_intent is not None
        assert order_intent["status"] == "protection_pending"
        assert order_intent["payload"]["protection_status"] == "rejected"
    finally:
        write_json(STATE_PATH, original_state)
