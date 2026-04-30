from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter

from execution.operator_controls import read_worker_status
from memory.db import session_scope
from memory.repositories import MemoryRepository

router = APIRouter()


def _portfolio_summary(state_payload: dict[str, Any]) -> dict[str, Any]:
    positions = list(state_payload.get("positions") or [])
    total_invested = 0.0
    sector_exposure: dict[str, float] = {}
    for position in positions:
        quantity = float(position.get("quantity") or 0)
        price = float(position.get("current_price") or position.get("entry_price") or 0)
        value = quantity * price
        total_invested += value
        sector = str(position.get("sector") or "Unknown")
        sector_exposure[sector] = sector_exposure.get(sector, 0.0) + value

    realized_pnl = float(state_payload.get("realized_pnl") or 0.0)
    unrealized_pnl = float(state_payload.get("unrealized_pnl") or 0.0)
    return {
        "cash_inr": float(state_payload.get("cash_inr") or 0.0),
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": realized_pnl + unrealized_pnl,
        "open_positions_count": len(positions),
        "sector_exposure": sector_exposure,
        "total_invested": total_invested,
        "drawdown_pct": float(state_payload.get("drawdown_pct") or 0.0),
        "weekly_loss_pct": float(state_payload.get("weekly_loss_pct") or 0.0),
        "consecutive_losses": int(state_payload.get("consecutive_losses") or 0),
    }


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(item.get("status") or "unknown") for item in items)
    return dict(sorted(counts.items()))


