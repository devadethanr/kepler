import asyncio
import os
import httpx
from httpx_sse import aconnect_sse
import reflex as rx
import json

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "dev_api_key_123")

class GlobalState(rx.State):
    """Global reactive state for the dashboard."""
    
    agent_activity: dict[str, dict[str, str]] = {}
    scheduler_phase: str = "Unknown"
    portfolio_summary: dict = {
        "cash_inr": 0.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "total_pnl": 0.0,
        "open_positions_count": 0,
        "sector_exposure": {},
        "total_invested": 0.0
    }
    
    @rx.event(background=True)
    async def connect_sse(self):
        """Connects to the FastAPI SSE endpoint to receive live updates."""
        headers = {"x-api-key": API_KEY}
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    async with aconnect_sse(client, "GET", f"{FASTAPI_URL}/sse/live", headers=headers, timeout=None) as event_source:
                        async for sse in event_source.aiter_sse():
                            if sse.data:
                                try:
                                    payload = json.loads(sse.data)
                                    await self.process_event(payload)
                                except Exception as e:
                                    print(f"Error parsing SSE data: {e}")
            except Exception as e:
                print(f"SSE connection failed: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)
                
    async def process_event(self, payload: dict):
        event_type = payload.get("type")
        data = payload.get("data", {})
        
        async with self:
            if event_type == "agent_activity":
                agent_name = data.get("agent_name")
                if agent_name:
                    self.agent_activity[agent_name] = data
            elif event_type == "scheduler_phase":
                self.scheduler_phase = data.get("phase", "Unknown")

    async def fetch_initial_data(self):
        """Fetch initial dashboard data from REST API."""
        headers = {"x-api-key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{FASTAPI_URL}/portfolio/summary", headers=headers)
                if res.status_code == 200:
                    self.portfolio_summary = res.json()
                
                # Fetch current activity snapshot
                res = await client.get(f"{FASTAPI_URL}/dashboard/activity", headers=headers)
                if res.status_code == 200:
                    snapshot = res.json()
                    self.agent_activity = snapshot.get("agents", {})
                    self.scheduler_phase = snapshot.get("scheduler_phase", "Unknown")
        except Exception as e:
            print(f"Error fetching initial data: {e}")

        # Start background SSE connection
        return GlobalState.connect_sse
