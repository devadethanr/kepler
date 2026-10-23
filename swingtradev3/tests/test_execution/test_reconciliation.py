from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from config import cfg
from execution.coordinator import ExecutionCoordinator
from memory.db import session_scope
from memory.models import ProtectiveTriggerRow
from memory.repository import MemoryRepository
from models import AccountState, GTTOrder, PendingApproval, TradingMode
from paths import CONTEXT_DIR
from storage import read_json, write_json


APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"
STATE_PATH = CONTEXT_DIR / "state.json"


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        with patch("execution.coordinator.is_session_fresh", return_value=(True, None, 1.0)):
            yield


def _intent_payload(ticker: str, order_intent_id: str) -> dict[str, object]:
    now = datetime.now()
    return PendingApproval.model_validate(
        {
            "ticker": ticker,
            "score": 8.6,
            "setup_type": "breakout",
            "entry_zone": {"low": 1000.0, "high": 1010.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 7,
            "confidence_reasoning": "Phase 9 timeout reconciliation setup",
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


def _store_order_intent(
    order_intent_id: str,
    ticker: str,
    *,
    status: str,
    payload: dict[str, object],
    broker_tag: str | None = None,
) -> None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            approval_id=str(payload.get("approval_id")),
            entry_intent_id=str(payload.get("entry_intent_id")),
            broker_order_id=(
                str(payload.get("broker_order_id"))
                if payload.get("broker_order_id") not in (None, "")
                else None
            ),
            broker_tag=broker_tag,
            payload=dict(payload),
            source="test_phase9_reconciliation",
        )


@pytest.mark.asyncio
async def test_submission_timeout_reconciles_later_fill_by_broker_tag(monkeypatch):
    ticker = f"TMO{uuid4().hex[:5]}".upper()
    order_intent_id = f"order-intent:{ticker}:timeout-retry"
    broker_tag = "STV3TIMEOUTRETRY"
    broker_order_id = f"kite-timeout-{uuid4().hex[:8]}"
    payload = _intent_payload(ticker, order_intent_id)
    original_approvals = read_json(APPROVALS_PATH, [])
    original_state = read_json(STATE_PATH, {})

    try:
        write_json(APPROVALS_PATH, [payload])
        write_json(STATE_PATH, AccountState(cash_inr=250000.0, positions=[]).model_dump(mode="json"))
        _store_order_intent(order_intent_id, ticker, status="queued", payload=payload)

        coordinator = ExecutionCoordinator(
            risk_tool=MagicMock(),
            order_tool=MagicMock(),
            alerts_tool=MagicMock(send_alert=AsyncMock()),
            gtt_manager=MagicMock(),
        )
        coordinator.risk_tool.check_risk = MagicMock(
            return_value={"approved": True, "quantity": 5, "reason": "ok"}
        )
        coordinator.order_tool.place_order_async = AsyncMock(
            return_value={
                "status": "submission_uncertain",
                "reason": "live_order_submission_timeout",
                "quantity": 5,
                "broker_tag": broker_tag,
                "protection_status": "pending_broker_reconciliation",
            }
        )
        detector = MagicMock()
        detector.detect_regime = MagicMock(return_value={"regime": "bull"})
        monkeypatch.setattr("execution.coordinator.MarketRegimeDetector", lambda: detector)
        monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

        submit_result = await coordinator.submit_order_intent(order_intent_id)

        assert submit_result == "submitting"
        with session_scope() as session:
            repo = MemoryRepository(session)
            order_intent = repo.get_order_intent(order_intent_id)
        assert order_intent is not None
        assert order_intent["status"] == "submitting"
        assert order_intent["broker_tag"] == broker_tag
        assert order_intent["payload"]["reconciliation_required"] is True
        approvals = read_json(APPROVALS_PATH, [])
        assert all(str(item.get("order_intent_id")) != order_intent_id for item in approvals)

        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id=broker_order_id,
                exchange_order_id=f"exchange-{uuid4().hex[:8]}",
                ticker=ticker,
                order_intent_id=order_intent_id,
                status="complete",
                broker_tag=broker_tag,
                payload={
                    "order_id": broker_order_id,
                    "status": "COMPLETE",
                    "tradingsymbol": ticker,
                    "quantity": 5,
                    "filled_quantity": 5,
                    "pending_quantity": 0,
                    "average_price": 1012.5,
                    "tag": broker_tag,
                },
                source="test_phase9_reconciliation",
            )
            repo.upsert_broker_fill(
                fill_id=f"trade-{uuid4().hex[:8]}",
                broker_order_id=broker_order_id,
                order_intent_id=order_intent_id,
                ticker=ticker,
                quantity=5,
                fill_price=1012.5,
                payload={"trade_id": f"trade-{uuid4().hex[:8]}"},
                source="test_phase9_reconciliation",
            )

        coordinator.gtt_manager.place_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="timeout-retry-gtt",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
                status="active",
            )
        )

        reconcile_result = await coordinator.reconcile_order_intent(order_intent_id)

        assert reconcile_result == "advanced"
        state = read_json(STATE_PATH, {})
        assert state["positions"][0]["ticker"] == ticker
        assert state["positions"][0]["entry_order_id"] == broker_order_id
        assert state["positions"][0]["oco_gtt_id"] == "timeout-retry-gtt"
        with session_scope() as session:
            repo = MemoryRepository(session)
            order_intent = repo.get_order_intent(order_intent_id)
            trigger = session.get(ProtectiveTriggerRow, "timeout-retry-gtt")
        assert order_intent is not None
        assert order_intent["status"] == "protected"
        assert trigger is not None
        assert trigger.status == "active"
    finally:
        write_json(APPROVALS_PATH, original_approvals)
        with session_scope() as session:
            MemoryRepository(session).replace_pending_approvals(
                original_approvals,
                source="test_reconciliation_restore",
            )
        write_json(STATE_PATH, original_state)
