"""
Tests for the Knowledge Graph: wiki_renderer and knowledge_models.
"""
from __future__ import annotations

import json
import shutil
from datetime import date, datetime
from pathlib import Path

import pytest

from knowledge.knowledge_models import (
    StockNoteFrontmatter,
    ScanHistoryEntry,
    StockContext,
    GraphNode,
    GraphEdge,
    KnowledgeGraph,
    KnowledgeIndex,
    StockIndexEntry,
)
from knowledge.wiki_renderer import (
    read_note,
    write_note,
    get_stock_note_path,
    load_stock_frontmatter,
    parse_scan_history,
    build_scan_history_table,
    upsert_stock_note,
    upsert_trade_journal,
    get_stock_context,
    format_context_for_llm,
    WIKI_DIR,
    INDEX_PATH,
    GRAPH_PATH,
)


@pytest.fixture(autouse=True)
def clean_knowledge_dir():
    """Ensure a clean knowledge directory for each test."""
    # Setup: ensure dirs exist
    for d in [
        WIKI_DIR / "stocks",
        WIKI_DIR / "sectors",
        WIKI_DIR / "themes",
        WIKI_DIR / "trade_journal",
    ]:
        d.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Teardown: clean up test data
    for f in (WIKI_DIR / "stocks").glob("TEST_*.md"):
        f.unlink()
    for f in (WIKI_DIR / "sectors").glob("TestSector*.md"):
        f.unlink()
    for f in (WIKI_DIR / "trade_journal").glob("TEST_*.md"):
        f.unlink()
    # Clean index/graph entries (reload, filter, save)
    if INDEX_PATH.exists():
        INDEX_PATH.unlink()
    if GRAPH_PATH.exists():
        GRAPH_PATH.unlink()


# ─────────────────────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────────────────────

class TestKnowledgeModels:
    def test_stock_frontmatter_defaults(self):
        fm = StockNoteFrontmatter(ticker="TEST_RELIANCE")
        assert fm.ticker == "TEST_RELIANCE"
        assert fm.scan_count == 0
        assert fm.avg_score == 0.0
        assert fm.sector is None

    def test_scan_history_entry(self):
        entry = ScanHistoryEntry(
            date=date(2026, 4, 12),
            score=8.2,
            setup_type="breakout",
            shortlisted=True,
        )
        assert entry.score == 8.2
        assert entry.shortlisted is True

    def test_graph_node(self):
        node = GraphNode(
            id="stock:TEST_RELIANCE",
            label="TEST_RELIANCE",
            type="stock",
            size=2.0,
            color="#22c55e",
        )
        assert node.type == "stock"

    def test_stock_context_no_history(self):
        ctx = StockContext(ticker="TEST_UNKNOWN")
        assert ctx.has_history is False
        assert ctx.scan_history == []


# ─────────────────────────────────────────────────────────────
# Wiki Renderer Tests
# ─────────────────────────────────────────────────────────────

