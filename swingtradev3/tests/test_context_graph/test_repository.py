"""Integration tests for ContextGraphRepository — all write methods.

Every test wipes Memgraph before and after (via ``_clean_between`` fixture).
Each test is self-contained: create data → assert → cleanup.
"""

from __future__ import annotations

from typing import Any

import pytest

from context_graph.repository import ContextGraphRepository

pytestmark = pytest.mark.memgraph_destructive

# ── helpers ──────────────────────────────────────────────────────────────


def _count(graph: ContextGraphRepository, label: str) -> int:
    with graph._driver.session() as s:
        return s.run(f"MATCH (n:`{label}`) RETURN count(n)").single()[0]


def _edge(graph: ContextGraphRepository, edge_type: str) -> int:
    with graph._driver.session() as s:
        return s.run(f"MATCH ()-[r:`{edge_type}`]->() RETURN count(r)").single()[0]


def _get(graph: ContextGraphRepository, label: str, node_id: str) -> dict[str, Any] | None:
    with graph._driver.session() as s:
        row = s.run(f"MATCH (n:`{label}` {{id: $id}}) RETURN n", id=node_id).single()
        return dict(row["n"]) if row else None


def _find(graph: ContextGraphRepository, label: str, **props: Any) -> list[dict[str, Any]]:
    clauses = " AND ".join(f"n.{k} = ${k}" for k in props)
    with graph._driver.session() as s:
        rows = s.run(f"MATCH (n:`{label}` WHERE {clauses}) RETURN n", **props)
        return [dict(r["n"]) for r in rows]


def _edge_between(
    graph: ContextGraphRepository, edge_type: str, from_id: str, to_id: str
) -> bool:
    with graph._driver.session() as s:
        return s.run(
            f"MATCH (a {{id: $fid}})-[r:`{edge_type}`]->(b {{id: $tid}}) RETURN r",
            fid=from_id, tid=to_id,
        ).single() is not None


# ── standard property shape checks ───────────────────────────────────────


def _assert_meta_shape(props: dict[str, Any]) -> None:
    """Verify every node carries the standard ``_meta`` keys."""
    for key in ("source", "source_id", "observed_at", "ingested_at", "payload_hash",
                "payload_json", "confidence", "projection_version"):
        assert key in props, f"missing _meta key: {key}"
    assert props["projection_version"] == "phase11.v1"


# ═══════════════════════════════════════════════════════════════════════════
# 1.  Stock + Sector
# ═══════════════════════════════════════════════════════════════════════════


class TestStockSector:
    def test_upsert_stock_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        node = _get(graph, "Stock", "stock:RELIANCE")
        assert node is not None
        assert node["ticker"] == "RELIANCE"
        assert node["id"] == "stock:RELIANCE"
        _assert_meta_shape(node)

    def test_upsert_stock_with_sector_creates_sector_and_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("TCS", sector="technology", source="test")
        assert _count(graph, "Stock") == 1
        assert _count(graph, "Sector") == 1
        assert _edge(graph, "BELONGS_TO_SECTOR") == 1
        assert _edge_between(graph, "BELONGS_TO_SECTOR", "stock:TCS", "sector:technology")

    def test_upsert_stock_idempotent(self, graph: ContextGraphRepository) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.upsert_stock("RELIANCE", source="test_2nd")
        assert _count(graph, "Stock") == 1

    def test_upsert_sector_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.upsert_sector("finance", source="test")
        node = _get(graph, "Sector", "sector:finance")
        assert node is not None
        assert node["name"] == "finance"

    def test_upsert_sector_idempotent(self, graph: ContextGraphRepository) -> None:
        graph.upsert_sector("finance", source="test")
        graph.upsert_sector("finance", source="test_2nd")
        assert _count(graph, "Sector") == 1

    def test_upsert_stock_empty_ticker_skips(self, graph: ContextGraphRepository) -> None:
        graph.upsert_stock("", source="test")
        assert _count(graph, "Stock") == 0


