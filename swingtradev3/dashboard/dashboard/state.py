import asyncio
import os
import httpx
from httpx_sse import aconnect_sse
import reflex as rx
import json
import plotly.graph_objects as go
import plotly.express as px
from dashboard.components.knowledge_graph_plotly import create_knowledge_graph_figure

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv(
    "FASTAPI_API_KEY", "67cb4e282a4935b76110bb41299784c7edf612b45abbe42ae33c6087394ce629"
)


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
        "total_invested": 0.0,
    }

    # Portfolio State
    positions: list[dict] = []

    # Research/Scan State
    scan_status: str = "idle"
    latest_scan_result: dict = {}
    trending_sectors: list[dict] = []
    top_setups: list[dict] = []

    # Knowledge Graph State
    knowledge_graph_nodes: list[dict] = []
    knowledge_graph_edges: list[dict] = []
    selected_kg_node: dict = {}
    graph_dimension: str = "2d"

    # UI Control
    is_scanning: bool = False
    next_scheduled_task: str = ""
    recent_events: list[dict] = []
    failed_events_count: int = 0
    failed_events: list[dict] = []

    @rx.var(cache=True)
    def formatted_total_invested(self) -> str:
        """Format total invested as INR with commas."""
        val = self.portfolio_summary.get("total_invested", 0.0)
        return f"₹{val:,.0f}"

    @rx.var(cache=True)
    def formatted_total_pnl(self) -> str:
        """Format total P&L as INR with commas and color."""
        val = self.portfolio_summary.get("total_pnl", 0.0)
        prefix = "+" if val >= 0 else ""
        return f"{prefix}₹{val:,.0f}"

    @rx.var(cache=True)
    def pnl_color(self) -> str:
        """Return color based on P&L."""
        val = self.portfolio_summary.get("total_pnl", 0.0)
        return "#00d4aa" if val >= 0 else "#ff4444"

    @rx.var(cache=True)
    def running_agents_count(self) -> int:
        """Count of currently running agents."""
        return sum(1 for agent in self.agent_activity.values() if agent.get("status") == "running")

    @rx.var(cache=True)
    def sector_exposure_fig(self) -> go.Figure:
        exposure = self.portfolio_summary.get("sector_exposure", {})
        if not exposure:
            fig = px.pie(names=["No Data"], values=[1], hole=0.5)
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="gray"),
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False,
            )
            return fig

        labels = list(exposure.keys())
        values = list(exposure.values())
        fig = px.pie(names=labels, values=values, hole=0.6)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        return fig

    @rx.var(cache=True)
    def risk_utilization_fig(self) -> go.Figure:
        total_invested = float(self.portfolio_summary.get("total_invested", 0.0))
        cash = float(self.portfolio_summary.get("cash_inr", 0.0))
        total_capital = total_invested + cash
        percentage = (total_invested / total_capital * 100) if total_capital > 0 else 0

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=percentage,
                number={"suffix": "%", "font": {"color": "white"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "white"},
                    "bar": {"color": "#00A86B"},
                    "bgcolor": "rgba(255,255,255,0.1)",
                    "steps": [
                        {"range": [0, 50], "color": "rgba(0, 168, 107, 0.2)"},
                        {"range": [50, 80], "color": "rgba(255, 191, 0, 0.2)"},
                        {"range": [80, 100], "color": "rgba(255, 68, 68, 0.2)"},
                    ],
                },
            )
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=250,
        )
        return fig

    @rx.event(background=True)
    async def connect_sse(self):
        """Connects to the FastAPI SSE endpoint to receive live updates."""
        headers = {"X-API-Key": API_KEY}
        while True:
            try:
                async with httpx.AsyncClient() as client:
                    async with aconnect_sse(
                        client, "GET", f"{FASTAPI_URL}/sse/live", headers=headers, timeout=None
                    ) as event_source:
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
                                            self.is_scanning = self.scan_status == "running"

                                    if (
                                        event_type == "scan_update"
                                        and data.get("status") == "completed"
                                    ):
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
                        res = await client.get(
                            f"{FASTAPI_URL}/health", headers={"X-API-Key": API_KEY}
                        )
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

                # Fetch scheduler info
                res = await client.get(f"{FASTAPI_URL}/dashboard/scheduler", headers=headers)
                if res.status_code == 200:
                    sched_data = res.json()
                    self.next_scheduled_task = sched_data.get("next_task", "")
                    self.failed_events_count = sched_data.get("failed_events", 0)

                # Fetch positions
                await self.fetch_positions()

                # Fetch scan status
                await self.fetch_scan_status()

                # Fetch knowledge graph
                await self.fetch_knowledge_graph()

                # Fetch failed events
                await self.fetch_failed_events()
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
                        self.trending_sectors = [
                            {"name": s, "count": c} for s, c in sorted_sectors[:3]
                        ]
                        self.top_setups = shortlist[:4]

                self.is_scanning = self.scan_status == "running"
        except Exception as e:
            print(f"Error fetching scan status: {e}")

    @rx.event
    async def fetch_knowledge_graph(self):
        """Fetch knowledge graph data for visualization."""
        headers = {"X-API-Key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{FASTAPI_URL}/dashboard/knowledge/graph", headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    self.knowledge_graph_nodes = data.get("nodes", [])
                    self.knowledge_graph_edges = data.get("edges", [])
        except Exception as e:
            print(f"Error fetching knowledge graph: {e}")

    @rx.event
    def select_kg_node(self, node: dict):
        """Handle node selection from graph."""
        self.selected_kg_node = node

    @rx.event
    def toggle_graph_dimension(self):
        """Toggle between 2D and 3D graph visualization."""
        self.graph_dimension = "3d" if self.graph_dimension == "2d" else "2d"

    @rx.var(cache=True)
    def knowledge_graph_figure(self) -> go.Figure:
        """Create knowledge graph visualization figure."""
        dim = 3 if self.graph_dimension == "3d" else 2
        return create_knowledge_graph_figure(
            self.knowledge_graph_nodes, self.knowledge_graph_edges, dim=dim, dark_theme=True
        )

    @rx.var(cache=True)
    def graph_data(self) -> dict:
        """Transform nodes/edges to force-graph format."""
        nodes = []
        for node in self.knowledge_graph_nodes:
            node_id = node.get("id", "")
            category = node.get("category", "unknown")
            group = node_id.split(":")[0] if ":" in node_id else "entity"
            nodes.append(
                {
                    "id": node_id,
                    "name": node_id.split(":")[-1] if ":" in node_id else node_id,
                    "group": group,
                    "category": category,
                    "val": 1,
                }
            )

        links = []
        for edge in self.knowledge_graph_edges:
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source and target:
                links.append(
                    {
                        "source": source,
                        "target": target,
                    }
                )

        return {"nodes": nodes, "links": links}

    @rx.event
    def trigger_scan(self):
        """Trigger the market scan pipeline."""
        self.is_scanning = True
        try:
            headers = {"X-API-Key": API_KEY}
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

    @rx.event
    async def fetch_failed_events(self):
        """Fetch failed events from the API."""
        headers = {"X-API-Key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{FASTAPI_URL}/portfolio/failed-events", headers=headers)
                if res.status_code == 200:
                    self.failed_events = res.json()
        except Exception as e:
            print(f"Error fetching failed events: {e}")

    @rx.event
    async def retry_failed_event(self, event_id: str):
        """Manually retry a failed event."""
        headers = {"X-API-Key": API_KEY}
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{FASTAPI_URL}/portfolio/failed-events/{event_id}/retry", headers=headers
                )
                if res.status_code == 200:
                    await self.fetch_failed_events()
                    return rx.toast("Retry scheduled")
                return rx.toast(f"Error: {res.status_code}")
        except Exception as e:
            return rx.toast(f"Error retrying event: {str(e)}")
