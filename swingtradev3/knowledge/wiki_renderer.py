"""
Wiki Renderer — Reads and writes Karpathy-style Markdown notes.

Handles:
- Parsing YAML frontmatter from .md files
- Building scan history tables
- Resolving [[wikilinks]]
- Updating _index.json and _graph.json
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import frontmatter

from paths import KNOWLEDGE_DIR
from storage import read_json, write_json
from knowledge.knowledge_models import (
    StockNoteFrontmatter,
    ScanHistoryEntry,
    StockContext,
    GraphNode,
    GraphEdge,
    KnowledgeGraph,
    KnowledgeIndex,
    StockIndexEntry,
    SectorNoteFrontmatter,
    TradeJournalFrontmatter,
)


WIKI_DIR = KNOWLEDGE_DIR / "wiki"
INDEX_PATH = KNOWLEDGE_DIR / "_index.json"
GRAPH_PATH = KNOWLEDGE_DIR / "_graph.json"


# ─────────────────────────────────────────────────────────────
# Core Read/Write Operations
# ─────────────────────────────────────────────────────────────

def read_note(path: Path) -> tuple[dict, str]:
    """Read a markdown note, return (frontmatter_dict, body)."""
    if not path.exists():
        return {}, ""
    post = frontmatter.load(str(path))
    return dict(post.metadata), post.content


def write_note(path: Path, metadata: dict, body: str) -> None:
    """Write a markdown note with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    post = frontmatter.Post(body, **metadata)
    with path.open("w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))


# ─────────────────────────────────────────────────────────────
# Stock Note Operations
# ─────────────────────────────────────────────────────────────

def get_stock_note_path(ticker: str) -> Path:
    """Get the path to a stock's wiki note."""
    return WIKI_DIR / "stocks" / f"{ticker}.md"


def load_stock_frontmatter(ticker: str) -> StockNoteFrontmatter | None:
    """Load a stock note's frontmatter, returns None if note doesn't exist."""
    path = get_stock_note_path(ticker)
    if not path.exists():
        return None
    meta, _ = read_note(path)
    return StockNoteFrontmatter(**meta) if meta else None


def parse_scan_history(body: str) -> list[ScanHistoryEntry]:
    """Extract scan history table rows from a stock note's body."""
    entries = []
    in_table = False
    for line in body.split("\n"):
        line = line.strip()
        if "| Date" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 4:
                try:
                    entries.append(ScanHistoryEntry(
                        date=date.fromisoformat(cols[0]),
                        score=float(cols[1]),
                        setup_type=cols[2],
                        shortlisted=cols[3] in ("✅", "True", "true", "Yes"),
                    ))
                except (ValueError, IndexError):
                    continue
        elif in_table and not line.startswith("|"):
            in_table = False
    return entries


def build_scan_history_table(entries: list[ScanHistoryEntry]) -> str:
    """Build a markdown table from scan history entries."""
    rows = ["| Date       | Score | Setup    | Shortlisted |",
            "|------------|-------|----------|-------------|"]
    for e in sorted(entries, key=lambda x: x.date, reverse=True):
        flag = "✅" if e.shortlisted else "❌"
        rows.append(f"| {e.date.isoformat()} | {e.score:.1f}   | {e.setup_type} | {flag}          |")
    return "\n".join(rows)


def upsert_stock_note(
    ticker: str,
    score: float,
    setup_type: str,
    shortlisted: bool,
    sector: str | None = None,
    connections: list[str] | None = None,
) -> None:
    """
    Create or update a stock's wiki note with a new scan entry.
    This is the primary write operation for the Knowledge Graph.
    """
    path = get_stock_note_path(ticker)
    
    # Load existing or create new
    if path.exists():
        meta, body = read_note(path)
        fm = StockNoteFrontmatter(**meta) if meta else StockNoteFrontmatter(ticker=ticker)
        history = parse_scan_history(body)
    else:
        fm = StockNoteFrontmatter(ticker=ticker, sector=sector)
        history = []
        body = ""

    # Add new scan entry
    today = date.today()
    new_entry = ScanHistoryEntry(
        date=today,
        score=score,
        setup_type=setup_type,
        shortlisted=shortlisted,
    )
    
    # Avoid duplicate entries for same date
    history = [h for h in history if h.date != today]
    history.insert(0, new_entry)

    # Update frontmatter
    fm.scan_count = len(history)
    fm.avg_score = round(sum(h.score for h in history) / len(history), 2) if history else 0.0
    fm.last_scanned = today
    fm.last_score = score
    if shortlisted:
        fm.shortlisted_count = sum(1 for h in history if h.shortlisted)
    if sector:
        fm.sector = sector

    # Build body
    connections = connections or []
    conn_section = ""
    if sector:
        conn_section += f"- Sector: [[{sector}]]\n"
    for conn in connections:
        conn_section += f"- Correlated: [[{conn}]]\n"

    new_body = f"# {ticker}\n\n## Scan History\n{build_scan_history_table(history)}\n\n## Connections\n{conn_section}"

    write_note(path, fm.model_dump(mode="json"), new_body)

    # Update index
    _update_index(ticker, fm)
    
    # Update graph
    _update_graph_for_stock(ticker, fm, connections)


# ─────────────────────────────────────────────────────────────
# Trade Journal Operations
# ─────────────────────────────────────────────────────────────

def upsert_trade_journal(
    trade_id: str,
    ticker: str,
    entry_price: float,
    exit_price: float,
    pnl_pct: float,
    entry_date: date | None = None,
    exit_date: date | None = None,
    setup_type: str | None = None,
    exit_reason: str | None = None,
    what_worked: str = "",
    what_failed: str = "",
    sector: str | None = None,
) -> None:
    """Create or update a trade journal entry and link it to the stock note."""
    path = WIKI_DIR / "trade_journal" / f"{trade_id}.md"
    outcome = "win" if pnl_pct > 0 else "loss"

    fm = TradeJournalFrontmatter(
        trade_id=trade_id,
        ticker=ticker,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=entry_price,
        exit_price=exit_price,
        pnl_pct=round(pnl_pct, 2),
        setup_type=setup_type,
        exit_reason=exit_reason,
        outcome=outcome,
    )

    body = f"# {trade_id}: {ticker}\n\n"
    body += f"## Summary\n"
    body += f"- Entry: ₹{entry_price} ({setup_type or 'N/A'})\n"
    body += f"- Exit: ₹{exit_price} ({exit_reason or 'N/A'})\n"
    body += f"- P&L: {pnl_pct:+.1f}% {'✅' if pnl_pct > 0 else '❌'}\n\n"
    
    if what_worked:
        body += f"## What Worked\n{what_worked}\n\n"
    if what_failed:
        body += f"## What Failed\n{what_failed}\n\n"
    
    body += f"## Connections\n"
    body += f"- Stock: [[{ticker}]]\n"
    if sector:
        body += f"- Sector: [[{sector}]]\n"
    if setup_type:
        body += f"- Setup type: {setup_type}\n"

    write_note(path, fm.model_dump(mode="json"), body)

    # Update the stock note's trade count and link
    stock_path = get_stock_note_path(ticker)
    if stock_path.exists():
        meta, stock_body = read_note(stock_path)
        if meta:
            meta["trade_count"] = meta.get("trade_count", 0) + 1
            # Add trade link to connections if not already there
            trade_link = f"- Trade: [[{trade_id}]]"
            if trade_link not in stock_body:
                stock_body += f"\n{trade_link}\n"
            write_note(stock_path, meta, stock_body)

    # Update graph with trade node
    _update_graph_for_trade(trade_id, ticker, pnl_pct, sector)


# ─────────────────────────────────────────────────────────────
# Sector Note Operations
# ─────────────────────────────────────────────────────────────

def upsert_sector_note(sector: str) -> None:
    """Rebuild a sector note from all stock notes in that sector."""
    path = WIKI_DIR / "sectors" / f"{sector}.md"
    
    # Find all stocks in this sector from the index
    index = _load_index()
    sector_stocks = [
        entry for entry in index.stocks.values()
        if entry.sector == sector
    ]

    fm = SectorNoteFrontmatter(
        sector=sector,
        stock_count=len(sector_stocks),
        avg_score=round(
            sum(s.avg_score for s in sector_stocks) / len(sector_stocks), 2
        ) if sector_stocks else 0.0,
        last_updated=date.today(),
    )

    body = f"# {sector}\n\n"
    body += f"## Stocks ({len(sector_stocks)})\n"
    for s in sorted(sector_stocks, key=lambda x: x.avg_score, reverse=True):
        body += f"- [[{s.ticker}]] — Avg Score: {s.avg_score:.1f}, Scans: {s.scan_count}\n"

    write_note(path, fm.model_dump(mode="json"), body)


# ─────────────────────────────────────────────────────────────
# Context retrieval (for ScorerAgent inline reads)
# ─────────────────────────────────────────────────────────────

def get_stock_context(ticker: str) -> StockContext:
    """
    Get historical context for a stock from the Knowledge Graph.
    Called by the ScorerAgent before scoring to provide comparative context.
    """
    path = get_stock_note_path(ticker)
    if not path.exists():
        return StockContext(ticker=ticker, has_history=False)

    meta, body = read_note(path)
    fm = StockNoteFrontmatter(**meta) if meta else StockNoteFrontmatter(ticker=ticker)
    history = parse_scan_history(body)

    # Extract connections
    connections = []
    for line in body.split("\n"):
        links = re.findall(r'\[\[([^\]]+)\]\]', line)
        connections.extend(links)

    # Build trade history summary
    trade_summary = None
    if fm.trade_count and fm.trade_count > 0:
        trade_summary = f"Traded {fm.trade_count}x"
        if fm.win_rate is not None:
            trade_summary += f", win rate: {fm.win_rate:.0%}"

    # Sector context
    sector_ctx = None
    if fm.sector:
        sector_path = WIKI_DIR / "sectors" / f"{fm.sector}.md"
        if sector_path.exists():
            _, sector_body = read_note(sector_path)
            sector_ctx = sector_body[:500] if sector_body else None

    return StockContext(
        ticker=ticker,
        scan_history=history[:10],  # Last 10 scans
        avg_score=fm.avg_score,
        trade_history_summary=trade_summary,
        sector_context=sector_ctx,
        connections=list(set(connections)),
        has_history=len(history) > 0,
    )


def format_context_for_llm(ctx: StockContext) -> str:
    """Format a StockContext into a human-readable string for LLM prompts."""
    if not ctx.has_history:
        return f"No previous research history for {ctx.ticker}."

    parts = [f"HISTORICAL CONTEXT for {ctx.ticker}:"]
    parts.append(f"- Average score: {ctx.avg_score:.1f} across {len(ctx.scan_history)} scans")

    if ctx.scan_history:
        latest = ctx.scan_history[0]
        parts.append(f"- Last scan: {latest.date} — Score {latest.score:.1f} ({latest.setup_type}, {'shortlisted' if latest.shortlisted else 'not shortlisted'})")
        if len(ctx.scan_history) > 1:
            prev = ctx.scan_history[1]
            parts.append(f"- Previous scan: {prev.date} — Score {prev.score:.1f} ({prev.setup_type})")

    if ctx.trade_history_summary:
        parts.append(f"- {ctx.trade_history_summary}")

    if ctx.sector_context:
        parts.append(f"- Sector info: {ctx.sector_context[:200]}")

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────
# Internal: Index management
# ─────────────────────────────────────────────────────────────

def _load_index() -> KnowledgeIndex:
    """Load the knowledge index."""
    data = read_json(INDEX_PATH, None)
    if data is None:
        return KnowledgeIndex()
    return KnowledgeIndex.model_validate(data)


def _save_index(index: KnowledgeIndex) -> None:
    """Save the knowledge index."""
    index.last_updated = datetime.now()
    write_json(INDEX_PATH, index.model_dump(mode="json"))


def _update_index(ticker: str, fm: StockNoteFrontmatter) -> None:
    """Update the index entry for a stock."""
    index = _load_index()
    index.stocks[ticker] = StockIndexEntry(
        ticker=ticker,
        note_path=f"wiki/stocks/{ticker}.md",
        scan_count=fm.scan_count,
        avg_score=fm.avg_score,
        last_scanned=fm.last_scanned,
        sector=fm.sector,
    )
    _save_index(index)


# ─────────────────────────────────────────────────────────────
# Internal: Graph management
# ─────────────────────────────────────────────────────────────

def _load_graph() -> KnowledgeGraph:
    """Load the knowledge graph."""
    data = read_json(GRAPH_PATH, None)
    if data is None:
        return KnowledgeGraph()
    return KnowledgeGraph.model_validate(data)


def _save_graph(graph: KnowledgeGraph) -> None:
    """Save the knowledge graph."""
    graph.last_updated = datetime.now()
    write_json(GRAPH_PATH, graph.model_dump(mode="json"))


def _score_to_color(score: float) -> str:
    """Map a score to a color: green (high), yellow (mid), red (low)."""
    if score >= 8.0:
        return "#22c55e"  # green
    elif score >= 6.5:
        return "#eab308"  # yellow
    else:
        return "#ef4444"  # red


def _update_graph_for_stock(
    ticker: str,
    fm: StockNoteFrontmatter,
    connections: list[str] | None = None,
) -> None:
    """Update graph nodes/edges for a stock."""
    graph = _load_graph()

    # Upsert stock node
    node_id = f"stock:{ticker}"
    existing = next((n for n in graph.nodes if n.id == node_id), None)
    new_node = GraphNode(
        id=node_id,
        label=ticker,
        type="stock",
        size=max(1.0, fm.scan_count * 0.5),
        color=_score_to_color(fm.avg_score),
        metadata={"avg_score": fm.avg_score, "scan_count": fm.scan_count},
    )
    if existing:
        graph.nodes = [n for n in graph.nodes if n.id != node_id]
    graph.nodes.append(new_node)

    # Upsert sector node + edge
    if fm.sector:
        sector_id = f"sector:{fm.sector}"
        if not any(n.id == sector_id for n in graph.nodes):
            graph.nodes.append(GraphNode(
                id=sector_id,
                label=fm.sector,
                type="sector",
                size=2.0,
                color="#3b82f6",
            ))
        edge_key = (node_id, sector_id)
        if not any((e.source, e.target) == edge_key for e in graph.edges):
            graph.edges.append(GraphEdge(
                source=node_id,
                target=sector_id,
                relationship="belongs_to",
            ))

    # Correlation edges
    for conn in (connections or []):
        conn_id = f"stock:{conn}"
        edge_key = tuple(sorted([node_id, conn_id]))
        if not any(tuple(sorted([e.source, e.target])) == edge_key for e in graph.edges):
            graph.edges.append(GraphEdge(
                source=edge_key[0],
                target=edge_key[1],
                relationship="correlated_with",
            ))

    _save_graph(graph)


def _update_graph_for_trade(
    trade_id: str,
    ticker: str,
    pnl_pct: float,
    sector: str | None = None,
) -> None:
    """Add a trade node to the graph."""
    graph = _load_graph()

    trade_node_id = f"trade:{trade_id}"
    color = "#22c55e" if pnl_pct > 0 else "#ef4444"
    
    graph.nodes.append(GraphNode(
        id=trade_node_id,
        label=trade_id,
        type="trade",
        size=1.0,
        color=color,
        metadata={"pnl_pct": pnl_pct},
    ))

    # Link trade to stock
    stock_id = f"stock:{ticker}"
    graph.edges.append(GraphEdge(
        source=stock_id,
        target=trade_node_id,
        relationship="traded",
    ))

    _save_graph(graph)
