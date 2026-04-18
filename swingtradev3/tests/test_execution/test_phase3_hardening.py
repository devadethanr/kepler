from __future__ import annotations

from datetime import datetime, timedelta
import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routes import approvals as approvals_route
from auth.kite.session_store import KiteSessionPayload
from auth.token_manager import TokenManager
from broker.kite_rest import build_kite_client, has_kite_session
from broker.kite_stream import KiteBrokerStream
from config import cfg
from execution.bootstrap import WorkerRuntime
from memory.db import session_scope
from memory.repositories import MemoryRepository
from models import PendingApproval, TradingMode


client = TestClient(app)


@pytest.fixture(autouse=True)
def override_auth():
    with patch.object(cfg.api, "enabled", False):
        yield


def _approval_payload(ticker: str) -> list[dict[str, object]]:
    now = datetime.now()
    return [
        {
            "ticker": ticker,
            "score": 8.4,
            "setup_type": "breakout",
            "entry_zone": {"low": 1000.0, "high": 1010.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 7,
            "confidence_reasoning": "Strong setup",
            "risk_flags": [],
            "approved": None,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=4)).isoformat(),
        }
    ]


def _stored_session() -> KiteSessionPayload:
    return KiteSessionPayload(
        api_key="stored-api-key",
        access_token="stored-access-token",
        public_token="stored-public-token",
        user_id="RDK847",
        user_name="Devadethan R",
        login_time=datetime.now().isoformat(),
    )


def test_approval_route_persists_order_intent_for_worker_queue(monkeypatch):
    ticker = f"REL{uuid4().hex[:6]}".upper()
    payload = _approval_payload(ticker)
    mock_write = MagicMock()
    mock_broadcast = AsyncMock()

    monkeypatch.setattr(approvals_route, "read_json", lambda *_args, **_kwargs: payload)
    monkeypatch.setattr(approvals_route, "write_json", mock_write)
    monkeypatch.setattr(approvals_route.broadcaster, "broadcast", mock_broadcast)

    response = client.post(f"/approvals/{PendingApproval.model_validate(payload[0]).approval_id}/yes")

    assert response.status_code == 200
    assert payload[0]["execution_requested"] is True
    assert payload[0]["order_intent_id"]
    with session_scope() as session:
        repo = MemoryRepository(session)
        order_intent = repo.get_order_intent(str(payload[0]["order_intent_id"]))
    assert order_intent is not None
    assert order_intent["ticker"] == ticker
    assert order_intent["status"] == "queued"


def test_build_kite_client_prefers_persisted_session_credentials(monkeypatch):
    captured: dict[str, str | None] = {}

    class FakeKiteConnect:
        def __init__(self, api_key: str):
            captured["api_key"] = api_key
            self.api_key = api_key
            self.access_token = None

        def set_access_token(self, access_token: str) -> None:
            self.access_token = access_token
            captured["access_token"] = access_token

    monkeypatch.setattr("broker.kite_rest.KiteConnect", FakeKiteConnect)
    monkeypatch.setattr("broker.kite_rest.load_kite_session", lambda: _stored_session())
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)

    client_obj = build_kite_client()

    assert client_obj.api_key == "stored-api-key"
    assert client_obj.access_token == "stored-access-token"
    assert captured == {
        "api_key": "stored-api-key",
        "access_token": "stored-access-token",
    }


def test_has_kite_session_requires_both_env_credentials_without_persisted_session(monkeypatch):
    monkeypatch.setattr("broker.kite_rest.load_kite_session", lambda: None)

    monkeypatch.setenv("KITE_ACCESS_TOKEN", "env-token")
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    assert has_kite_session() is False

    monkeypatch.setenv("KITE_API_KEY", "env-key")
    assert has_kite_session() is True


