from __future__ import annotations

import asyncio
import json
from datetime import date, datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from memory.db import session_scope
from memory.repositories import MemoryRepository

router = APIRouter()


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _sse_frame(
    *,
    data: dict,
    event_id: int | None = None,
    event: str = "execution_event",
) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, default=_json_default)}")
    return "\n".join(lines) + "\n\n"


def _read_events(after_id: int | None, limit: int = 100) -> list[dict]:
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.list_execution_events(limit=limit, after_id=after_id)


def _latest_event_id() -> int | None:
    with session_scope() as session:
        repo = MemoryRepository(session)
        return repo.get_latest_execution_event_id()


def _cursor_from_request(request: Request, after_id: int | None) -> int | None:
    if after_id is not None:
        return after_id
    header_value = request.headers.get("last-event-id")
    if header_value is None:
        return None
    try:
        return int(header_value)
    except ValueError:
        return None


@router.get("/live")
async def live_dashboard(request: Request, after_id: int | None = None) -> StreamingResponse:
    """Durable dashboard SSE stream backed by execution_events."""

    async def event_stream() -> AsyncGenerator[str, None]:
        cursor = _cursor_from_request(request, after_id)
        if cursor is None:
            cursor = await asyncio.to_thread(_latest_event_id)

        yield _sse_frame(
            event="ready",
            event_id=cursor,
            data={"type": "ready", "cursor": cursor},
        )
        heartbeat_ticks = 0
        try:
            while True:
                if await request.is_disconnected():
                    break

                events = await asyncio.to_thread(_read_events, cursor, 100)
                if events:
                    for event in events:
                        cursor = int(event["event_id"])
                        yield _sse_frame(
                            event_id=cursor,
                            data={"type": event["event_type"], "data": event},
                        )
                    heartbeat_ticks = 0
                    continue

                heartbeat_ticks += 1
                if heartbeat_ticks >= 15:
                    heartbeat_ticks = 0
                    yield _sse_frame(
                        event="heartbeat",
                        event_id=cursor,
                        data={"type": "heartbeat", "cursor": cursor},
                    )
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
