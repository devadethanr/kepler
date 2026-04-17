from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import pytest

from api.main import app
from api.routes import postbacks as postbacks_route
from broker.postbacks import compute_postback_checksum
from config import cfg


client = TestClient(app)


def _payload() -> dict[str, object]:
    payload = {
        "user_id": "AB1234",
        "order_id": "220303000308932",
        "exchange_order_id": "1000000001482421",
        "status": "COMPLETE",
        "order_timestamp": "2022-03-03 09:24:25",
        "exchange_update_timestamp": "2022-03-03 09:24:25",
        "exchange": "NSE",
        "tradingsymbol": "SBIN",
        "order_type": "MARKET",
        "transaction_type": "BUY",
        "product": "CNC",
        "quantity": 1,
        "price": 0,
        "trigger_price": 0,
        "average_price": 470,
        "filled_quantity": 1,
        "pending_quantity": 0,
        "cancelled_quantity": 0,
        "tag": "STV3SBIN12345678",
    }
    payload["checksum"] = compute_postback_checksum(
        str(payload["order_id"]),
        str(payload["order_timestamp"]),
        "postback-secret",
    )
    return payload


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", True):
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "api-secret"}, clear=False):
            yield


def test_kite_postback_bypasses_api_key_and_reduces_valid_payload(monkeypatch):
    payload = _payload()
    mock_reduce = MagicMock(return_value={"status": "applied"})
    monkeypatch.setattr(postbacks_route, "reducer", MagicMock(apply_order_update=mock_reduce))

    with patch.dict("os.environ", {"KITE_API_SECRET": "postback-secret"}, clear=False):
        response = client.post("/broker/postbacks/kite", json=payload)

    assert response.status_code == 200
    assert response.json()["reducer"]["status"] == "applied"
    mock_reduce.assert_called_once_with(payload, source="postback")


def test_kite_postback_rejects_invalid_checksum(monkeypatch):
    payload = _payload()
    payload["checksum"] = "invalid"
    mock_reduce = MagicMock(return_value={"status": "applied"})
    monkeypatch.setattr(postbacks_route, "reducer", MagicMock(apply_order_update=mock_reduce))

    with patch.dict("os.environ", {"KITE_API_SECRET": "postback-secret"}, clear=False):
        response = client.post("/broker/postbacks/kite", json=payload)

    assert response.status_code == 403
    mock_reduce.assert_not_called()
