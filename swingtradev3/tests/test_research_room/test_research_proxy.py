"""Real Unix HTTP transport and existing authentication, against disposable Postgres only."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.research_proxy import router
from research_room.server import app as host_app

pytestmark = pytest.mark.skipif(
    urlsplit(os.getenv("DATABASE_URL", "")).path != "/swingtradev3_test",
    reason="Requires the disposable Postgres database; never production",
)


def test_real_unix_proxy_auth_create_history_cursor_and_cancel(monkeypatch, tmp_path):
    config = json.loads(
        (Path(__file__).parents[2] / "research_room/local.example.json").read_text()
    )
    config["state_root"] = str(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setenv("KEPLER_RESEARCH_CONFIG", str(config_path))
    monkeypatch.setenv("FASTAPI_API_KEY", "disposable-unix-proxy-test")
    with tempfile.TemporaryDirectory(prefix="krr-") as temporary:
        socket_path = Path(temporary) / "api.sock"
        monkeypatch.setenv("KEPLER_RESEARCH_SOCKET", str(socket_path))
        server = uvicorn.Server(uvicorn.Config(host_app, uds=str(socket_path), log_level="error"))
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for _ in range(100):
                if server.started:
                    break
                time.sleep(0.02)
            assert server.started
            app = FastAPI()
            app.include_router(router, prefix="/research")
            with TestClient(app) as client:
                assert client.get("/research/rooms").status_code == 403
                client.headers["X-API-Key"] = "disposable-unix-proxy-test"
                body = {
                    "request_id": str(uuid4()),
                    "target": "ACME",
                    "question": "Which evidence supports ACME?",
                }
                response = client.post("/research/rooms", json=body)
                assert response.status_code == 202
                room_id = response.json()["id"]
                assert client.get("/research/rooms/" + room_id).json()["status"] == "queued"
                assert (
                    client.post("/research/rooms/" + room_id + "/cancel").json()["status"]
                    == "cancelled"
                )
                history = client.get("/research/rooms/" + room_id + "/events").json()
                streamed = client.get("/research/rooms/" + room_id + "/stream")
                assert streamed.status_code == 200 and "event: room" in streamed.text
                assert "room.cancel_requested" in streamed.text
                replay = client.get(
                    "/research/rooms/" + room_id + "/stream",
                    headers={"Last-Event-ID": str(history["cursor"])},
                )
                assert replay.status_code == 200 and "event: room" not in replay.text
                assert client.get("/research/rooms/missing").status_code == 404
        finally:
            server.should_exit = True
            thread.join(timeout=5)
            assert not thread.is_alive()


def test_unavailable_unix_backend_returns_auth_failure_or_honest_503(monkeypatch):
    monkeypatch.setenv("FASTAPI_API_KEY", "disposable-unix-proxy-test")
    monkeypatch.setenv("KEPLER_RESEARCH_SOCKET", "/tmp/kepler-nonexistent-test-socket")
    app = FastAPI()
    app.include_router(router, prefix="/research")
    with TestClient(app) as client:
        assert client.get("/research/rooms").status_code == 403
        response = client.get(
            "/research/rooms", headers={"X-API-Key": "disposable-unix-proxy-test"}
        )
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"]
