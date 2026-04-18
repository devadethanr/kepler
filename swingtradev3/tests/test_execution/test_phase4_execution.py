from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from config import cfg
from execution.coordinator import ExecutionCoordinator
from memory.db import session_scope
from memory.models import ApprovalRow, BrokerFillRow, ProtectiveTriggerRow
from memory.repositories import MemoryRepository
from models import AccountState, GTTOrder, PendingApproval, TradingMode
from paths import CONTEXT_DIR
from storage import read_json, write_json


APPROVALS_PATH = CONTEXT_DIR / "pending_approvals.json"
STATE_PATH = CONTEXT_DIR / "state.json"


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
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
        "confidence_reasoning": "Phase 4 setup",
        "risk_flags": [],
        "sector": "energy",
        "approved": True,
        "order_intent_id": order_intent_id,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=4)).isoformat(),
        "execution_requested": True,
        "execution_request_id": order_intent_id.rsplit(":", 1)[-1],
        }
    ).model_dump(mode="json")


def _store_order_intent(order_intent_id: str, ticker: str, *, status: str, payload: dict[str, object]) -> None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        repo.upsert_order_intent(
            order_intent_id=order_intent_id,
            ticker=ticker,
            status=status,
            approval_id=(
                str(payload.get("approval_id"))
                if payload.get("approval_id") not in (None, "")
                else None
            ),
            entry_intent_id=(
                str(payload.get("entry_intent_id"))
                if payload.get("entry_intent_id") not in (None, "")
                else None
            ),
            broker_order_id=(
                str(payload.get("broker_order_id"))
                if payload.get("broker_order_id") not in (None, "")
                else None
            ),
            broker_tag=payload.get("broker_tag") if isinstance(payload.get("broker_tag"), str) else None,
            payload=dict(payload),
            source="test_phase4",
        )


@pytest.mark.asyncio
async def test_execution_coordinator_submits_queued_intent_and_removes_pending_approval(monkeypatch):
    ticker = f"REL{uuid4().hex[:6]}".upper()
    order_intent_id = f"order-intent:{ticker}:req-phase4"
    intent_payload = _intent_payload(ticker, order_intent_id)
    original_approvals = read_json(APPROVALS_PATH, [])
    original_state = read_json(STATE_PATH, {})

    try:
        _store_order_intent(order_intent_id, ticker, status="queued", payload=intent_payload)
        write_json(APPROVALS_PATH, [intent_payload])
        write_json(STATE_PATH, AccountState(cash_inr=150000.0, positions=[]).model_dump(mode="json"))

        coordinator = ExecutionCoordinator(
            risk_tool=MagicMock(),
            order_tool=MagicMock(),
            alerts_tool=MagicMock(),
        )
        coordinator.risk_tool.check_risk = MagicMock(
            return_value={"approved": True, "quantity": 5, "reason": "ok"}
        )
        coordinator.order_tool.place_order_async = AsyncMock(
            return_value={
                "status": "submitted",
                "order_id": "kite-order-phase4",
                "quantity": 5,
                "broker_tag": "STV3RELPHASE4TAG",
                "protection_status": "pending_fill_confirmation",
            }
        )
        coordinator.alerts_tool.send_alert = AsyncMock()
        detector = MagicMock()
        detector.detect_regime = MagicMock(return_value={"regime": "bull"})
        monkeypatch.setattr("execution.coordinator.MarketRegimeDetector", lambda: detector)
        monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

        result = await coordinator.submit_order_intent(order_intent_id)

        assert result == "submitted"
        with session_scope() as session:
            repo = MemoryRepository(session)
            order_intent = repo.get_order_intent(order_intent_id)
            approval_row = session.get(ApprovalRow, intent_payload["approval_id"])
        assert order_intent is not None
        assert order_intent["status"] == "submitted"
        assert order_intent["broker_tag"] == "STV3RELPHASE4TAG"
        assert order_intent["payload"]["broker_order_id"] == "kite-order-phase4"
        assert approval_row is not None
        assert approval_row.status == "submitted"
        approvals = read_json(APPROVALS_PATH, [])
        assert [item["ticker"] for item in approvals if item.get("ticker") == ticker] == []
    finally:
        write_json(APPROVALS_PATH, original_approvals)
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_execution_coordinator_removes_only_matching_candidate_for_same_ticker(monkeypatch):
    ticker = f"SBI{uuid4().hex[:5]}".upper()
    first_intent_id = f"order-intent:{ticker}:phase4-a"
    second_intent_id = f"order-intent:{ticker}:phase4-b"
    first_payload = _intent_payload(ticker, first_intent_id)
    second_payload = {
        **_intent_payload(ticker, second_intent_id),
        "setup_type": "pullback",
        "stop_price": 975.0,
        "target_price": 1090.0,
    }
    second_payload.pop("approval_id", None)
    second_payload.pop("entry_intent_id", None)
    second_payload = PendingApproval.model_validate(second_payload).model_dump(mode="json")
    original_approvals = read_json(APPROVALS_PATH, [])
    original_state = read_json(STATE_PATH, {})

    try:
        _store_order_intent(first_intent_id, ticker, status="queued", payload=first_payload)
        _store_order_intent(second_intent_id, ticker, status="queued", payload=second_payload)
        write_json(APPROVALS_PATH, [first_payload, second_payload])
        write_json(STATE_PATH, AccountState(cash_inr=150000.0, positions=[]).model_dump(mode="json"))

        coordinator = ExecutionCoordinator(
            risk_tool=MagicMock(),
            order_tool=MagicMock(),
            alerts_tool=MagicMock(),
        )
        coordinator.risk_tool.check_risk = MagicMock(
            return_value={"approved": True, "quantity": 5, "reason": "ok"}
        )
        coordinator.order_tool.place_order_async = AsyncMock(
            return_value={
                "status": "submitted",
                "order_id": "kite-order-same-ticker",
                "quantity": 5,
                "broker_tag": "STV3SBIPHASE4TAG",
                "protection_status": "pending_fill_confirmation",
            }
        )
        coordinator.alerts_tool.send_alert = AsyncMock()
        detector = MagicMock()
        detector.detect_regime = MagicMock(return_value={"regime": "bull"})
        monkeypatch.setattr("execution.coordinator.MarketRegimeDetector", lambda: detector)
        monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

        result = await coordinator.submit_order_intent(first_intent_id)

        assert result == "submitted"
        approvals = read_json(APPROVALS_PATH, [])
        remaining_ids = {item["approval_id"] for item in approvals}
        assert first_payload["approval_id"] not in remaining_ids
        assert second_payload["approval_id"] in remaining_ids
    finally:
        write_json(APPROVALS_PATH, original_approvals)
        write_json(STATE_PATH, original_state)


