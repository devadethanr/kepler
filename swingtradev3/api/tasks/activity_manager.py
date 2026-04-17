"""
Agent Activity Manager — Tracks what each agent/pipeline is doing in real-time.

Provides:
- Start/stop tracking for named activities
- Current activity snapshot for the dashboard
- Activity history for debugging
- Thread-safe operations via asyncio.Lock
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from paths import CONTEXT_DIR
from storage import read_json, write_json
from api.sse_broadcaster import broadcaster


ACTIVITY_PATH = CONTEXT_DIR / "agent_activity.json"


class AgentActivity(BaseModel):
    """A single agent's current activity."""
    agent_name: str
    status: str = "idle"  # "idle", "running", "completed", "error"
    current_task: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress: str | None = None
    last_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivitySnapshot(BaseModel):
    """Full snapshot of all agent activities."""
    agents: dict[str, AgentActivity] = Field(default_factory=dict)
    scheduler_phase: str = "unknown"
    last_updated: datetime = Field(default_factory=datetime.now)


class AgentActivityManager:
    """
    Tracks what each agent is doing. Used by:
    - Scheduler: to report current phase
    - Pipeline agents: to report individual progress
    - Dashboard: to show real-time status
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._snapshot = ActivitySnapshot()
        self._load()

    def _load(self) -> None:
        """Load persisted snapshot."""
        data = read_json(ACTIVITY_PATH, None)
        if data:
            try:
                self._snapshot = ActivitySnapshot.model_validate(data)
            except Exception:
                self._snapshot = ActivitySnapshot()

    def _persist(self) -> None:
        """Persist snapshot to disk."""
        self._snapshot.last_updated = datetime.now()
        write_json(ACTIVITY_PATH, self._snapshot.model_dump(mode="json"))

    async def start_activity(
        self,
        agent_name: str,
        task: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mark an agent as running a task."""
        async with self._lock:
            self._snapshot.agents[agent_name] = AgentActivity(
                agent_name=agent_name,
                status="running",
                current_task=task,
                started_at=datetime.now(),
                metadata=metadata or {},
            )
            self._persist()
            await broadcaster.broadcast("agent_activity", self._snapshot.agents[agent_name].model_dump(mode="json"))

    async def update_progress(self, agent_name: str, progress: str) -> None:
        """Update progress for a running agent."""
        async with self._lock:
            if agent_name in self._snapshot.agents:
                self._snapshot.agents[agent_name].progress = progress
                self._persist()
                await broadcaster.broadcast("agent_activity", self._snapshot.agents[agent_name].model_dump(mode="json"))

    async def complete_activity(
        self,
        agent_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mark an agent as completed."""
        async with self._lock:
            if agent_name in self._snapshot.agents:
                agent = self._snapshot.agents[agent_name]
                agent.status = "completed"
                agent.completed_at = datetime.now()
                if metadata:
                    agent.metadata.update(metadata)
                self._persist()
                await broadcaster.broadcast("agent_activity", self._snapshot.agents[agent_name].model_dump(mode="json"))

    async def error_activity(self, agent_name: str, error: str) -> None:
        """Mark an agent as errored."""
        async with self._lock:
            if agent_name in self._snapshot.agents:
                self._snapshot.agents[agent_name].status = "error"
                self._snapshot.agents[agent_name].last_error = error
                self._snapshot.agents[agent_name].completed_at = datetime.now()
            else:
                self._snapshot.agents[agent_name] = AgentActivity(
                    agent_name=agent_name,
                    status="error",
                    last_error=error,
                    completed_at=datetime.now(),
                )
            self._persist()
            await broadcaster.broadcast("agent_activity", self._snapshot.agents[agent_name].model_dump(mode="json"))

    async def set_scheduler_phase(self, phase: str) -> None:
        """Update the current scheduler phase."""
        async with self._lock:
            self._snapshot.scheduler_phase = phase
            self._persist()
            await broadcaster.broadcast("scheduler_phase", {"phase": phase})

    def get_snapshot(self) -> ActivitySnapshot:
        """Get current activity snapshot (non-async for API routes)."""
        self._load()
        return self._snapshot

    def get_agent_status(self, agent_name: str) -> AgentActivity | None:
        """Get a specific agent's status."""
        self._load()
        return self._snapshot.agents.get(agent_name)


# Singleton
activity_manager = AgentActivityManager()
