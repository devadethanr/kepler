import asyncio
import json
from typing import Any

class SSEBroadcaster:
    """Simple in-memory SSE broadcaster."""
    def __init__(self) -> None:
        self.queues: list[asyncio.Queue] = []

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected clients."""
        # Clean up dead queues if any, though we rely on unsubscribe
        msg = json.dumps({"type": event_type, "data": data})
        for q in list(self.queues):  # copy list to avoid mutation issues
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                self.queues.remove(q)
            except Exception:
                pass

    def subscribe(self) -> asyncio.Queue:
        """Create a new queue for a client."""
        q = asyncio.Queue(maxsize=100)
        self.queues.append(q)
        return q
        
    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a client queue."""
        if q in self.queues:
            self.queues.remove(q)

broadcaster = SSEBroadcaster()
