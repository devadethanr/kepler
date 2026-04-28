"""
Knowledge Graph Models — Karpathy-style Markdown Wiki.

These models define the schema for the Knowledge Graph stored as
structured markdown files with YAML frontmatter and [[wikilinks]].
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Frontmatter models (parsed from YAML frontmatter in .md files)
# ─────────────────────────────────────────────────────────────

class StockNoteFrontmatter(BaseModel):
    """YAML frontmatter for a stock wiki note (stocks/TICKER.md)."""
    ticker: str
    sector: str | None = None
    scan_count: int = 0
    avg_score: float = 0.0
    last_scanned: date | None = None
    last_score: float | None = None
    shortlisted_count: int = 0
    trade_count: int = 0
    win_rate: float | None = None
    tags: list[str] = Field(default_factory=list)


class SectorNoteFrontmatter(BaseModel):
    """YAML frontmatter for a sector wiki note (sectors/SECTOR.md)."""
    sector: str
    stock_count: int = 0
    avg_score: float = 0.0
    last_updated: date | None = None
    regime_tendency: str | None = None
    tags: list[str] = Field(default_factory=list)


class ThemeNoteFrontmatter(BaseModel):
    """YAML frontmatter for a theme wiki note (themes/THEME.md)."""
    theme: str
    frequency: int = 0
    last_seen: date | None = None
    related_stocks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TradeJournalFrontmatter(BaseModel):
    """YAML frontmatter for a trade journal entry (trade_journal/T001.md)."""
    trade_id: str
    ticker: str
    entry_date: date | None = None
    exit_date: date | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    pnl_pct: float | None = None
    setup_type: str | None = None
    exit_reason: str | None = None
    outcome: str | None = None  # "win" or "loss"
    tags: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# Scan history row — stored in the markdown table
# ─────────────────────────────────────────────────────────────

class ScanHistoryEntry(BaseModel):
    """A single row in a stock note's scan history table."""
    date: date
    score: float
    setup_type: str
    shortlisted: bool = False


# ─────────────────────────────────────────────────────────────
# Graph data models (for _graph.json and dashboard rendering)
# ─────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    """A node in the knowledge graph."""
    id: str
    label: str
    type: str  # "stock", "sector", "theme", "trade"
    size: float = 1.0
    color: str | None = None
    metadata: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""
    source: str
    target: str
    relationship: str  # "belongs_to", "correlated_with", "traded", "tagged"
    weight: float = 1.0


class KnowledgeGraph(BaseModel):
    """Full serializable graph for _graph.json."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    last_updated: datetime | None = None


# ─────────────────────────────────────────────────────────────
# Index model (for _index.json fast lookups)
# ─────────────────────────────────────────────────────────────

class StockIndexEntry(BaseModel):
    """Fast lookup entry for a stock ticker."""
    ticker: str
    note_path: str
    scan_count: int = 0
    avg_score: float = 0.0
    last_scanned: date | None = None
    sector: str | None = None


class KnowledgeIndex(BaseModel):
    """The _index.json that maps tickers to scan history for fast lookups."""
    stocks: dict[str, StockIndexEntry] = Field(default_factory=dict)
    last_updated: datetime | None = None


# ─────────────────────────────────────────────────────────────
# Stock context (returned to ScorerAgent for inline reads)
# ─────────────────────────────────────────────────────────────

class StockContext(BaseModel):
    """Context about a stock returned from the Knowledge Graph for scoring."""
    ticker: str
    scan_history: list[ScanHistoryEntry] = Field(default_factory=list)
    avg_score: float = 0.0
    trade_history_summary: str | None = None
    sector_context: str | None = None
    connections: list[str] = Field(default_factory=list)
    has_history: bool = False
