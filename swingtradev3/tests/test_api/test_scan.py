from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch

from api.main import app
from config import cfg

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield

def test_scan_status():
    response = client.get("/scan/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data

def test_trigger_scan():
    with patch("api.routes.scan.scan_status_store", {"status": "idle"}):
        response = client.post("/scan")
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

def test_trigger_scan_already_running():
    with patch("api.routes.scan.scan_status_store", {"status": "running"}):
        response = client.post("/scan")
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
