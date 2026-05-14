"""pytest fixtures for Memgraph integration tests.

These tests require a running Memgraph instance (bolt://memgraph:7687).
Run with: make test-memgraph

Each test receives a fresh ``graph`` instance with Memgraph pre-wiped.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from context_graph.repository import ContextGraphRepository, GraphUnavailableError


def _wipe(repo: ContextGraphRepository) -> None:
    """Remove all nodes and edges from Memgraph."""
    repo._client()
    with repo._driver.session() as s:
        s.run("MATCH (n) DETACH DELETE n")


@pytest.fixture(scope="session")
def _schema() -> Generator[None, None, None]:
    """Ensure Memgraph schema exists once per session; clean at session end."""
    repo = ContextGraphRepository()
    try:
        repo._client()
    except GraphUnavailableError:
        pytest.skip("Memgraph is not available")
    try:
        repo.ensure_schema()
    except GraphUnavailableError:
        pytest.skip("Memgraph schema unavailable")
    _wipe(repo)
    yield
    _wipe(repo)


@pytest.fixture
def graph(_schema: None) -> ContextGraphRepository:
    """Return a fresh ContextGraphRepository with Memgraph wiped.

    Each call wipes all data so tests start clean.
    """
    repo = ContextGraphRepository()
    _wipe(repo)
    return repo
