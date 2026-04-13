"""
Tests for Phase 5C: Event Bus, Activity Manager, and Scheduler.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time as dt_time

import pytest

from api.tasks.event_bus import EventBus, BusEvent, EventType, EVENTS_LOG_PATH
from api.tasks.activity_manager import (
    AgentActivityManager,
    AgentActivity,
    ActivitySnapshot,
    ACTIVITY_PATH,
)


# ─────────────────────────────────────────────────────────────
# Event Bus Tests
# ─────────────────────────────────────────────────────────────

class TestEventBus:
    def setup_method(self):
        """Fresh bus per test."""
        self.bus = EventBus()

    @pytest.mark.asyncio
    async def test_publish_and_subscribe(self):
        received = []

        async def handler(event: BusEvent):
            received.append(event)

        self.bus.subscribe(EventType.SCAN_COMPLETED, handler)
        await self.bus.publish(BusEvent(
            type=EventType.SCAN_COMPLETED,
            payload={"count": 5},
            source="test",
        ))

        # Give the task a moment to run
        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].payload["count"] == 5

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        counter = {"a": 0, "b": 0}

        async def handler_a(event: BusEvent):
            counter["a"] += 1

        async def handler_b(event: BusEvent):
            counter["b"] += 1

        self.bus.subscribe(EventType.PHASE_STARTED, handler_a)
        self.bus.subscribe(EventType.PHASE_STARTED, handler_b)

        await self.bus.publish(BusEvent(type=EventType.PHASE_STARTED, source="test"))
        await asyncio.sleep(0.1)

        assert counter["a"] == 1
        assert counter["b"] == 1

    @pytest.mark.asyncio
    async def test_handler_error_isolation(self):
        """A failing handler should not crash the bus or other handlers."""
        success = {"called": False}

        async def bad_handler(event: BusEvent):
            raise ValueError("boom")

        async def good_handler(event: BusEvent):
            success["called"] = True

        self.bus.subscribe(EventType.ERROR, bad_handler)
        self.bus.subscribe(EventType.ERROR, good_handler)

        await self.bus.publish(BusEvent(type=EventType.ERROR, source="test"))
        await asyncio.sleep(0.1)

        assert success["called"] is True

    @pytest.mark.asyncio
    async def test_get_recent(self):
        for i in range(5):
            await self.bus.publish(BusEvent(
                type=EventType.HEALTH_CHECK,
                payload={"i": i},
                source="test",
            ))

        recent = self.bus.get_recent(event_type=EventType.HEALTH_CHECK, limit=3)
        assert len(recent) == 3
        assert recent[-1].payload["i"] == 4

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        counter = {"count": 0}

        async def handler(event: BusEvent):
            counter["count"] += 1

        self.bus.subscribe(EventType.SCAN_STARTED, handler)
        self.bus.unsubscribe(EventType.SCAN_STARTED, handler)

        await self.bus.publish(BusEvent(type=EventType.SCAN_STARTED, source="test"))
        await asyncio.sleep(0.1)

        assert counter["count"] == 0

    def test_event_types_enum(self):
        """Ensure critical event types exist."""
        assert EventType.SCAN_STARTED.value == "scan_started"
        assert EventType.REGIME_CHANGE.value == "regime_change"
        assert EventType.ORDER_PLACED.value == "order_placed"
        assert EventType.APPROVAL_REQUESTED.value == "approval_requested"


# ─────────────────────────────────────────────────────────────
# Activity Manager Tests
# ─────────────────────────────────────────────────────────────

class TestActivityManager:
    def setup_method(self):
        self.manager = AgentActivityManager()

    @pytest.mark.asyncio
    async def test_start_and_complete_activity(self):
        await self.manager.start_activity("ScorerAgent", "Scoring RELIANCE")

        status = self.manager.get_agent_status("ScorerAgent")
        assert status is not None
        assert status.status == "running"
        assert status.current_task == "Scoring RELIANCE"

        await self.manager.complete_activity("ScorerAgent")

        status = self.manager.get_agent_status("ScorerAgent")
        assert status.status == "completed"

    @pytest.mark.asyncio
    async def test_error_activity(self):
        await self.manager.start_activity("FilterAgent", "Filtering stocks")
        await self.manager.error_activity("FilterAgent", "Connection timeout")

        status = self.manager.get_agent_status("FilterAgent")
        assert status.status == "error"
        assert "timeout" in status.last_error

    @pytest.mark.asyncio
    async def test_update_progress(self):
        await self.manager.start_activity("Pipeline", "Research scan")
        await self.manager.update_progress("Pipeline", "3/10 stocks scored")

        status = self.manager.get_agent_status("Pipeline")
        assert status.progress == "3/10 stocks scored"

    @pytest.mark.asyncio
    async def test_scheduler_phase(self):
        await self.manager.set_scheduler_phase("market_hours")

        snapshot = self.manager.get_snapshot()
        assert snapshot.scheduler_phase == "market_hours"

    def test_snapshot_structure(self):
        snapshot = self.manager.get_snapshot()
        assert isinstance(snapshot, ActivitySnapshot)
        assert isinstance(snapshot.agents, dict)

    def test_unknown_agent(self):
        status = self.manager.get_agent_status("NonExistentAgent")
        assert status is None


# ─────────────────────────────────────────────────────────────
# Scheduler Phase Detection Tests
# ─────────────────────────────────────────────────────────────

class TestSchedulerPhases:
    """Test the phase detection logic (no actual scheduling)."""

    def test_phase_detection(self):
        from api.tasks.scheduler import TradingScheduler
        sched = TradingScheduler()

        assert sched._get_current_phase(dt_time(3, 0)) == "overnight_monitoring"
        assert sched._get_current_phase(dt_time(7, 0)) == "pre_market_prep"
        assert sched._get_current_phase(dt_time(10, 0)) == "market_hours"
        assert sched._get_current_phase(dt_time(16, 0)) == "post_market"
        assert sched._get_current_phase(dt_time(19, 0)) == "evening_research"
        assert sched._get_current_phase(dt_time(21, 30)) == "wind_down"
        assert sched._get_current_phase(dt_time(23, 0)) == "overnight_monitoring"

    def test_scheduler_init(self):
        from api.tasks.scheduler import TradingScheduler
        sched = TradingScheduler()
        assert sched.is_running is False
        assert sched.current_phase == "initializing"

    def test_schedule_info(self):
        from api.tasks.scheduler import TradingScheduler
        sched = TradingScheduler()
        info = sched.get_schedule_info()
        assert info["is_running"] is False
        assert "current_phase" in info