@pytest.mark.asyncio
async def test_token_manager_refresh_restores_env_from_persisted_session(monkeypatch):
    monkeypatch.setattr("auth.token_manager.load_kite_session", lambda: _stored_session())
    monkeypatch.setenv("KITE_API_KEY", "wrong-key")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "wrong-token")

    await TokenManager().refresh()

    assert os.environ["KITE_API_KEY"] == "stored-api-key"
    assert os.environ["KITE_ACCESS_TOKEN"] == "stored-access-token"


@pytest.mark.asyncio
async def test_worker_maintains_broker_stream_when_session_appears(monkeypatch):
    runtime = WorkerRuntime()
    runtime._broker_stream = MagicMock()
    monkeypatch.setattr(runtime, "_broker_live_enabled", lambda: True)

    with patch("execution.bootstrap.has_kite_session", side_effect=[False, True]):
        await runtime._maintain_broker_stream()
        await runtime._maintain_broker_stream()

    runtime._broker_stream.stop.assert_called_once()
    runtime._broker_stream.ensure_running.assert_called_once()


@pytest.mark.asyncio
async def test_worker_fails_closed_when_live_startup_sync_fails(monkeypatch):
    runtime = WorkerRuntime()
    fake_lease = MagicMock()
    monkeypatch.setattr(cfg.trading, "mode", TradingMode.LIVE)
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    monkeypatch.setattr(runtime._broker_reducer, "sync_from_broker", MagicMock(side_effect=RuntimeError("boom")))

    with patch("execution.bootstrap.initialize_memory_layer"):
        with patch("execution.bootstrap.WorkerLease.acquire", return_value=fake_lease):
            with patch("execution.bootstrap.has_kite_session", return_value=True):
                with pytest.raises(RuntimeError, match="startup sync failed"):
                    await runtime.start()

    fake_lease.release.assert_called_once()


def test_broker_stream_rebuilds_after_reconnect_exhausted():
    created: list[object] = []

    class FakeTicker:
        MODE_FULL = "full"

        def __init__(self):
            self.connected = False
            self.connect_calls = 0
            self.close_calls = 0
            self.stop_calls = 0

        def connect(self, threaded: bool = True) -> None:
            self.connect_calls += 1

        def is_connected(self) -> bool:
            return self.connected

        def subscribe(self, _tokens):
            return None

        def set_mode(self, _mode, _tokens):
            return None

        def close(self, code=None, reason=None) -> None:
            self.close_calls += 1

        def stop(self) -> None:
            self.stop_calls += 1

    def factory() -> FakeTicker:
        ticker = FakeTicker()
        created.append(ticker)
        return ticker

    stream = KiteBrokerStream(ticker_factory=factory)
    stream.ensure_running()
    first = created[0]
    stream._on_noreconnect(first)
    stream.ensure_running()

    assert len(created) == 2
    assert created[0].connect_calls == 1
    assert created[1].connect_calls == 1


def test_broker_stream_rebuilds_when_access_token_changes(monkeypatch):
    created: list[object] = []

    class FakeTicker:
        MODE_FULL = "full"

        def __init__(self):
            self.connected = True
            self.connect_calls = 0
            self.close_calls = 0
            self.stop_calls = 0

        def connect(self, threaded: bool = True) -> None:
            self.connect_calls += 1

        def is_connected(self) -> bool:
            return self.connected

        def subscribe(self, _tokens):
            return None

        def set_mode(self, _mode, _tokens):
            return None

        def close(self, code=None, reason=None) -> None:
            self.close_calls += 1

        def stop(self) -> None:
            self.stop_calls += 1

    def factory() -> FakeTicker:
        ticker = FakeTicker()
        created.append(ticker)
        return ticker

    stream = KiteBrokerStream(ticker_factory=factory)

    monkeypatch.setattr(
        "broker.kite_stream.resolve_kite_credentials",
        MagicMock(side_effect=[("key", "token-a"), ("key", "token-b")]),
    )

    stream.ensure_running()
    stream.ensure_running()

    assert len(created) == 2
    assert created[0].close_calls == 1
    assert created[0].stop_calls == 1
