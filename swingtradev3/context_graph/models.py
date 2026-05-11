from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphDashboardPayload(BaseModel):
    phase: str = "phase_11"
    status: str = "ok"
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    generated_at_ist: str | None = None
    message: str | None = None


class StockGraphContext(BaseModel):
    ticker: str
    has_history: bool = False
    research: list[dict[str, Any]] = Field(default_factory=list)
    news: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    generated_at_ist: str | None = None


class ProjectionResult(BaseModel):
    projected: int = 0
    latest_event_id: int | None = None
    status: str = "ok"
    error: str | None = None


class ResearchRunPayload(BaseModel):
    run_id: str
    scan_date: str
    analyzed_at: datetime
    regime: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)
    qualified_count: int = 0
    total_screened: int = 0
    shortlist_count: int = 0

