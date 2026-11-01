"""Actual spawned graph reader against the independently verified disposable graph."""

import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from context_graph.repository import ContextGraphRepository
from context_graph.test_safety import guard
from research_room.store import Budget
from research_room.tools import Gateway


@pytest.mark.skipif(not os.getenv("MEMGRAPH_TEST_EXPECTED_ADDRESS"),
                    reason="Requires independently verified disposable graph")
def test_owned_graph_child_reads_real_scoped_evidence(store, tmp_path):
    repository = ContextGraphRepository()
    guard(repository)  # Before any seed or deletion, never trust hostname alone.
    target = "PHASE2" + uuid4().hex[:10].upper()
    stock, article = "stock:" + target, "article:" + target
    try:
        repository._run(
            "CREATE (s:Stock {id: $stock, company_name: $target}) "
            "CREATE (n:NewsArticle {id: $article, title: $target}) "
            "CREATE (n)-[:MENTIONS]->(s)",
            {"stock": stock, "article": article, "target": target},
        )
        room = store.create("What evidence is present?", target, str(uuid4()),
                            {"model": 1, "tool": 2, "seconds": 60})
        store.claim("owner", 60)
        gateway = Gateway(SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler",
                                          max_messages=12), store, room, "owner",
                          Budget(store, room["id"], "owner"))
        result = gateway.dispatch("analyst", "lookup", "graph_lookup", {"entity": target})
        assert result["status"] == "ok"
        assert article in result["evidence"][0]["text"]
        result = gateway.dispatch("analyst", "neighbors", "graph_neighbors", {"node_id": article})
        assert result["status"] == "ok"
        assert stock in result["evidence"][0]["text"]
        gateway.close()
    finally:
        guard(repository)
        repository._run("MATCH (n) WHERE n.id IN $ids DETACH DELETE n", {"ids": [stock, article]})
        repository.close()
