"""Market endpoint/migration checks guarded to the disposable Postgres database."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

pytestmark = pytest.mark.skipif(
    urlsplit(os.getenv("DATABASE_URL", "")).path != "/swingtradev3_test",
    reason="Requires explicitly disposable Postgres database",
)


def test_market_api_is_read_only_authenticated_and_keeps_room_cutoff(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    from data.market_context.refresh import refresh
    from research_room.server import app

    config = json.loads(
        (Path(__file__).parents[2] / "research_room/local.example.json").read_text()
    )
    config["state_root"] = str(tmp_path)
    filename = tmp_path / "config.json"
    filename.write_text(json.dumps(config))
    monkeypatch.setenv("KEPLER_RESEARCH_CONFIG", str(filename))
    monkeypatch.setenv("FASTAPI_API_KEY", "market-disposable-fixture")
    client = TestClient(app)
    assert client.get("/research/market-context").status_code == 403
    client.headers["X-API-Key"] = "market-disposable-fixture"
    assert refresh()["network_requests"] == 0
    response = client.get("/research/market-context")
    assert response.status_code == 200
    assert len(response.json()["observations"]) == 3
    assert all(item["status"] == "unavailable" for item in response.json()["observations"])
    assert client.post("/research/market-context", json={}).status_code == 405
    assert client.get("/research/market-context?scope=orders").status_code == 422
    room = client.post(
        "/research/rooms",
        json={
            "request_id": str(uuid4()),
            "target": "Kepler",
            "question": "Which market inputs are available by the recorded cutoff?",
        },
    ).json()
    try:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        assert (
            client.get(
                "/research/market-context",
                params={
                    "room_id": room["id"],
                    "cutoff": future,
                },
            ).status_code
            == 422
        )
        saved = client.get("/research/market-context", params={"room_id": room["id"]}).json()
        assert saved["cutoff"] == room["source_cutoff"]
        assert saved["limits"]["network_requests"] == 0
    finally:
        client.post("/research/rooms/" + room["id"] + "/cancel")


async def test_scheduler_hook_runs_real_bounded_data_subprocess_without_news_or_broker_writes():
    from sqlalchemy import func, select

    from api.tasks.scheduler import TradingScheduler
    from memory.db import get_session_factory
    from memory.models import ExecutionEventRow, NewsArticleRow, NewsSourceVersionRow

    def counts():
        with get_session_factory()() as session:
            return [
                session.scalar(select(func.count()).select_from(table))
                for table in (ExecutionEventRow, NewsArticleRow, NewsSourceVersionRow)
            ]

    before = counts()
    await TradingScheduler()._gift_nifty_check()
    assert counts() == before