def _source_activity(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for event in events:
        source = str(event.get("source") or "unknown")
        current = grouped.setdefault(
            source,
            {
                "agent_name": source,
                "status": "observed",
                "event_count": 0,
                "last_event": None,
                "updated_at": None,
            },
        )
        current["event_count"] += 1
        current["last_event"] = event.get("event_type")
        current["updated_at"] = event.get("created_at")
    return list(grouped.values())


@router.get("/knowledge/index")
async def get_knowledge_index():
    """Phase 8 keeps the graph UI local-only; the real graph API is Phase 14."""
    return {
        "phase": "phase_14_mock",
        "status": "deferred",
        "stocks": {},
        "message": "Knowledge graph API is intentionally disabled until Phase 14.",
    }


@router.get("/knowledge/graph")
async def get_knowledge_graph():
    """Phase 8 deterministic placeholder; no context files are read here."""
    return {
        "phase": "phase_14_mock",
        "nodes": [
            {"id": "mock:regime", "label": "Regime", "type": "Regime"},
            {"id": "mock:stock", "label": "Candidate", "type": "Stock"},
            {"id": "mock:lesson", "label": "Lesson", "type": "Lesson"},
        ],
        "edges": [
            {"source": "mock:regime", "target": "mock:stock", "label": "constrains"},
            {"source": "mock:stock", "target": "mock:lesson", "label": "informs"},
        ],
    }


@router.get("/knowledge/stock/{ticker}")
async def get_stock_knowledge(ticker: str):
    """Phase 8 placeholder; real stock graph memory is deferred to Phase 14."""
    return {
        "phase": "phase_14_mock",
        "ticker": ticker.upper(),
        "summary": "Local mock only. Real Postgres/Memgraph memory arrives in Phase 14.",
        "evidence": [],
    }


@router.get("/snapshot")
async def get_dashboard_snapshot() -> dict[str, Any]:
    """Operator overview backed by Postgres execution truth."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        state = repo.get_account_state_payload()
        positions = repo.list_positions()
        approvals = repo.get_pending_approvals_payload()
        trades = repo.get_trades_payload()
        incidents = repo.list_failure_incidents(status="open")
        order_intents = repo.list_order_intents()
        broker_orders = repo.list_broker_orders()
        protective_triggers = repo.list_protective_triggers()
        latest_event_id = repo.get_latest_execution_event_id()

    return {
        "portfolio": _portfolio_summary(state),
        "account": state,
        "counts": {
            "positions": len(positions),
            "approvals": len(approvals),
            "trades": len(trades),
            "open_incidents": len(incidents),
            "order_intents": len(order_intents),
            "broker_orders": len(broker_orders),
            "protective_triggers": len(protective_triggers),
        },
        "status_counts": {
            "positions": _status_counts(positions),
            "approvals": _status_counts(approvals),
            "order_intents": _status_counts(order_intents),
            "broker_orders": _status_counts(broker_orders),
            "protective_triggers": _status_counts(protective_triggers),
        },
        "positions": [position["payload"] for position in positions],
        "approvals": approvals,
        "recent_trades": trades[:10],
        "open_incidents": incidents,
        "worker_status": read_worker_status() or {},
        "latest_event_id": latest_event_id,
    }


@router.get("/activity")
async def get_agent_activity():
    """Derived source activity from durable execution events."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        events = repo.list_execution_events(limit=200)
    return {
        "agents": _source_activity(events),
        "event_count": len(events),
    }


@router.get("/activity/{agent_name}")
async def get_agent_status(agent_name: str):
    """Derived status for one source from durable execution events."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        events = [
            event
            for event in repo.list_execution_events(limit=200)
            if str(event.get("source") or "").lower() == agent_name.lower()
        ]
    if not events:
        return {"agent_name": agent_name, "status": "unknown", "event_count": 0}
    return _source_activity(events)[0]


@router.get("/events")
async def get_recent_events(
    limit: int = 20,
    after_id: int | None = None,
    event_type: str | None = None,
):
    """Durable execution-event feed for dashboard tables and SSE resume."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.list_execution_events(limit=limit, after_id=after_id, event_type=event_type)


@router.get("/execution")
async def get_execution_dashboard() -> dict[str, Any]:
    """Full execution state machine surface for the React dashboard."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        positions = repo.list_positions()
        order_intents = repo.list_order_intents()
        broker_orders = repo.list_broker_orders()
        broker_fills = repo.list_broker_fills()
        protective_triggers = repo.list_protective_triggers()
        reconciliation_runs = repo.list_reconciliation_runs(limit=20)
        incidents = repo.list_failure_incidents()
        entry_intents = repo.list_entry_intents()

    return {
        "positions": positions,
        "entry_intents": entry_intents,
        "order_intents": order_intents,
        "broker_orders": broker_orders,
        "broker_fills": broker_fills,
        "protective_triggers": protective_triggers,
        "reconciliation_runs": reconciliation_runs,
        "incidents": incidents,
        "status_counts": {
            "positions": _status_counts(positions),
            "entry_intents": _status_counts(entry_intents),
            "order_intents": _status_counts(order_intents),
            "broker_orders": _status_counts(broker_orders),
            "protective_triggers": _status_counts(protective_triggers),
            "incidents": _status_counts(incidents),
        },
    }


@router.get("/quotes")
async def get_dashboard_quotes() -> dict[str, Any]:
    """Quote-facing dashboard model derived from broker-confirmed positions."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        positions = repo.list_positions()

    quotes = []
    for position in positions:
        payload = dict(position.get("payload") or {})
        current_price = payload.get("current_price")
        quotes.append(
            {
                "ticker": position.get("ticker"),
                "price": current_price or payload.get("entry_price"),
                "source": "position",
                "stale": current_price is None,
                "position_state": position.get("state"),
                "updated_at": None,
            }
        )
    return {"quotes": quotes, "count": len(quotes)}


@router.get("/broker")
async def get_dashboard_broker() -> dict[str, Any]:
    """Broker state without exposing secret auth material."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        auth_session = repo.get_auth_session_payload()
        broker_orders = repo.list_broker_orders()
        broker_fills = repo.list_broker_fills()

    return {
        "auth_session": {
            "provider": "kite",
            "user_id": auth_session.get("user_id"),
            "user_name": auth_session.get("user_name"),
            "has_api_key": bool(auth_session.get("api_key")),
            "has_access_token": bool(auth_session.get("access_token")),
            "created_at": auth_session.get("created_at"),
            "login_time": auth_session.get("login_time"),
        },
        "broker_orders": broker_orders,
        "broker_fills": broker_fills,
        "status_counts": {
            "broker_orders": _status_counts(broker_orders),
        },
    }


@router.get("/telemetry")
async def get_dashboard_telemetry(limit: int = 100) -> dict[str, Any]:
    """Runtime telemetry backed by durable execution events and controls."""
    with session_scope() as session:
        repo = MemoryRepository(session)
        events = repo.list_execution_events(limit=limit)
        controls = repo.list_operator_controls()

    return {
        "worker_status": read_worker_status() or {},
        "events": events,
        "operator_controls": controls,
        "event_type_counts": dict(Counter(event["event_type"] for event in events)),
        "source_counts": dict(Counter(event["source"] for event in events)),
    }


@router.get("/scheduler")
async def get_scheduler_info():
    """Get scheduler status and current phase."""
    status = read_worker_status()
    if status is not None:
        return status
    return {
        "is_running": False,
        "current_phase": "stopped",
        "total_jobs": 0,
        "next_run": None,
        "next_task": None,
        "failed_events": 0,
    }
