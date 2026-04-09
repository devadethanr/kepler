from __future__ import annotations

from fastapi.testclient import TestClient
import pytest
from unittest.mock import patch

from api.main import app
from config import cfg

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    # Disable auth for tests
    with patch.object(cfg.api, "enabled", False):
        yield

def test_get_positions():
    response = client.get("/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_position_not_found():
    response = client.get("/positions/NONEXISTENT")
    assert response.status_code == 404
