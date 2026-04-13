from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.sse_broadcaster import broadcaster

router = APIRouter()

@router.get("/live")
async def live_dashboard() -> StreamingResponse:
    """Server-Sent Events endpoint for real-time dashboard updates."""

    async def event_stream() -> AsyncGenerator[str, None]:
        queue = broadcaster.subscribe()
        try:
            while True:
                # Wait for next event
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            broadcaster.unsubscribe(queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
