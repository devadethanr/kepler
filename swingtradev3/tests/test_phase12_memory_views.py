from __future__ import annotations

import yaml
from sqlalchemy import text

from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory_views import MemoryViewClient


PHASE12_VIEWS = (
    "portfolio_risk_view",
    "open_positions_view",
    "execution_incidents_view",
    "policy_effective_view",
    "session_readiness_view",
    "recent_trades_view",
    "reconciliation_readiness_view",
    "operator_controls_view",
)


def test_phase12_postgres_views_are_queryable() -> None:
    with session_scope() as session:
        for view_name in PHASE12_VIEWS:
            rows = session.execute(text(f"SELECT * FROM {view_name} LIMIT 1")).all()
            assert rows is not None


def test_phase12_memory_client_uses_local_view_fallback(monkeypatch) -> None:
    client = MemoryViewClient()
    monkeypatch.setattr(client, "_toolbox_call", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        client,
        "_query_view",
        lambda *_args, **_kwargs: [{"cash_inr": 1000.0, "open_positions_count": 0}],
    )

    assert client.portfolio_risk_snapshot()["cash_inr"] == 1000.0


def test_phase12_toolbox_config_is_read_only() -> None:
    docs = list(yaml.safe_load_all(open("toolbox/tools.yaml", encoding="utf-8")))
    tools = [item for item in docs if item and item.get("kind") == "tool"]
    assert tools
    assert {tool["type"] for tool in tools} <= {"postgres-sql", "neo4j-cypher"}
    assert "postgres-execute-sql" not in {tool["type"] for tool in tools}
    assert "neo4j-execute-cypher" not in {tool["type"] for tool in tools}

    mutating_tokens = (" INSERT ", " UPDATE ", " DELETE ", " MERGE ", " CREATE ", " DROP ")
    for tool in tools:
        statement = f" {str(tool.get('statement') or '').upper()} "
        assert not any(token in statement for token in mutating_tokens), tool["name"]


def test_phase12_graph_traversal_applies_allow_lists() -> None:
    class FakeGraph(ContextGraphRepository):
        def __init__(self) -> None:
            super().__init__(enabled=True)
            self.params = {}

        def _run(self, query, parameters=None):
            self.params = parameters or {}
            return []

    graph = FakeGraph()
    graph.get_graph_neighbors(
        "stock:RELIANCE",
        allowed_labels=["Stock", "IllegalLabel"],
        allowed_relationships=["HAS_SIGNAL", "MERGE"],
        limit=10,
    )

    assert graph.params["labels"] == ["Stock"]
    assert graph.params["relationships"] == ["HAS_SIGNAL"]
