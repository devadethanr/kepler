from __future__ import annotations

from copy import deepcopy
import uuid

from broker.reducer import BrokerReducer
from memory.db import session_scope
from memory.models import BrokerFillRow, BrokerOrderRow, ExecutionEventRow, ProtectiveTriggerRow
from memory.repositories import MemoryRepository
from models import PendingApproval
from paths import CONTEXT_DIR
from storage import read_json, write_json


STATE_PATH = CONTEXT_DIR / "state.json"


def test_broker_reducer_deduplicates_order_updates_and_creates_fill():
    reducer = BrokerReducer()
    suffix = uuid.uuid4().hex[:8]
    order_id = f"kite-order-{suffix}"
    exchange_order_id = f"exchange-order-{suffix}"
    payload = {
        "order_id": order_id,
        "exchange_order_id": exchange_order_id,
        "status": "COMPLETE",
        "tradingsymbol": "RELIANCE",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "quantity": 5,
        "filled_quantity": 5,
        "pending_quantity": 0,
        "cancelled_quantity": 0,
        "average_price": 1012.5,
        "price": 1010.0,
        "tag": "STV3REL12345678",
        "exchange_update_timestamp": "2026-04-17 09:20:00",
    }

    first = reducer.apply_order_update(payload, source="websocket")
    second = reducer.apply_order_update(payload, source="websocket")

    assert first["status"] == "applied"
    assert second["status"] == "deduplicated"

    with session_scope() as session:
        order_row = session.get(BrokerOrderRow, order_id)
        fill_rows = session.query(BrokerFillRow).filter_by(broker_order_id=order_id).all()
        event_rows = (
            session.query(ExecutionEventRow)
            .filter_by(event_type="broker_event_applied", entity_type="broker_event")
            .all()
        )

    assert order_row is not None
    assert order_row.status == "complete"
    assert order_row.broker_tag == "STV3REL12345678"
    assert len(fill_rows) == 1
    assert fill_rows[0].quantity == 5
    assert len(event_rows) >= 1


def test_broker_reducer_deduplicates_same_order_across_sources():
    reducer = BrokerReducer()
    suffix = uuid.uuid4().hex[:8]
    order_id = f"kite-order-cross-{suffix}"
    payload = {
        "order_id": order_id,
        "exchange_order_id": f"exchange-order-{suffix}",
        "status": "COMPLETE",
        "tradingsymbol": "TCS",
        "exchange": "NSE",
        "transaction_type": "BUY",
        "quantity": 3,
        "filled_quantity": 3,
        "pending_quantity": 0,
        "cancelled_quantity": 0,
        "average_price": 4012.5,
        "price": 4010.0,
        "tag": "STV3TCS123456789",
        "exchange_update_timestamp": "2026-04-17 09:25:00",
    }

    first = reducer.apply_order_update(payload, source="websocket")
    second = reducer.apply_order_update(payload, source="postback")

    assert first["status"] == "applied"
    assert second["status"] == "deduplicated"

    with session_scope() as session:
        fill_rows = session.query(BrokerFillRow).filter_by(broker_order_id=order_id).all()

    assert len(fill_rows) == 1


def test_broker_reducer_projects_positions_from_broker_truth_and_gtt():
    reducer = BrokerReducer()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    ticker = f"INF{uuid.uuid4().hex[:5]}".upper()
    trigger_id = str(int(uuid.uuid4().hex[:6], 16))
    seed_state = {
        "cash_inr": 100000.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "drawdown_pct": 0.0,
        "weekly_loss_pct": 0.0,
        "consecutive_losses": 0,
        "positions": [],
    }

    gtt_payload = [
        {
            "id": trigger_id,
            "status": "active",
            "condition": {
                "exchange": "NSE",
                "tradingsymbol": ticker,
                "trigger_values": [1400.0, 1600.0],
            },
            "orders": [
                {"tradingsymbol": ticker, "result": None},
                {"tradingsymbol": ticker, "result": None},
            ],
        }
    ]
    positions_payload = {
        "net": [
            {
                "tradingsymbol": ticker,
                "quantity": 2,
                "average_price": 1500.0,
                "last_price": 1510.0,
            }
        ]
    }

    try:
        write_json(STATE_PATH, seed_state)
        reducer.apply_gtt_snapshot(gtt_payload, source="rest_snapshot")
        result = reducer.apply_position_snapshot(positions_payload, [], source="rest_snapshot")

        assert result["status"] == "ok"
        projected = read_json(STATE_PATH, {})
        assert projected["positions"][0]["ticker"] == ticker
        assert projected["positions"][0]["quantity"] == 2
        assert projected["positions"][0]["stop_price"] == 1400.0
        assert projected["positions"][0]["target_price"] == 1600.0
        assert projected["positions"][0]["oco_gtt_id"] == trigger_id
        assert projected["positions"][0]["lifecycle_state"] == "open"

        with session_scope() as session:
            trigger_row = session.get(ProtectiveTriggerRow, trigger_id)
        assert trigger_row is not None
        assert trigger_row.status == "active"
    finally:
        write_json(STATE_PATH, original_state)


