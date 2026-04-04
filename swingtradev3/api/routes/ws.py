from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

connected_clients: set[WebSocket] = set()


@router.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts and position updates."""
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)


async def broadcast_alert(alert: dict) -> None:
    """Send alert to all connected WebSocket clients."""
    disconnected = set()
    for client in connected_clients:
        try:
            await client.send_json(alert)
        except Exception:
            disconnected.add(client)
    connected_clients.difference_update(disconnected)