@pytest.mark.asyncio
async def test_execution_coordinator_materializes_filled_intent_and_arms_protection(monkeypatch):
    ticker = f"INF{uuid4().hex[:6]}".upper()
    order_intent_id = f"order-intent:{ticker}:req-phase4-fill"
    broker_order_id = f"kite-order-{uuid4().hex[:8]}"
    intent_payload = {
        **_intent_payload(ticker, order_intent_id),
        "broker_tag": "STV3INFPHASE4TAG",
        "requested_quantity": 5,
        "broker_order_id": broker_order_id,
    }
    original_state = read_json(STATE_PATH, {})

    try:
        write_json(STATE_PATH, AccountState(cash_inr=250000.0, positions=[]).model_dump(mode="json"))
        _store_order_intent(order_intent_id, ticker, status="submitted", payload=intent_payload)
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_broker_order(
                broker_order_id=broker_order_id,
                exchange_order_id=f"exchange-{uuid4().hex[:8]}",
                ticker=ticker,
                order_intent_id=order_intent_id,
                status="complete",
                broker_tag="STV3INFPHASE4TAG",
                payload={
                    "order_id": broker_order_id,
                    "exchange_order_id": f"exchange-{uuid4().hex[:8]}",
                    "status": "COMPLETE",
                    "tradingsymbol": ticker,
                    "quantity": 5,
                    "filled_quantity": 5,
                    "pending_quantity": 0,
                    "average_price": 1012.5,
                    "exchange_update_timestamp": "2026-04-18 09:20:00",
                },
                source="test_phase4",
            )
            repo.upsert_broker_fill(
                fill_id=f"trade-{uuid4().hex[:8]}",
                broker_order_id=broker_order_id,
                order_intent_id=order_intent_id,
                ticker=ticker,
                quantity=5,
                fill_price=1012.5,
                payload={"trade_id": "trade-1"},
                source="test_phase4",
            )

        coordinator = ExecutionCoordinator(
            alerts_tool=MagicMock(),
            gtt_manager=MagicMock(),
        )
        coordinator.alerts_tool.send_alert = AsyncMock()
        coordinator.gtt_manager.place_gtt_async = AsyncMock(
            return_value=GTTOrder(
                oco_gtt_id="34567",
                ticker=ticker,
                stop_price=980.0,
                target_price=1080.0,
            )
        )
        monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)

        result = await coordinator.reconcile_order_intent(order_intent_id)

        assert result == "advanced"
        with session_scope() as session:
            repo = MemoryRepository(session)
            order_intent = repo.get_order_intent(order_intent_id)
            trigger = session.get(ProtectiveTriggerRow, "34567")
        assert order_intent is not None
        assert order_intent["status"] == "protected"
        assert order_intent["payload"]["oco_gtt_id"] == "34567"
        assert trigger is not None
        assert trigger.status == "active"
        state = read_json(STATE_PATH, {})
        positions = [item for item in state.get("positions", []) if item.get("ticker") == ticker]
        assert len(positions) == 1
        assert positions[0]["entry_order_id"] == broker_order_id
        assert positions[0]["oco_gtt_id"] == "34567"
    finally:
        write_json(STATE_PATH, original_state)


def test_broker_reducer_uses_order_trades_for_partial_fill(monkeypatch):
    from broker.reducer import BrokerReducer

    reducer = BrokerReducer()
    suffix = uuid4().hex[:8]
    order_id = f"kite-order-partial-{suffix}"
    trade_id = f"trade-{suffix}"

    monkeypatch.setattr(
        "broker.reducer.fetch_order_trades",
        lambda broker_order_id: [
            {
                "trade_id": trade_id,
                "order_id": broker_order_id,
                "tradingsymbol": "TCS",
                "average_price": 4012.5,
                "quantity": 3,
                "fill_timestamp": "2026-04-18 09:31:00",
                "exchange_timestamp": "2026-04-18 09:31:00",
            }
        ],
    )

    payload = {
        "order_id": order_id,
        "exchange_order_id": f"exchange-order-{suffix}",
        "status": "OPEN",
        "tradingsymbol": "TCS",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "quantity": 5,
        "filled_quantity": 3,
        "pending_quantity": 2,
        "cancelled_quantity": 0,
        "average_price": 0,
        "price": 4010.0,
        "tag": "STV3TCSPHASE4TAG",
        "exchange_update_timestamp": "2026-04-18 09:31:00",
    }

    result = reducer.apply_order_update(payload, source="websocket")

    assert result["status"] == "applied"
    with session_scope() as session:
        fill_row = session.get(BrokerFillRow, trade_id)
    assert fill_row is not None
    assert fill_row.quantity == 3
    assert fill_row.fill_price == 4012.5
