from __future__ import annotations

import urllib.request

from fastapi import APIRouter
from sqlalchemy import text

from config import cfg
from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from ..schemas.health import HealthResponse
from health_manager import get_all_statuses

router = APIRouter()

PHASE12_MEMORY_VIEWS = {
    "portfolio_risk_view",
    "open_positions_view",
    "execution_incidents_view",
    "policy_effective_view",
    "session_readiness_view",
    "recent_trades_view",
    "reconciliation_readiness_view",
    "operator_controls_view",
}


def _postgres_memory_views_status() -> str:
    try:
        with session_scope() as session:
            rows = session.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'public'
                      AND table_name = ANY(:view_names)
                    """
                ),
                {"view_names": sorted(PHASE12_MEMORY_VIEWS)},
            ).scalars()
            found = set(rows)
        return "healthy" if found >= PHASE12_MEMORY_VIEWS else "degraded"
    except Exception:
        return "unhealthy"


def _context_graph_status() -> str:
    if not cfg.context_graph.enabled:
        return "disabled"
    graph = ContextGraphRepository()
    try:
        status = graph.health().get("status")
        return "healthy" if status == "ok" else "degraded"
    except Exception:
        return "degraded"
    finally:
        graph.close()


def _toolbox_status() -> str:
    if not cfg.toolbox.enabled:
        return "disabled"
    try:
        url = f"{cfg.toolbox.url.rstrip('/')}/api/toolset"
        with urllib.request.urlopen(url, timeout=cfg.toolbox.timeout_seconds) as response:
            return "healthy" if response.status == 200 else "degraded"
    except Exception:
        return "degraded"


def _phase12_statuses() -> dict[str, str]:
    return {
        "postgres_memory_views": _postgres_memory_views_status(),
        "memgraph_context_graph": _context_graph_status(),
        "toolbox": _toolbox_status(),
    }


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {
        "app": "running",
    }
    services.update(get_all_statuses())
    services.update(_phase12_statuses())

    return HealthResponse(
        status="ok",
        mode="paper",
        services=services,
    )
