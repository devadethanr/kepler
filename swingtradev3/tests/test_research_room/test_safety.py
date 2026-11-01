import pytest

from config import ContextGraphConfig, ToolboxConfig
from context_graph.test_safety import UnsafeGraphTarget, validate_address, validate_target


def test_graph_and_toolbox_environment_overrides_explicit_yaml(monkeypatch):
    for key, value in {
        "MEMGRAPH_URI": "bolt://memgraph-test:7687",
        "MEMGRAPH_USER": "test-user",
        "MEMGRAPH_PASSWORD": "dummy-password",
        "MEMGRAPH_DATABASE": "disposable",
        "TOOLBOX_ENABLED": "false",
        "TOOLBOX_URL": "http://disabled:5000",
    }.items():
        monkeypatch.setenv(key, value)
    graph = ContextGraphConfig.model_validate(
        {"uri": "bolt://production:7687", "database": "real", "user": "yaml", "password": "yaml"}
    )
    toolbox = ToolboxConfig.model_validate({"enabled": True, "url": "http://production:5000"})
    assert graph.uri == "bolt://memgraph-test:7687"
    assert (graph.user, graph.password, graph.database) == (
        "test-user",
        "dummy-password",
        "disposable",
    )
    assert toolbox.enabled is False and toolbox.url == "http://disabled:5000"


@pytest.mark.parametrize(
    "uri,db,expected,ack",
    [
        ("bolt://memgraph:7687", "memgraph", "bolt://memgraph:7687", "kepler-disposable-only"),
        ("bolt://localhost:7687", "memgraph", "bolt://localhost:7687", "kepler-disposable-only"),
        (
            "bolt://memgraph-test:7687",
            "production",
            "bolt://memgraph-test:7687",
            "kepler-disposable-only",
        ),
        ("bolt://memgraph-test:7687", "memgraph", "bolt://memgraph-test:7687", ""),
        (
            "neo4j://memgraph-test:7687",
            "memgraph",
            "neo4j://memgraph-test:7687",
            "kepler-disposable-only",
        ),
    ],
)
def test_refuses_production_like_target_before_any_driver_access(uri, db, expected, ack):
    with pytest.raises(UnsafeGraphTarget):
        validate_target(uri, db, expected, "memgraph", ack)


def test_connected_endpoint_and_named_database_guard():
    validate_target(
        "bolt://memgraph-test:7687",
        "memgraph",
        "bolt://memgraph-test:7687",
        "memgraph",
        "kepler-disposable-only",
    )
    validate_address(("172.28.0.2", 7687), {"172.28.0.2"})
    with pytest.raises(UnsafeGraphTarget):
        validate_address(("172.27.0.2", 7687), {"172.28.0.2"})
    with pytest.raises(UnsafeGraphTarget):
        validate_address(("127.0.0.1", 7687), {"127.0.0.1"})


@pytest.mark.parametrize("expected", ["", "198.51.100.7:7687", "127.0.0.1:7687"])
def test_independent_expected_endpoint_required_before_driver_access(monkeypatch, expected):
    import os
    from context_graph.repository import ContextGraphRepository
    from context_graph.test_safety import guard

    if os.getenv("MEMGRAPH_TEST_ACK") != "kepler-disposable-only":
        pytest.skip("Requires the disposable test network for DNS only")
    monkeypatch.setenv("MEMGRAPH_TEST_EXPECTED_ADDRESS", expected)
    # A disabled real repository raises GraphUnavailableError if a driver is requested.
    # The target guard must refuse first, without creating a driver or running a query.
    repo = ContextGraphRepository(enabled=False)
    with pytest.raises(UnsafeGraphTarget):
        guard(repo)
