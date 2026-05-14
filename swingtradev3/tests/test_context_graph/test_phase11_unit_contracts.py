from __future__ import annotations

from typing import Any

from context_graph.projector import GraphProjector
from context_graph.repository import ContextGraphRepository
from data.news.aggregator import NewsAggregator
from data.news.parsers import extract_tickers_from_text


class FakeGraph(ContextGraphRepository):
    def __init__(self) -> None:
        super().__init__(enabled=True)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def _run(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        params = parameters or {}
        self.calls.append((query, params))
        if "MATCH (n)" in query:
            return [
                {
                    "id": "news:1",
                    "labels": ["NewsArticle"],
                    "properties": {
                        "id": "news:1",
                        "title": "Reliance wins order",
                        "summary": "Useful catalyst",
                        "confidence": 0.95,
                    },
                }
            ]
        if "MATCH (a)-[r]->(b)" in query:
            return [
                {
                    "source": "news:1",
                    "target": "stock:RELIANCE",
                    "label": "AFFECTS_STOCK",
                    "properties": {"confidence": 0.95},
                }
            ]
        return []


class FakeProjectorGraph:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.stocks: list[str] = []
        self.cypher_calls: list[tuple[str, dict[str, Any]]] = []

    def record_execution_event(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def upsert_stock(self, ticker: str, *, source: str = "context_graph") -> None:
        self.stocks.append(ticker)

    def _run(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        self.cypher_calls.append((query, parameters or {}))
        return []

    def close(self) -> None:
        return None


def test_dashboard_graph_exposes_frontend_contract_fields() -> None:
    payload = FakeGraph().dashboard_graph(node_limit=1, edge_limit=1)

    assert payload.last_updated
    assert payload.counts["nodes"] == 1
    assert payload.nodes[0].metadata["title"] == "Reliance wins order"
    assert payload.nodes[0].name == "Reliance wins order"
    assert payload.nodes[0].summary == "Useful catalyst"
    assert payload.edges[0].relationship == "AFFECTS_STOCK"
    assert payload.edges[0].metadata["confidence"] == 0.95


def test_news_edges_split_verified_affects_from_loose_mentions() -> None:
    graph = FakeGraph()

    graph.upsert_news_item(
        {
            "news_id": "n1",
            "title": "Reliance update mentions TCS vendor",
            "verified_tickers": ["RELIANCE"],
            "mentioned_tickers": ["TCS"],
            "tickers": ["RELIANCE", "TCS"],
            "confidence": 0.91,
        }
    )

    affect_edges = [
        params["stock_id"]
        for query, params in graph.calls
        if "AFFECTS_STOCK" in query and "stock_id" in params
    ]
    mention_edges = [
        params["stock_id"]
        for query, params in graph.calls
        if "MERGE (n)-[rel:MENTIONS]" in query and "stock_id" in params
    ]
    assert affect_edges == ["stock:RELIANCE"]
    assert mention_edges == ["stock:TCS"]


def test_research_run_materializes_market_snapshots() -> None:
    graph = FakeGraph()

    graph.upsert_research_run(
        run_id="research:2026-05-14",
        scan_date="2026-05-14",
        analyzed_at="2026-05-14T09:30:00+05:30",
        regime={"regime": "neutral"},
        diagnostics={"total_screened": 1},
        qualified_count=1,
        total_screened=1,
        shortlist=[{"ticker": "RELIANCE", "score": 8.1}],
        scan_results=[{"ticker": "RELIANCE", "score": 8.1}],
        stock_data={
            "RELIANCE": {
                "technical": {"rsi": 61},
                "fundamentals": {"pe": 22},
                "sentiment": {"sentiment_score": 0.4, "sentiment_label": "bullish"},
                "options": {"signal": "support"},
            }
        },
    )

    merged_labels = "\n".join(query for query, _ in graph.calls)
    assert "TechnicalSnapshot" in merged_labels
    assert "FundamentalSnapshot" in merged_labels
    assert "SentimentSnapshot" in merged_labels
    assert "SignalSnapshot" in merged_labels


def test_news_aggregator_default_mode_does_not_write_runtime_json(monkeypatch) -> None:
    writes: list[str] = []

    def fail_write(path: Any, payload: Any) -> None:
        writes.append(str(path))
        raise AssertionError("unexpected runtime JSON write")

    monkeypatch.setattr("data.news.core.write_json", fail_write)
    aggregator = NewsAggregator()
    monkeypatch.setattr(aggregator, "_persist_postgres", lambda results: None)
    monkeypatch.setattr(aggregator, "_persist_context_graph", lambda results: None)
    aggregator._persist_results(
        [
            {
                "title": "Reliance Industries board update",
                "canonical_url": "https://example.test/reliance",
                "verified_tickers": ["RELIANCE"],
            }
        ]
    )

    assert writes == []


def test_ticker_extraction_does_not_match_single_company_first_word() -> None:
    universe = [{"ticker": "TCS", "name": "Tata Consultancy Services Ltd"}]

    assert extract_tickers_from_text("Tata Steel announces expansion", universe) == []
    assert extract_tickers_from_text("Tata Consultancy Services wins deal", universe) == ["TCS"]


def test_projector_materializes_position_for_order_intent_event_type() -> None:
    graph = FakeProjectorGraph()
    projector = GraphProjector(graph_repo=graph)  # type: ignore[arg-type]

    projector._project_event(
        {
            "event_id": 42,
            "event_type": "order_intent_position_materialized",
            "entity_type": "order_intent",
            "entity_id": "intent-1",
            "source": "unit_test",
            "created_at": "2026-05-14T09:30:00+05:30",
            "payload": {
                "ticker": "RELIANCE",
                "position_id": "pos-1",
                "order_intent_id": "intent-1",
            },
        }
    )

    assert graph.events[0]["created_at"] == "2026-05-14T09:30:00+05:30"
    assert "RELIANCE" in graph.stocks
    assert any("MERGE (p:Position {id: $position_id})" in query for query, _ in graph.cypher_calls)
    assert any(params.get("position_id") == "position:pos-1" for _, params in graph.cypher_calls)
    assert any("MERGE (oi:OrderIntent {id: $intent_id})" in query for query, _ in graph.cypher_calls)
