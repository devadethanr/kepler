import asyncio
import os
import httpx
from httpx_sse import aconnect_sse
import reflex as rx
import json
import plotly.graph_objects as go
import plotly.express as px

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
    
    # Portfolio State
    positions: list[dict] = []
    
    # Research/Scan State
    scan_status: str = "idle"
    latest_scan_result: dict = {}
    trending_sectors: list[dict] = []
    top_setups: list[dict] = []
    
    # UI Control
    is_scanning: bool = False
    
    @rx.var(cache=True)
    def sector_exposure_fig(self) -> go.Figure:
        exposure = self.portfolio_summary.get("sector_exposure", {})
        if not exposure:
            fig = px.pie(names=["No Data"], values=[1], hole=0.5)
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='gray'),
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False
            )
            return fig
            
        labels = list(exposure.keys())
        values = list(exposure.values())
        fig = px.pie(names=labels, values=values, hole=0.6)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        return fig

    @rx.var(cache=True)
    def risk_utilization_fig(self) -> go.Figure:
        total_invested = float(self.portfolio_summary.get("total_invested", 0.0))
        cash = float(self.portfolio_summary.get("cash_inr", 0.0))
        total_capital = total_invested + cash
        percentage = (total_invested / total_capital * 100) if total_capital > 0 else 0

        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = percentage,
            number = {'suffix': "%", 'font': {'color': 'white'}},
            gauge = {
                'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#00A86B"},
                'bgcolor': "rgba(255,255,255,0.1)",
                'steps': [
                    {'range': [0, 50], 'color': "rgba(0, 168, 107, 0.2)"},
                    {'range': [50, 80], 'color': "rgba(255, 191, 0, 0.2)"},
                    {'range': [80, 100], 'color': "rgba(255, 68, 68, 0.2)"}
                ]
            }
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            margin=dict(l=20, r=20, t=20, b=20),
            height=250
        )
        return fig
    
    @rx.event(background=True)
    async def connect_sse(self):
        """Connects to the FastAPI SSE endpoint to receive live updates."""
        headers = {"X-API-Key": API_KEY}
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    async with aconnect_sse(client, "GET", f"{FASTAPI_URL}/sse/live", headers=headers, timeout=None) as event_source:
                        async for sse in event_source.aiter_sse():
                            if sse.data:
                                try:
                                    payload = json.loads(sse.data)
                                    event_type = payload.get("type")
                                    data = payload.get("data", {})
                                    
                                    async with self:
                                        if event_type == "agent_activity":
                                            agent_name = data.get("agent_name")
                                            if agent_name:
                                                self.agent_activity[agent_name] = data
                                        elif event_type == "scheduler_phase":
                                            self.scheduler_phase = data.get("phase", "Unknown")
                                        elif event_type == "scan_update":
                                            self.scan_status = data.get("status")
                                            self.is_scanning = (self.scan_status == "running")
                                            
                                    if event_type == "scan_update" and data.get("status") == "completed":
                                        yield GlobalState.fetch_scan_status
                                    elif event_type == "position_update":
                                        yield GlobalState.fetch_positions
                                        yield GlobalState.fetch_portfolio_summary
                                except Exception as e:
                                    print(f"Error parsing SSE data: {e}")
            except Exception as e:
                print(f"SSE connection failed: {e}")
                # Log extra info for debugging
                try:
                    async with httpx.AsyncClient() as client:
                        res = await client.get(f"{FASTAPI_URL}/health", headers={"X-API-Key": API_KEY})
                        print(f"Health check status: {res.status_code}")
                except:
                    pass
                print("Retrying in 5 seconds...")
                await asyncio.sleep(5)
                


    async def fetch_initial_data(self):
        """Fetch initial dashboard data from REST API."""
        headers = {"X-API-Key": API_KEY}
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
                
                # Fetch positions
                await self.fetch_positions()
                
                # Fetch scan status
                await self.fetch_scan_status()
        except Exception as e:
            print(f"Error fetching initial data: {e}")

        # Start background SSE connection
        return GlobalState.connect_sse

    @rx.event
    async def fetch_positions(self):
        """Fetch the list of open positions."""
        headers = {"X-API-Key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{FASTAPI_URL}/positions", headers=headers)
                if res.status_code == 200:
                    self.positions = res.json()
        except Exception as e:
            print(f"Error fetching positions: {e}")

    @rx.event
    async def fetch_scan_status(self):
        """Fetch the latest scan status."""
        headers = {"X-API-Key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{FASTAPI_URL}/scan/status", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    self.scan_status = data.get("status", "idle")
                    self.latest_scan_result = data.get("result") or {}
                    
                    # Process trending sectors
                    if self.latest_scan_result and "shortlist" in self.latest_scan_result:
                        shortlist = self.latest_scan_result["shortlist"]
                        sectors = {}
                        for stock in shortlist:
                            s = stock.get("sector", "Unknown")
                            sectors[s] = sectors.get(s, 0) + 1
                        
                        # Sort and pick top 3
                        sorted_sectors = sorted(sectors.items(), key=lambda x: x[1], reverse=True)
                        self.trending_sectors = [{"name": s, "count": c} for s, c in sorted_sectors[:3]]
                        self.top_setups = shortlist[:4]
                
                self.is_scanning = (self.scan_status == "running")
        except Exception as e:
            print(f"Error fetching scan status: {e}")

    @rx.event
    def trigger_scan(self):
        """Trigger the market scan pipeline."""
        self.is_scanning = True
        try:
            headers = {"X-API-Key": API_KEY}
            # Use background execution for the request if it might hang
            response = httpx.post(f"{FASTAPI_URL}/scan", headers=headers, timeout=30.0)
            if response.status_code in (200, 202):
                data = response.json()
                if data.get("status") == "accepted":
                    return rx.toast("Market scan triggered successfully")
                else:
                    self.is_scanning = False
                    return rx.toast(f"Scan rejected: {data.get('message')}")
            else:
                self.is_scanning = False
                return rx.toast(f"Failed to trigger scan: {response.status_code}")
        except Exception as e:
            self.is_scanning = False
            return rx.toast(f"Error triggering scan: {str(e)}")
