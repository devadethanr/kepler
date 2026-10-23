"""
Tests for Phase 5C: Event Bus, Activity Manager, and Scheduler.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time as dt_time
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from api.tasks import event_bus as event_bus_module
from api.tasks.event_bus import EventBus, BusEvent, EventType
from api.tasks.activity_manager import (
    AgentActivityManager,
    ActivitySnapshot,
)


# ─────────────────────────────────────────────────────────────
# Event Bus Tests
# ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_event_bus_runtime_files(tmp_path, monkeypatch):
    monkeypatch.setattr(event_bus_module, "EVENTS_LOG_PATH", tmp_path / "event_log.jsonl")
    monkeypatch.setattr(event_bus_module, "FAILED_EVENTS_PATH", tmp_path / "failed_events.json")


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
        assert EventType.MARKET_NEWS_DIGEST.value == "market_news_digest"
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

    def test_phase_detection_on_non_trading_days(self):
        from api.tasks.scheduler import TradingScheduler

        sched = TradingScheduler()

        assert sched._get_current_phase(dt_time(7, 0), trading_day=False) == "market_closed"
        assert sched._get_current_phase(dt_time(10, 0), trading_day=False) == "market_closed"
        assert sched._get_current_phase(dt_time(16, 0), trading_day=False) == "post_market"
        assert sched._get_current_phase(dt_time(21, 30), trading_day=False) == "wind_down"

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

    @pytest.mark.asyncio
    async def test_overnight_news_sweep_skips_daytime(self, monkeypatch):
        from api.tasks import scheduler as scheduler_module
        from api.tasks.scheduler import TradingScheduler

        sched = TradingScheduler()
        monkeypatch.setattr(
            scheduler_module,
            "_now_ist",
            lambda: datetime(2026, 5, 5, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        )

        await sched._overnight_news_sweep()

    @pytest.mark.asyncio
    async def test_morning_news_digest_publishes_grouped_digest(self, monkeypatch):
        from api.tasks import scheduler as scheduler_module
        from api.tasks.scheduler import TradingScheduler

        published = []

        class FakeNews:
            def sweep_market_news(self):
                return {"query": "market", "results": [{"title": "RBI policy"}]}

            def build_market_digest(self, payload):
                return {
                    "query": payload["query"],
                    "ticker_groups": [],
                    "general": [{"title": "RBI policy", "url": "https://example.com/rbi"}],
                    "item_count": 1,
                    "generated_at_ist": "2026-05-08T06:00:00+05:30",
                }

        async def fake_publish(event):
            published.append(event)

        monkeypatch.setattr("data.news.NewsAggregator", FakeNews)
        monkeypatch.setattr(scheduler_module.event_bus, "publish", fake_publish)

        await TradingScheduler()._morning_news_digest()

        assert len(published) == 1
        assert published[0].type == EventType.MARKET_NEWS_DIGEST
        assert published[0].payload["item_count"] == 1

    @pytest.mark.asyncio
    async def test_observation_logging_runs_pending_trade_reviews(self, monkeypatch):
        from agents.learning.reviewer import TradeReviewerAgent
        from api.tasks.scheduler import TradingScheduler

        review_pending = AsyncMock(return_value={"status": "completed", "reviewed": 2})
        monkeypatch.setattr(TradeReviewerAgent, "review_pending", review_pending)

        await TradingScheduler()._observation_logging()

        review_pending.assert_awaited_once_with()

    @pytest.mark.asyncio
    async def test_monthly_policy_analysis_only_runs_on_configured_day(self, monkeypatch):
        from agents.learning.lesson_agent import LessonAgent
        from api.tasks import scheduler as scheduler_module
        from api.tasks.scheduler import TradingScheduler

        propose = AsyncMock(return_value={"status": "completed", "proposal_count": 0})
        monkeypatch.setattr(LessonAgent, "propose_monthly_overlays", propose)
        monkeypatch.setattr(
            scheduler_module,
            "_now_ist",
            lambda: datetime(
                2026,
                6,
                scheduler_module.cfg.research.analyst_loop.day_of_month,
                18,
                0,
                tzinfo=ZoneInfo("Asia/Kolkata"),
            ),
        )

        await TradingScheduler()._monthly_policy_analysis()

        propose.assert_awaited_once_with()

    def test_morning_briefing_filters_to_pending_latest_approvals(self):
        from api.tasks.morning_briefing import _is_actionable_latest_approval
        from models import PendingApproval

        base = {
            "ticker": "RELIANCE",
            "score": 8.1,
            "setup_type": "breakout",
            "entry_zone": {"low": 1000.0, "high": 1010.0},
            "stop_price": 980.0,
            "target_price": 1080.0,
            "holding_days_expected": 7,
            "confidence_reasoning": "Current setup",
            "risk_flags": [],
            "approved": None,
            "status": "pending",
            "created_at": "2026-05-05T18:00:00",
            "expires_at": "2030-05-06T10:00:00",
            "research_date": "2026-05-05",
        }

        assert _is_actionable_latest_approval(
            PendingApproval.model_validate(base),
            datetime(2026, 5, 5).date(),
        )
        assert not _is_actionable_latest_approval(
            PendingApproval.model_validate({**base, "approved": True, "status": "approved"}),
            datetime(2026, 5, 5).date(),
        )
        assert not _is_actionable_latest_approval(
            PendingApproval.model_validate({**base, "research_date": "2026-05-04"}),
            datetime(2026, 5, 5).date(),
        )
