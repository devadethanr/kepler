"""Concurrency checks against only the explicitly configured disposable test DB."""

import concurrent.futures
import os
from uuid import uuid4
from urllib.parse import urlsplit

import pytest

from research_room.store import Store, RoomStopped

pytestmark = pytest.mark.skipif(
    urlsplit(os.getenv("DATABASE_URL", "")).path != "/swingtradev3_test",
    reason="Requires explicitly disposable Postgres database; never use production",
)


def test_atomic_postgres_claim_admission_and_durable_cursor():
    store = Store()
    room = store.create(
        "Which evidence supports ACME?",
        "ACME",
        str(uuid4()),
        {"model": 1, "tool": 2, "seconds": 60},
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda owner: store.claim(owner, 30), ["one", "two"]))
    claimed = [x for x in claims if x and x["id"] == room["id"]]
    assert len(claimed) == 1
    owner = claimed[0]["owner"]

    def admit(_):
        try:
            store.admit(room["id"], owner, "model")
            return True
        except RoomStopped:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(admit, range(2))) == [False, True]
    first = store.event(room["id"], owner, "once", "message", {"text": "durable"})
    assert Store().events(room["id"], first["seq"] - 1)[0]["id"] == first["id"]
    store.cancel(room["id"])
    with pytest.raises(RoomStopped):
        store.admit(room["id"], owner, "tool")
    store.release(room["id"], owner, "model")
    store.finish(room["id"], owner, "abstention", "test complete")


def test_authenticated_room_api_idempotency_cancel_history_and_sse(monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from fastapi.testclient import TestClient
    from research_room.server import app

    settings = Path(__file__).parents[2] / "research_room/local.example.json"
    config = json.loads(settings.read_text())
    config["state_root"] = str(tmp_path)
    filename = tmp_path / "config.json"
    filename.write_text(json.dumps(config))
    monkeypatch.setenv("KEPLER_RESEARCH_CONFIG", str(filename))
    monkeypatch.setenv("FASTAPI_API_KEY", "only-this-disposable-test")
    client = TestClient(app)
    assert client.get("/research/rooms").status_code == 403
    client.headers["X-API-Key"] = "only-this-disposable-test"
    body = {
        "request_id": str(uuid4()),
        "target": "ACME",
        "question": "Which evidence supports ACME?",
    }
    response = client.post("/research/rooms", json=body)
    assert response.status_code == 202
    room = response.json()
    assert client.post("/research/rooms", json=body).json()["id"] == room["id"]
    assert client.post("/research/rooms", json={**body, "target": "BETA"}).status_code == 409
    assert client.post("/research/rooms", json={**body, "target": " "}).status_code == 422
    assert client.post("/research/rooms/" + room["id"] + "/cancel").json()["status"] == "cancelled"
    history = client.get("/research/rooms/" + room["id"] + "/events").json()
    stream = client.get("/research/rooms/" + room["id"] + "/stream")
    assert stream.status_code == 200
    assert "event: room" in stream.text
    cursor = history["cursor"]
    replay = client.get(
        "/research/rooms/" + room["id"] + "/stream", headers={"Last-Event-ID": str(cursor)}
    )
    assert "event: room" not in replay.text
    assert (
        client.get(
            "/research/rooms/" + room["id"] + "/stream", headers={"Last-Event-ID": "invalid"}
        ).status_code
        == 400
    )
    assert client.get("/research/rooms/does-not-exist").status_code == 404


def test_retry_links_a_new_attempt_without_replaying_old_tool_intents(monkeypatch, tmp_path):
    import json
    from pathlib import Path
    from fastapi.testclient import TestClient
    from research_room.server import app

    config = json.loads(
        (Path(__file__).parents[2] / "research_room/local.example.json").read_text()
    )
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setenv("KEPLER_RESEARCH_CONFIG", str(path))
    monkeypatch.setenv("FASTAPI_API_KEY", "disposable-retry-test")
    client = TestClient(app, headers={"X-API-Key": "disposable-retry-test"})
    room = client.post(
        "/research/rooms",
        json={
            "request_id": str(uuid4()),
            "target": "ACME",
            "question": "Which evidence supports ACME?",
        },
    ).json()
    client.post("/research/rooms/" + room["id"] + "/cancel")
    retry = client.post(
        "/research/rooms/" + room["id"] + "/retry", json={"request_id": str(uuid4())}
    )
    assert retry.status_code == 202
    linked = retry.json()
    assert linked["id"] != room["id"] and linked["parent_room"] == room["id"]
    assert linked["counts"]["tool"] == 0
    client.post("/research/rooms/" + linked["id"] + "/cancel")