class TestWikiRenderer:
    def test_write_and_read_note(self):
        path = WIKI_DIR / "stocks" / "TEST_WRITE.md"
        meta = {"ticker": "TEST_WRITE", "score": 7.5}
        body = "# TEST_WRITE\n\nA test note."
        
        write_note(path, meta, body)
        assert path.exists()
        
        loaded_meta, loaded_body = read_note(path)
        assert loaded_meta["ticker"] == "TEST_WRITE"
        assert "A test note" in loaded_body
        
        # Cleanup
        path.unlink()

    def test_parse_scan_history(self):
        body = """# TEST_PARSE

## Scan History
| Date       | Score | Setup    | Shortlisted |
|------------|-------|----------|-------------|
| 2026-04-14 | 6.0   | Pullback | ❌          |
| 2026-04-13 | 8.2   | Breakout | ✅          |

## Connections
- Sector: [[Energy]]
"""
        entries = parse_scan_history(body)
        assert len(entries) == 2
        assert entries[0].score == 6.0
        assert entries[1].shortlisted is True

    def test_build_scan_history_table(self):
        entries = [
            ScanHistoryEntry(date=date(2026, 4, 12), score=7.5, setup_type="Pullback", shortlisted=True),
            ScanHistoryEntry(date=date(2026, 4, 13), score=8.2, setup_type="Breakout", shortlisted=True),
        ]
        table = build_scan_history_table(entries)
        assert "| 2026-04-13 |" in table
        assert "| 2026-04-12 |" in table
        assert "✅" in table

    def test_upsert_stock_note_creates_new(self):
        upsert_stock_note(
            ticker="TEST_NEW",
            score=7.5,
            setup_type="pullback",
            shortlisted=True,
            sector="TestSector",
        )
        
        path = get_stock_note_path("TEST_NEW")
        assert path.exists()
        
        fm = load_stock_frontmatter("TEST_NEW")
        assert fm is not None
        assert fm.ticker == "TEST_NEW"
        assert fm.scan_count == 1
        assert fm.avg_score == 7.5
        assert fm.sector == "TestSector"
        
        # Cleanup
        path.unlink()

    def test_upsert_stock_note_updates_existing(self):
        # First scan
        upsert_stock_note(
            ticker="TEST_UPDATE",
            score=7.0,
            setup_type="pullback",
            shortlisted=False,
            sector="TestSector",
        )
        
        # Second scan (same day — should replace)
        upsert_stock_note(
            ticker="TEST_UPDATE",
            score=8.5,
            setup_type="breakout",
            shortlisted=True,
            sector="TestSector",
        )
        
        fm = load_stock_frontmatter("TEST_UPDATE")
        assert fm is not None
        assert fm.scan_count == 1  # Same day = 1 entry
        assert fm.avg_score == 8.5
        assert fm.last_score == 8.5
        
        # Cleanup
        get_stock_note_path("TEST_UPDATE").unlink()

    def test_get_stock_context_no_history(self):
        ctx = get_stock_context("TEST_NONEXISTENT")
        assert ctx.has_history is False
        assert ctx.ticker == "TEST_NONEXISTENT"

    def test_get_stock_context_with_history(self):
        upsert_stock_note(
            ticker="TEST_CONTEXT",
            score=8.0,
            setup_type="breakout",
            shortlisted=True,
            sector="TestSector",
        )
        
        ctx = get_stock_context("TEST_CONTEXT")
        assert ctx.has_history is True
        assert len(ctx.scan_history) == 1
        assert ctx.scan_history[0].score == 8.0
        assert ctx.avg_score == 8.0
        
        # Cleanup
        get_stock_note_path("TEST_CONTEXT").unlink()

    def test_format_context_for_llm_no_history(self):
        ctx = StockContext(ticker="TEST_NONE")
        text = format_context_for_llm(ctx)
        assert "No previous research history" in text

    def test_format_context_for_llm_with_history(self):
        ctx = StockContext(
            ticker="TEST_FMT",
            scan_history=[
                ScanHistoryEntry(date=date(2026, 4, 13), score=8.2, setup_type="breakout", shortlisted=True),
                ScanHistoryEntry(date=date(2026, 4, 12), score=7.5, setup_type="pullback", shortlisted=True),
            ],
            avg_score=7.85,
            has_history=True,
        )
        text = format_context_for_llm(ctx)
        assert "HISTORICAL CONTEXT" in text
        assert "8.2" in text
        assert "7.5" in text

    def test_index_updated_on_upsert(self):
        upsert_stock_note(
            ticker="TEST_IDX",
            score=7.0,
            setup_type="pullback",
            shortlisted=False,
        )
        
        # Verify index file exists and has the entry
        assert INDEX_PATH.exists()
        with INDEX_PATH.open() as f:
            index_data = json.load(f)
        assert "TEST_IDX" in index_data.get("stocks", {})
        
        # Cleanup
        get_stock_note_path("TEST_IDX").unlink()

    def test_graph_updated_on_upsert(self):
        upsert_stock_note(
            ticker="TEST_GRP",
            score=8.0,
            setup_type="breakout",
            shortlisted=True,
            sector="TestSector",
        )
        
        assert GRAPH_PATH.exists()
        with GRAPH_PATH.open() as f:
            graph_data = json.load(f)
        
        node_ids = [n["id"] for n in graph_data.get("nodes", [])]
        assert "stock:TEST_GRP" in node_ids
        assert "sector:TestSector" in node_ids
        
        # Cleanup
        get_stock_note_path("TEST_GRP").unlink()


class TestTradeJournal:
    def test_create_trade_journal(self):
        # First create the stock note
        upsert_stock_note(
            ticker="TEST_TJ",
            score=8.0,
            setup_type="breakout",
            shortlisted=True,
            sector="TestSector",
        )
        
        upsert_trade_journal(
            trade_id="TEST_T001",
            ticker="TEST_TJ",
            entry_price=1000.0,
            exit_price=1100.0,
            pnl_pct=10.0,
            setup_type="breakout",
            exit_reason="target_hit",
            sector="TestSector",
        )
        
        path = WIKI_DIR / "trade_journal" / "TEST_T001.md"
        assert path.exists()
        
        meta, body = read_note(path)
        assert meta["trade_id"] == "TEST_T001"
        assert meta["outcome"] == "win"
        assert "₹1000" in body
        assert "[[TEST_TJ]]" in body
        
        # Cleanup
        path.unlink()
        get_stock_note_path("TEST_TJ").unlink()