def test_broker_reducer_persists_triggered_leg_and_exit_order_metadata():
    reducer = BrokerReducer()
    trigger_id = f"{int(uuid.uuid4().hex[:6], 16)}"
    payload = [
        {
            "id": trigger_id,
            "status": "triggered",
            "condition": {
                "exchange": "NSE",
                "tradingsymbol": "INFY",
                "trigger_values": [1400.0, 1600.0],
            },
            "orders": [
                {"tradingsymbol": "INFY", "result": None},
                {
                    "tradingsymbol": "INFY",
                    "result": {
                        "account_id": "AB1234",
                        "timestamp": "2026-04-18 10:15:00",
                        "triggered_at": 1600.0,
                        "order_result": {
                            "status": "complete",
                            "order_id": "exit-trigger-order",
                            "exchange_order_id": "exit-trigger-exchange",
                        },
                    },
                },
            ],
        }
    ]

    result = reducer.apply_gtt_snapshot(payload, source="rest_snapshot")

    assert result["status"] == "ok"
    with session_scope() as session:
        trigger_row = session.get(ProtectiveTriggerRow, trigger_id)
    assert trigger_row is not None
    assert trigger_row.status == "exit_filled"
    assert trigger_row.payload["broker_status"] == "triggered"
    assert trigger_row.payload["triggered_leg"] == "target"
    assert trigger_row.payload["exit_order_id"] == "exit-trigger-order"
    assert trigger_row.payload["exit_order_status"] == "complete"


def test_broker_reducer_backfills_order_intent_before_projecting_position():
    reducer = BrokerReducer()
    original_state = deepcopy(read_json(STATE_PATH, {}))
    ticker = f"HDFC{uuid.uuid4().hex[:4]}".upper()
    approval = PendingApproval.model_validate(
        {
            "ticker": ticker,
            "score": 8.7,
            "setup_type": "breakout",
            "entry_zone": {"low": 1500.0, "high": 1510.0},
            "stop_price": 1460.0,
            "target_price": 1600.0,
            "holding_days_expected": 8,
            "confidence_reasoning": "Reducer reconstruction test",
            "risk_flags": [],
            "approved": True,
            "execution_requested": True,
            "created_at": "2026-04-18T08:00:00",
            "expires_at": "2026-04-18T12:00:00",
        }
    )
    positions_payload = {
        "net": [
            {
                "tradingsymbol": ticker,
                "quantity": 3,
                "average_price": 1505.0,
                "last_price": 1512.0,
            }
        ]
    }

    try:
        write_json(STATE_PATH, {
            "cash_inr": 100000.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "drawdown_pct": 0.0,
            "weekly_loss_pct": 0.0,
            "consecutive_losses": 0,
            "positions": [],
        })
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_order_intent(
                order_intent_id=str(approval.order_intent_id),
                ticker=ticker,
                status="submitted",
                approval_id=approval.approval_id,
                entry_intent_id=approval.entry_intent_id,
                broker_order_id="kite-order-reconcile",
                broker_tag="STV3REDUCERTEST",
                payload={
                    **approval.model_dump(mode="json"),
                    "broker_order_id": "kite-order-reconcile",
                },
                source="test_broker_reducer",
            )

        result = reducer.apply_position_snapshot(positions_payload, [], source="rest_snapshot")

        assert result["status"] == "ok"
        projected = read_json(STATE_PATH, {})
        assert projected["positions"][0]["ticker"] == ticker
        assert projected["positions"][0]["stop_price"] == 1460.0
        assert projected["positions"][0]["target_price"] == 1600.0
        assert projected["positions"][0]["entry_order_id"] == "kite-order-reconcile"

        with session_scope() as session:
            repo = MemoryRepository(session)
            order_intent = repo.get_order_intent(str(approval.order_intent_id))
        assert order_intent is not None
        assert order_intent["status"] == "protection_pending"
        assert order_intent["payload"]["broker_position_quantity"] == 3
    finally:
        write_json(STATE_PATH, original_state)
