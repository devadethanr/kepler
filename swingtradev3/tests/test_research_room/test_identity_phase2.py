import concurrent.futures
import os
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from research_room.store import Store

LIMITS = {"model": 2, "tool": 2, "seconds": 60}
QUESTION = "What evidence supports ACME?"


def test_identity_includes_parent_question_and_target(store):
    request_id = str(uuid4())
    room = store.create(QUESTION, "ACME", request_id, LIMITS)
    assert store.create(QUESTION, "ACME", request_id, LIMITS)["id"] == room["id"]
    for question, target, parent in [
        (QUESTION, "ACME", "room:parent"),
        (QUESTION + " More?", "ACME", None),
        (QUESTION, "OTHER", None),
    ]:
        with pytest.raises(ValueError):
            store.create(question, target, request_id, LIMITS, parent_room=parent)
    linked_id = str(uuid4())
    linked = store.create(QUESTION, "ACME", linked_id, LIMITS, parent_room="room:parent")
    assert store.create(QUESTION, "ACME", linked_id, LIMITS, parent_room="room:parent") == linked
    with pytest.raises(ValueError):
        store.create(QUESTION, "ACME", linked_id, LIMITS, parent_room="room:other")


@pytest.mark.skipif(
    urlsplit(os.getenv("DATABASE_URL", "")).path != "/swingtradev3_test",
    reason="Requires explicitly disposable Postgres database",
)
def test_concurrent_postgres_idempotency_and_cancel_finish():
    import threading

    from sqlalchemy import event

    from memory.db import ensure_database_ready, get_engine

    ensure_database_ready()
    store = Store()
    request_id = str(uuid4())
    barrier = threading.Barrier(2)

    def create(parent):
        barrier.wait()
        try:
            return store.create(QUESTION, "ACME", request_id, LIMITS, parent_room=parent)
        except ValueError:
            return None

    def race(parents):
        # Both initial lookups have missed before either actual insert executes.
        insert_barrier = threading.Barrier(2, timeout=10)

        def synchronize_insert(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("INSERT INTO COGNITION_RUNS"):
                insert_barrier.wait()

        engine = get_engine()
        event.listen(engine, "before_cursor_execute", synchronize_insert)
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                return list(pool.map(create, parents))
        finally:
            event.remove(engine, "before_cursor_execute", synchronize_insert)

    result = race([None, None])
    assert result[0]["id"] == result[1]["id"]
    assert len([e for e in store.events(result[0]["id"]) if e["kind"] == "room.created"]) == 1
    store.cancel(result[0]["id"])

    request_id = str(uuid4())
    barrier = threading.Barrier(2)
    linked = race(["room:parent", "room:parent"])
    assert linked[0]["id"] == linked[1]["id"]
    assert linked[0]["parent_room"] == "room:parent"
    store.cancel(linked[0]["id"])

    request_id = str(uuid4())
    barrier = threading.Barrier(2)
    result = race([None, "room:parent"])
    assert sum(value is None for value in result) == 1

    room = next(value for value in result if value is not None)
    claimed = store.claim("phase2-owner-" + str(uuid4()), 60)
    # Existing tests may leave queued rooms in a reused DB; do not act on another room.
    if claimed and claimed["id"] != room["id"]:
        pytest.fail("Disposable database was not isolated: unexpected queued room")
    assert claimed is not None
    barrier = threading.Barrier(2)

    def cancel():
        barrier.wait()
        store.cancel(room["id"])

    def finish():
        barrier.wait()
        store.finish(room["id"], claimed["owner"], "conclusion", "finished")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(cancel), pool.submit(finish)]
        for future in futures:
            future.result()
    events = store.events(room["id"])
    terminal = [e for e in events if e["kind"] == "room.finished"]
    assert len(terminal) == 1
    assert terminal[0]["data"]["status"] == store.get(room["id"])["status"]


@pytest.mark.skipif(
    urlsplit(os.getenv("DATABASE_URL", "")).path != "/swingtradev3_test",
    reason="Requires explicitly disposable Postgres database",
)
def test_retry_route_reports_parent_identity_conflict(monkeypatch, tmp_path):
    import json
    from pathlib import Path

    from fastapi.testclient import TestClient

    from research_room.server import app

    config = json.loads(
        (Path(__file__).parents[2] / "research_room/local.example.json").read_text()
    )
    config["state_root"] = str(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setenv("KEPLER_RESEARCH_CONFIG", str(config_path))
    monkeypatch.setenv("FASTAPI_API_KEY", "disposable-identity-test")
    client = TestClient(app, headers={"X-API-Key": "disposable-identity-test"})
    request_id = str(uuid4())
    response = client.post(
        "/research/rooms", json={"question": QUESTION, "target": "ACME", "request_id": request_id}
    )
    assert response.status_code == 202
    room_id = response.json()["id"]
    client.post(f"/research/rooms/{room_id}/cancel")
    assert (
        client.post(f"/research/rooms/{room_id}/retry", json={"request_id": request_id}).status_code
        == 409
    )
    retry_id = str(uuid4())
    first = client.post(f"/research/rooms/{room_id}/retry", json={"request_id": retry_id})
    second = client.post(f"/research/rooms/{room_id}/retry", json={"request_id": retry_id})
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["parent_room"] == room_id
    client.post(f"/research/rooms/{first.json()['id']}/cancel")
