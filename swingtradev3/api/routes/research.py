"""Authenticated durable research room API; all inference runs in the separate worker."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from research_room.settings import load_settings
from research_room.store import Store, TERMINAL

router = APIRouter()


class CreateRoom(BaseModel):
    request_id: UUID
    target: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9 .&_-]+$")
    question: str = Field(min_length=8, max_length=3000)

    @field_validator("target", "question")
    @classmethod
    def nonblank(cls, value: str, info):
        result = value.strip()
        if len(result) < (8 if info.field_name == "question" else 1):
            raise ValueError("A nonblank target and meaningful question are required")
        return result


@router.get("/rooms")
def list_rooms():
    return {"rooms": Store().list()}


@router.post("/rooms", status_code=202)
def create_room(body: CreateRoom):
    try:
        settings = load_settings()
        return Store().create(
            body.question.strip(),
            body.target.strip(),
            str(body.request_id),
            {
                "model": settings.model_calls,
                "tool": settings.tool_calls,
                "seconds": settings.room_seconds,
            },
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/rooms/{room_id}")
def get_room(room_id: str):
    try:
        return Store().get(room_id)
    except KeyError as exc:
        raise HTTPException(404, "Research room not found") from exc


@router.get("/rooms/{room_id}/events")
def room_events(room_id: str, after: int = Query(0, ge=0)):
    get_room(room_id)
    events = Store().events(room_id, after)
    return {"events": events, "cursor": events[-1]["seq"] if events else after}


@router.post("/rooms/{room_id}/cancel")
def cancel_room(room_id: str):
    get_room(room_id)
    return Store().cancel(room_id)


@router.get("/rooms/{room_id}/stream")
async def stream_room(room_id: str, request: Request, after: int = Query(0, ge=0)):
    await asyncio.to_thread(get_room, room_id)
    try:
        cursor = max(after, int(request.headers.get("last-event-id", "0")))
    except ValueError as exc:
        raise HTTPException(400, "Invalid event cursor") from exc

    async def stream():
        nonlocal cursor
        while not await request.is_disconnected():
            events = await asyncio.to_thread(Store().events, room_id, cursor)
            for event in events:
                cursor = event["seq"]
                yield f"id: {cursor}\nevent: room\ndata: {json.dumps(event)}\n\n"
            state = await asyncio.to_thread(Store().get, room_id)
            if state["status"] in TERMINAL and cursor >= state["seq"]:
                return
            if not events:
                yield ": heartbeat\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/health")
def research_health():
    from urllib.request import ProxyHandler, build_opener

    try:
        settings = load_settings()
    except (RuntimeError, ValueError, OSError):
        return {"status": "unconfigured", "models": {}}
    opener = build_opener(ProxyHandler({}))
    models = {}
    for role, profile in settings.profiles.items():
        try:
            with opener.open(profile.endpoint + "/models", timeout=2) as response:
                ids = [item["id"] for item in json.load(response)["data"]]
            status = "ready" if profile.model in ids else "identity_mismatch"
        except Exception:
            status = "unavailable"
        models[role] = {"model": profile.model, "status": status}
    return {
        "status": "ready" if all(x["status"] == "ready" for x in models.values()) else "degraded",
        "models": models,
    }


class RetryRoom(BaseModel):
    request_id: UUID


@router.post("/rooms/{room_id}/retry", status_code=202)
def retry_room(room_id: str, body: RetryRoom):
    previous = get_room(room_id)
    if previous["status"] not in TERMINAL:
        raise HTTPException(409, "Finish or cancel the previous room before a linked attempt")
    try:
        settings = load_settings()
        return Store().create(
            previous["question"],
            previous["target"],
            str(body.request_id),
            {
                "model": settings.model_calls,
                "tool": settings.tool_calls,
                "seconds": settings.room_seconds,
            },
            parent_room=room_id,
        )
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
