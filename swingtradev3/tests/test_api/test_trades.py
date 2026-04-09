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

def test_get_trades():
    response = client.get("/trades")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_trade_not_found():
    response = client.get("/trades/NONEXISTENT")
    assert response.status_code == 404

def test_close_trade_not_implemented():
    response = client.post("/trades/NONEXISTENT/close")
    assert response.status_code == 501
