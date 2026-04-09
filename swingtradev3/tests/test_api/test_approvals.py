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

def test_get_approvals():
    response = client.get("/approvals")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_approve_not_found():
    response = client.post("/approvals/NONEXISTENT/yes")
    assert response.status_code == 404

def test_reject_not_found():
    response = client.post("/approvals/NONEXISTENT/no")
    assert response.status_code == 404
