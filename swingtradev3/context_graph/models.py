from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None
    summary: str | None = None
    val: float | None = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    properties: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    relationship: str | None = None
    weight: float = 1.0


class GraphDashboardPayload(BaseModel):
    phase: str = "phase_11"
    status: str = "ok"
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    generated_at_ist: str | None = None
    last_updated: str | None = None
    message: str | None = None
    degraded_reason: str | None = None
    last_error: str | None = None


class StockGraphContext(BaseModel):
    ticker: str
    status: str = "available"
    has_history: bool = False
    summary: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    connections: list[dict[str, Any]] = Field(default_factory=list)
    research: list[dict[str, Any]] = Field(default_factory=list)
    news: list[dict[str, Any]] = Field(default_factory=list)
    observations: list[dict[str, Any]] = Field(default_factory=list)
    generated_at_ist: str | None = None
    last_updated: str | None = None
    message: str | None = None
    degraded_reason: str | None = None
    last_error: str | None = None


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