# ═══════════════════════════════════════════════════════════════════════════
# 2.  Index
# ═══════════════════════════════════════════════════════════════════════════


class TestIndex:
    def test_upsert_index_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.upsert_index("NIFTY 50", source="test")
        node = _get(graph, "Index", "index:NIFTY 50")
        assert node is not None
        assert node["name"] == "NIFTY 50"
        assert node["index_type"] == "index"

    def test_upsert_index_custom_type(self, graph: ContextGraphRepository) -> None:
        graph.upsert_index("BANK NIFTY", index_type="sectoral", source="test")
        node = _get(graph, "Index", "index:BANK NIFTY")
        assert node["index_type"] == "sectoral"

    def test_upsert_index_idempotent(self, graph: ContextGraphRepository) -> None:
        graph.upsert_index("NIFTY 50", source="test")
        graph.upsert_index("NIFTY 50", source="test_2nd")
        assert _count(graph, "Index") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 3.  Research Run → RegimeSnapshot → ResearchCandidate
# ═══════════════════════════════════════════════════════════════════════════


class TestResearchFlow:
    def test_upsert_research_run_creates_run_regime_and_candidates(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_research_run(
            run_id="run_001",
            scan_date="2026-05-12",
            analyzed_at="2026-05-12T09:00:00+05:30",
            regime={"name": "bullish", "volatility": "low"},
            diagnostics={"model_version": "v2"},
            qualified_count=2,
            total_screened=500,
            shortlist=[{"ticker": "RELIANCE", "score": 8.5, "sector": "energy"}],
            scan_results=[{"ticker": "TCS", "score": 6.0, "sector": "technology"}],
            source="test",
        )
        assert _count(graph, "ResearchRun") == 1
        assert _count(graph, "RegimeSnapshot") >= 1
        assert _count(graph, "ResearchCandidate") >= 1
        assert _edge(graph, "CANDIDATE_FOR") >= 1
        assert _edge(graph, "ANALYZED_IN") >= 1
        assert _edge(graph, "UNDER_REGIME") >= 1

        # Verify ResearchRun has correct properties
        run = _get(graph, "ResearchRun", "run_001")
        assert run is not None
        assert run["scan_date"] == "2026-05-12"
        assert run["qualified_count"] == 2
        assert run["total_screened"] == 500

    def test_upsert_research_run_idempotent(self, graph: ContextGraphRepository) -> None:
        kwargs = dict(
            run_id="run_001", scan_date="2026-05-12",
            analyzed_at="2026-05-12T09:00:00+05:30",
            regime={"name": "bullish"}, diagnostics={},
            qualified_count=1, total_screened=100,
            shortlist=[], scan_results=[], source="test",
        )
        graph.upsert_research_run(**kwargs)
        graph.upsert_research_run(**kwargs)
        assert _count(graph, "ResearchRun") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 4.  NewsArticle + AFFECTS_STOCK
# ═══════════════════════════════════════════════════════════════════════════


class TestNews:
    def test_upsert_news_item_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.upsert_news_item(
            {"news_id": "n1", "title": "Test News", "tickers": []},
            source="test",
        )
        assert _count(graph, "NewsArticle") == 1
        node = _get(graph, "NewsArticle", "news:n1")
        assert node is not None
        assert node["title"] == "Test News"
        _assert_meta_shape(node)

    def test_upsert_news_item_with_tickers_creates_edges(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.upsert_news_item(
            {"news_id": "n2", "title": "Reliance News", "tickers": ["RELIANCE"]},
            source="test",
        )
        assert _edge(graph, "AFFECTS_STOCK") == 1
        assert _edge_between(graph, "AFFECTS_STOCK", "news:n2", "stock:RELIANCE")

    def test_upsert_news_item_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_news_item(
            {"news_id": "n3", "title": "TCS News", "tickers": ["TCS"]},
            source="test",
        )
        assert _count(graph, "Stock") == 1
        assert _get(graph, "Stock", "stock:TCS") is not None

    def test_upsert_news_items_batch(self, graph: ContextGraphRepository) -> None:
        items = [
            {"news_id": "a", "title": "A", "tickers": []},
            {"news_id": "b", "title": "B", "tickers": []},
        ]
        graph.upsert_news_items(items, source="test")
        assert _count(graph, "NewsArticle") == 2

    def test_upsert_news_item_idempotent(self, graph: ContextGraphRepository) -> None:
        item = {"news_id": "n1", "title": "Same", "tickers": []}
        graph.upsert_news_item(item, source="test")
        graph.upsert_news_item(item, source="test_2nd")
        assert _count(graph, "NewsArticle") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 5.  SignalSnapshot + HAS_SIGNAL
# ═══════════════════════════════════════════════════════════════════════════


class TestSignalSnapshot:
    def test_upsert_signal_snapshot_creates_node_and_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.upsert_signal_snapshot(
            ticker="RELIANCE",
            signal_type="momentum",
            payload={"score": 0.85},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "SignalSnapshot") == 1
        assert _edge(graph, "HAS_SIGNAL") == 1

    def test_upsert_signal_snapshot_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_signal_snapshot(
            ticker="INFY",
            signal_type="volume",
            payload={"score": 0.7},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "Stock") == 1
        # node id is hash-based, just verify count
        assert _count(graph, "SignalSnapshot") == 1

    def test_upsert_signal_snapshot_idempotent(self, graph: ContextGraphRepository) -> None:
        graph.upsert_signal_snapshot(
            ticker="RELIANCE", signal_type="momentum",
            payload={"signal_id": "s1", "score": 0.85},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        graph.upsert_signal_snapshot(
            ticker="RELIANCE", signal_type="momentum",
            payload={"signal_id": "s1", "score": 0.90},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test_2nd",
        )
        assert _count(graph, "SignalSnapshot") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 6.  TechnicalSnapshot + FundamentalSnapshot
# ═══════════════════════════════════════════════════════════════════════════


class TestTechnicalFundamental:
    def test_upsert_technical_snapshot_creates_node(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_technical_snapshot(
            ticker="RELIANCE",
            payload={"rsi": 62, "macd": "bullish"},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "TechnicalSnapshot") == 1

    def test_upsert_technical_snapshot_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_technical_snapshot(
            ticker="TCS",
            payload={"tech_id": "t1", "rsi": 55},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "Stock") == 1
        # No edge to Stock — current implementation
        assert _count(graph, "TechnicalSnapshot") == 1

    def test_upsert_fundamental_snapshot_creates_node(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_fundamental_snapshot(
            ticker="HDFC",
            payload={"pe": 25, "roe": 18},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "FundamentalSnapshot") == 1

    def test_upsert_fundamental_snapshot_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_fundamental_snapshot(
            ticker="HDFC",
            payload={"fund_id": "f1", "pe": 25},
            observed_at="2026-05-12T10:00:00+05:30",
            source="test",
        )
        assert _count(graph, "Stock") == 1

    def test_upsert_technical_idempotent(self, graph: ContextGraphRepository) -> None:
        payload = {"tech_id": "t1", "rsi": 55}
        graph.upsert_technical_snapshot(
            ticker="TCS", payload=payload,
            observed_at="2026-05-12T10:00:00+05:30", source="test",
        )
        graph.upsert_technical_snapshot(
            ticker="TCS", payload=payload,
            observed_at="2026-05-12T10:00:00+05:30", source="test",
        )
        assert _count(graph, "TechnicalSnapshot") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 7.  TradeMemory + ABOUT_STOCK + SIMILAR_TO
# ═══════════════════════════════════════════════════════════════════════════


class TestTradeMemory:
    def test_upsert_trade_memory_creates_node_and_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.upsert_trade_memory(
            trade_id="t1", ticker="RELIANCE",
            payload={}, entry_price=2500, exit_price=2600,
            pnl_pct=4.0, setup_type="breakout",
            source="test",
        )
        assert _count(graph, "TradeMemory") == 1
        assert _edge(graph, "ABOUT_STOCK") == 1
        assert _edge_between(graph, "ABOUT_STOCK", "trade_memory:t1", "stock:RELIANCE")

    def test_upsert_trade_memory_with_similar_trades(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_trade_memory(
            trade_id="t1", ticker="RELIANCE", payload={},
            entry_price=2500, exit_price=2600, pnl_pct=4.0,
            source="test",
        )
        graph.upsert_trade_memory(
            trade_id="t2", ticker="TCS", payload={},
            entry_price=3500, exit_price=3600, pnl_pct=2.8,
            similar_trade_ids=["t1"],
            source="test",
        )
        # No auto stock upsert for similar trades; SIMILAR_TO edge
        assert _edge(graph, "SIMILAR_TO") == 1
        assert _edge_between(
            graph, "SIMILAR_TO", "trade_memory:t2", "trade_memory:t1"
        )

    def test_upsert_trade_memory_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_trade_memory(
            trade_id="t3", ticker="INFY", payload={},
            entry_price=1500, exit_price=1600, pnl_pct=6.0,
            source="test",
        )
        assert _count(graph, "Stock") == 1

    def test_upsert_trade_memory_idempotent(self, graph: ContextGraphRepository) -> None:
        kwargs = dict(trade_id="t1", ticker="RELIANCE", payload={},
                      entry_price=2500, exit_price=2600, pnl_pct=4.0, source="test")
        graph.upsert_trade_memory(**kwargs)
        graph.upsert_trade_memory(**kwargs)
        assert _count(graph, "TradeMemory") == 1

    def test_similar_to_skips_self_reference(self, graph: ContextGraphRepository) -> None:
        graph.upsert_trade_memory(
            trade_id="t1", ticker="RELIANCE", payload={},
            entry_price=2500, exit_price=2600, pnl_pct=4.0,
            similar_trade_ids=["t1"],
            source="test",
        )
        assert _edge(graph, "SIMILAR_TO") == 0


# ═══════════════════════════════════════════════════════════════════════════
# 8.  Observation + MENTIONS
# ═══════════════════════════════════════════════════════════════════════════


class TestObservation:
    def test_record_observation_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.record_observation(
            observation_type="technical_note",
            ticker=None,
            payload={"note": "observed pattern"},
            source="test",
        )
        assert _count(graph, "Observation") == 1

    def test_record_observation_with_ticker_creates_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.record_observation(
            observation_type="price_action",
            ticker="RELIANCE",
            payload={"observation_id": "obs1", "note": "double top"},
            source="test",
        )
        assert _edge(graph, "MENTIONS") == 1

    def test_record_observation_auto_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_observation(
            observation_type="news_impact",
            ticker="TCS",
            payload={"observation_id": "obs2", "note": "positive catalyst"},
            source="test",
        )
        assert _count(graph, "Stock") == 1

    def test_record_observation_idempotent(self, graph: ContextGraphRepository) -> None:
        payload = {"observation_id": "obs1", "note": "same note"}
        graph.record_observation(
            observation_type="note", ticker=None,
            payload=payload, source="test",
        )
        graph.record_observation(
            observation_type="note", ticker=None,
            payload=payload, source="test_2nd",
        )
        assert _count(graph, "Observation") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 9.  Lesson + SUPPORTS_LESSON
# ═══════════════════════════════════════════════════════════════════════════


class TestLesson:
    def test_upsert_lesson_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.upsert_lesson(
            lesson_id="l1",
            lesson_text="Always check volume before entry.",
            category="risk",
            source="test",
        )
        assert _count(graph, "Lesson") == 1
        node = _get(graph, "Lesson", "lesson:l1")
        assert node is not None
        assert "volume" in node["lesson_text"]

    def test_upsert_lesson_with_observation_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_observation(
            observation_type="note", ticker=None,
            payload={"observation_id": "obs1", "note": "saw volume spike"},
            source="test",
        )
        graph.upsert_lesson(
            lesson_id="l2",
            lesson_text="Volume confirms breakout.",
            category="technical",
            observation_ids=["obs1"],
            source="test",
        )
        assert _edge(graph, "SUPPORTS_LESSON") == 1
        assert _edge_between(
            graph, "SUPPORTS_LESSON", "lesson:l2", "observation:obs1"
        )

    def test_upsert_lesson_with_ticker_creates_stock(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_lesson(
            lesson_id="l3",
            lesson_text="RELIANCE tends to gap up on results.",
            category="empirical",
            ticker="RELIANCE",
            source="test",
        )
        assert _count(graph, "Stock") == 1

    def test_upsert_lesson_idempotent(self, graph: ContextGraphRepository) -> None:
        kwargs = dict(
            lesson_id="l1", lesson_text="Same lesson",
            category="general", source="test",
        )
        graph.upsert_lesson(**kwargs)
        graph.upsert_lesson(**kwargs)
        assert _count(graph, "Lesson") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 10.  ExecutionEvent + MENTIONS + PRODUCED_OBSERVATION
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutionEvent:
    def test_record_execution_event_creates_node(self, graph: ContextGraphRepository) -> None:
        graph.record_execution_event({
            "event_id": 1,
            "event_type": "test_event",
            "entity_type": "test",
            "entity_id": "e1",
            "source": "test",
            "payload": {},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "ExecutionEvent") == 1
        node = _get(graph, "ExecutionEvent", "execution_event:1")
        assert node is not None
        assert node["event_type"] == "test_event"
        assert node["event_id"] == 1
        _assert_meta_shape(node)

    def test_record_execution_event_with_tickers_creates_mentions(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_execution_event({
            "event_id": 2,
            "event_type": "scan_completed",
            "entity_type": "scan",
            "entity_id": "s1",
            "source": "test",
            "payload": {"tickers": ["RELIANCE", "TCS"]},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _edge(graph, "MENTIONS") == 2
        assert _edge_between(
            graph, "MENTIONS", "execution_event:2", "stock:RELIANCE"
        )
        assert _edge_between(
            graph, "MENTIONS", "execution_event:2", "stock:TCS"
        )

    def test_record_execution_event_news_creates_news_and_produced_observation(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_stock("RELIANCE", source="test")
        graph.record_execution_event({
            "event_id": 3,
            "event_type": "news_item_ingested",
            "entity_type": "news",
            "entity_id": "news_hash_123",
            "source": "news_aggregator",
            "payload": {
                "news_id": "news_hash_123",
                "title": "Breaking: Market Up",
                "tickers": ["RELIANCE"],
                "provider": "test_provider",
            },
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "NewsArticle") == 1
        assert _edge(graph, "PRODUCED_OBSERVATION") == 1
        assert _edge(graph, "AFFECTS_STOCK") == 1

    def test_record_execution_event_failure_creates_failure_pattern(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_execution_event({
            "event_id": 4,
            "event_type": "broker_error_incident",
            "entity_type": "failure_incident",
            "entity_id": "fail1",
            "source": "broker",
            "payload": {"severity": "critical", "reason": "Connection lost"},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "FailurePattern") == 1
        assert _edge(graph, "FAILED_DURING") == 1

    def test_record_execution_event_single_ticker(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_execution_event({
            "event_id": 5,
            "event_type": "trade_placed",
            "entity_type": "trade",
            "entity_id": "tr1",
            "source": "test",
            "payload": {"ticker": "RELIANCE"},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _edge(graph, "MENTIONS") == 1

    def test_record_execution_event_idempotent(self, graph: ContextGraphRepository) -> None:
        event = {
            "event_id": 1, "event_type": "test", "entity_type": "test",
            "entity_id": "e1", "source": "test", "payload": {},
            "created_at": "2026-05-12T10:00:00+05:30",
        }
        graph.record_execution_event(event)
        graph.record_execution_event(event)
        assert _count(graph, "ExecutionEvent") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 11.  FailurePattern (standalone)
# ═══════════════════════════════════════════════════════════════════════════


class TestFailurePattern:
    def test_upsert_failure_pattern_creates_node_and_edge(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.record_execution_event({
            "event_id": 10, "event_type": "api_error",
            "entity_type": "failure_incident", "entity_id": "f1",
            "source": "test", "payload": {"severity": "high"},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "FailurePattern") == 1
        assert _count(graph, "ExecutionEvent") == 1
        assert _edge(graph, "FAILED_DURING") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 12.  SentimentSnapshot + SkillVersion (node-only)
# ═══════════════════════════════════════════════════════════════════════════


class TestMiscNodes:
    def test_upsert_sentiment_snapshot(self, graph: ContextGraphRepository) -> None:
        graph.upsert_sentiment_snapshot(
            text_hash="abc123",
            result={"label": "positive", "score": 0.92},
            text="Great earnings!",
            source="test",
        )
        assert _count(graph, "SentimentSnapshot") == 1
        node = _get(graph, "SentimentSnapshot", "sentiment:abc123")
        assert node is not None
        assert node["score"] == 0.92

    def test_upsert_sentiment_snapshot_idempotent(
        self, graph: ContextGraphRepository
    ) -> None:
        graph.upsert_sentiment_snapshot(
            text_hash="abc123", result={"label": "positive", "score": 0.92},
            source="test",
        )
        graph.upsert_sentiment_snapshot(
            text_hash="abc123", result={"label": "positive", "score": 0.95},
            source="test",
        )
        assert _count(graph, "SentimentSnapshot") == 1

    def test_upsert_skill_version(self, graph: ContextGraphRepository) -> None:
        graph.upsert_skill_version(
            version_id="v1",
            name="entry_rules_v3",
            content="Entry rules version 3",
            source="test",
        )
        assert _count(graph, "SkillVersion") == 1
        node = _get(graph, "SkillVersion", "skill:v1")
        assert node is not None
        assert node["name"] == "entry_rules_v3"

    def test_upsert_skill_version_idempotent(self, graph: ContextGraphRepository) -> None:
        kwargs = dict(
            version_id="v1", name="rules", content="same",
            source="test",
        )
        graph.upsert_skill_version(**kwargs)
        graph.upsert_skill_version(**kwargs)
        assert _count(graph, "SkillVersion") == 1


# ═══════════════════════════════════════════════════════════════════════════
# 13.  ProjectionCursor
# ═══════════════════════════════════════════════════════════════════════════


class TestProjectionCursor:
    def test_set_and_get_cursor(self, graph: ContextGraphRepository) -> None:
        graph.set_projection_cursor(500)
        assert _count(graph, "ProjectionCursor") == 1
        assert graph.get_projection_cursor() == 500

    def test_set_cursor_updates_existing(self, graph: ContextGraphRepository) -> None:
        graph.set_projection_cursor(100)
        graph.set_projection_cursor(200)
        assert _count(graph, "ProjectionCursor") == 1
        assert graph.get_projection_cursor() == 200

    def test_get_cursor_defaults_to_zero(self, graph: ContextGraphRepository) -> None:
        assert graph.get_projection_cursor() == 0


# ═══════════════════════════════════════════════════════════════════════════
# 14.  Schema
# ═══════════════════════════════════════════════════════════════════════════


class TestSchema:
    def test_ensure_schema_runs(self, graph: ContextGraphRepository) -> None:
        """Calling ensure_schema twice should not raise (idempotent)."""
        graph.ensure_schema()  # second call; first was in conftest
        # No assertion needed — just checking it doesn't raise


# ═══════════════════════════════════════════════════════════════════════════
# 15.  GraphProjector integration
# ═══════════════════════════════════════════════════════════════════════════


class TestGraphProjector:
    def test_project_event_creates_execution_event(
        self, graph: ContextGraphRepository
    ) -> None:
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 100,
            "event_type": "scan_completed",
            "entity_type": "scan",
            "entity_id": "s1",
            "source": "test",
            "payload": {},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "ExecutionEvent") == 1

    def test_project_event_with_tickers_creates_mentions(
        self, graph: ContextGraphRepository
    ) -> None:
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 101,
            "event_type": "scan_completed",
            "entity_type": "scan",
            "entity_id": "s2",
            "source": "test",
            "payload": {"tickers": ["RELIANCE"]},
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _edge(graph, "MENTIONS") == 1

    def test_project_once_returns_ok(self, graph: ContextGraphRepository) -> None:
        """_project_once returns ok even with no pending events."""
        from context_graph.projector import GraphProjector
        # Set cursor past all existing Postgres events so the sweep is a no-op
        from memory.db import session_scope
        from memory.repository import MemoryRepository
        with session_scope() as s:
            max_id = MemoryRepository(s).get_latest_execution_event_id() or 0
        graph.set_projection_cursor(max_id)
        projector = GraphProjector(graph_repo=graph, batch_size=100, interval=999)
        result = projector._project_once()
        assert result.projected == 0
        assert result.status == "ok"

    def test_project_position_event_creates_position(
        self, graph: ContextGraphRepository
    ) -> None:
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 200,
            "event_type": "order_intent_position_materialized",
            "entity_type": "position",
            "entity_id": "pos1",
            "source": "test",
            "payload": {
                "ticker": "RELIANCE",
                "state": "open",
                "created_at": "2026-05-12T10:00:00+05:30",
            },
        })
        assert _count(graph, "Stock") >= 1
        assert _edge(graph, "POSITION_FOR") == 1

    def test_project_approval_event(self, graph: ContextGraphRepository) -> None:
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 300,
            "event_type": "approval_updated",
            "entity_type": "approval",
            "entity_id": "app1",
            "source": "test",
            "payload": {
                "ticker": "RELIANCE",
                "status": "approved",
                "created_at": "2026-05-12T10:00:00+05:30",
            },
        })
        # Approval nodes use MERGE via _run_cypher
        with graph._driver.session() as s:
            cnt = s.run(
                "MATCH (a:Approval {id: 'approval:app1'}) RETURN count(a)"
            ).single()[0]
            assert cnt == 1
        assert _edge(graph, "APPROVAL_FOR") == 1

    def test_project_order_intent_event(self, graph: ContextGraphRepository) -> None:
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 400,
            "event_type": "order_intent_upserted",
            "entity_type": "order_intent",
            "entity_id": "oi1",
            "source": "test",
            "payload": {
                "ticker": "RELIANCE",
                "status": "proposed",
                "created_at": "2026-05-12T10:00:00+05:30",
            },
        })
        with graph._driver.session() as s:
            cnt = s.run(
                "MATCH (oi:OrderIntent {id: 'order_intent:oi1'}) RETURN count(oi)"
            ).single()[0]
            assert cnt == 1
        assert _edge(graph, "ORDER_INTENT_FOR") == 1
        assert _edge(graph, "GENERATED_INTENT") == 1

    def test_project_news_event_via_projector(self, graph: ContextGraphRepository) -> None:
        """Verify projector pipeline for news_item_ingested."""
        from context_graph.projector import GraphProjector
        projector = GraphProjector(graph_repo=graph)
        projector._project_event({
            "event_id": 500,
            "event_type": "news_item_ingested",
            "entity_type": "news",
            "entity_id": "news_hash_p1",
            "source": "news_aggregator",
            "payload": {
                "news_id": "news_hash_p1",
                "title": "Projector Test News",
                "tickers": ["RELIANCE"],
                "provider": "test",
            },
            "created_at": "2026-05-12T10:00:00+05:30",
        })
        assert _count(graph, "NewsArticle") == 1
        assert _edge(graph, "PRODUCED_OBSERVATION") == 1
        assert _edge(graph, "AFFECTS_STOCK") == 1
