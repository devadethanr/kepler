"""
API routes for the Knowledge Graph, Event Bus, and Agent Activity.
Powers the dashboard's real-time views.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.tasks.event_bus import event_bus, EventType
from api.tasks.activity_manager import activity_manager
from api.tasks.scheduler import scheduler
from knowledge.wiki_renderer import (
    get_stock_context,
    INDEX_PATH,
    GRAPH_PATH,
)
from storage import read_json

router = APIRouter()


# ─────────────────────────────────────────────────────────────
# Knowledge Graph
# ─────────────────────────────────────────────────────────────

@router.get("/knowledge/index")
async def get_knowledge_index():
    """Get the full Knowledge Graph index (fast lookup of all stocks)."""
    return read_json(INDEX_PATH, {"stocks": {}})


@router.get("/knowledge/graph")
async def get_knowledge_graph():
    """Get the Knowledge Graph (nodes + edges for visualization)."""
    return read_json(GRAPH_PATH, {"nodes": [], "edges": []})


@router.get("/knowledge/stock/{ticker}")
async def get_stock_knowledge(ticker: str):
    """Get historical context for a specific stock from the KG."""
    ctx = get_stock_context(ticker.upper())
    return ctx.model_dump(mode="json")


# ─────────────────────────────────────────────────────────────
# Agent Activity
# ─────────────────────────────────────────────────────────────

@router.get("/activity")
async def get_agent_activity():
    """Get current activity snapshot for all agents."""
    return activity_manager.get_snapshot().model_dump(mode="json")


@router.get("/activity/{agent_name}")
async def get_agent_status(agent_name: str):
    """Get a specific agent's current status."""
    status = activity_manager.get_agent_status(agent_name)
    if status is None:
        return {"agent_name": agent_name, "status": "unknown"}
    return status.model_dump(mode="json")


# ─────────────────────────────────────────────────────────────
# Event Bus
# ─────────────────────────────────────────────────────────────

@router.get("/events")
async def get_recent_events(limit: int = 20, event_type: str | None = None):
    """Get recent events from the event bus."""
    et = EventType(event_type) if event_type else None
    events = event_bus.get_recent(event_type=et, limit=limit)
    return [e.model_dump(mode="json") for e in events]


# ─────────────────────────────────────────────────────────────
# Scheduler
# ─────────────────────────────────────────────────────────────

@router.get("/scheduler")
async def get_scheduler_info():
    """Get scheduler status and current phase."""
    return scheduler.get_schedule_info()
