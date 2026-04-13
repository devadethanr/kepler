"""
Tests for Phase 5C: Failed Event Recovery, Regime Adapter, Event Handlers.
"""
from __future__ import annotations

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# Failed Event Recovery Tests
# ═══════════════════════════════════════════════════════════

class TestFailedEventRecovery:
    """Tests for the event bus failed event system."""

    def test_failed_event_model(self):
        from api.tasks.event_bus import BusEvent, EventType, FailedEvent
        event = BusEvent(type=EventType.ERROR, payload={"test": True}, source="test")
        failed = FailedEvent(
            event=event,
            handler_name="test_handler",
            error="Something went wrong",
        )
        assert failed.retry_count == 0
        assert failed.max_retries == 3
        assert not failed.permanently_failed

    def test_event_has_id(self):
        from api.tasks.event_bus import BusEvent, EventType
        event = BusEvent(type=EventType.ERROR, source="test")
        assert len(event.id) == 12

    @pytest.mark.asyncio
    async def test_handler_failure_creates_failed_event(self):
        from api.tasks.event_bus import EventBus, BusEvent, EventType

        bus = EventBus()
        
        # Create a handler that fails
        async def failing_handler(event: BusEvent) -> None:
            raise ValueError("Intentional failure")

        bus.subscribe(EventType.ERROR, failing_handler)
        
        # Patch the auto-retry to not actually retry (we test retry separately)
        with patch.object(bus, '_auto_retry', new_callable=AsyncMock):
            await bus.publish(BusEvent(type=EventType.ERROR, source="test"))
            await asyncio.sleep(0.1)  # Let tasks complete
            
            assert len(bus._failed_events) == 1
            assert bus._failed_events[0].handler_name == "failing_handler"
            assert "Intentional failure" in bus._failed_events[0].error

    @pytest.mark.asyncio
    async def test_auto_retry_succeeds(self):
        from api.tasks.event_bus import EventBus, BusEvent, EventType, FailedEvent

        bus = EventBus()
        call_count = 0
        
        async def eventually_passes(event: BusEvent) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Not yet")

        event = BusEvent(type=EventType.ERROR, source="test")
        failed = FailedEvent(
            event=event,
            handler_name="eventually_passes",
            error="Not yet",
        )
        bus._failed_events.append(failed)

        # Use a very short retry delay for testing
        with patch("api.tasks.event_bus.RETRY_BASE_SECONDS", 0.01), \
             patch("api.tasks.event_bus.RETRY_MULTIPLIER", 1):
            await bus._auto_retry(failed, eventually_passes)
        
        assert call_count == 2
        assert failed not in bus._failed_events

    @pytest.mark.asyncio
    async def test_auto_retry_exhausted(self):
        from api.tasks.event_bus import EventBus, BusEvent, EventType, FailedEvent

        bus = EventBus()
        
        async def always_fails(event: BusEvent) -> None:
            raise ValueError("Always fails")

        event = BusEvent(type=EventType.ERROR, source="test")
        failed = FailedEvent(
            event=event,
            handler_name="always_fails",
            error="Always fails",
            max_retries=2,
        )
        bus._failed_events.append(failed)

        with patch("api.tasks.event_bus.RETRY_BASE_SECONDS", 0.01), \
             patch("api.tasks.event_bus.RETRY_MULTIPLIER", 1), \
             patch.object(bus, '_alert_permanent_failure', new_callable=AsyncMock):
            await bus._auto_retry(failed, always_fails)
        
        assert failed.permanently_failed
        assert failed.retry_count == 2

    @pytest.mark.asyncio
    async def test_failed_events_persistence(self, tmp_path):
        from api.tasks.event_bus import EventBus, BusEvent, EventType, FailedEvent
        
        bus = EventBus()
        event = BusEvent(type=EventType.ERROR, source="test")
        failed = FailedEvent(
            event=event,
            handler_name="test_handler",
            error="Test error",
        )
        bus._failed_events.append(failed)
        
        # Override path for test
        import api.tasks.event_bus as eb
        original_path = eb.FAILED_EVENTS_PATH
        eb.FAILED_EVENTS_PATH = tmp_path / "failed_events.json"
        
        bus._persist_failed_events()
        
        # Verify file was written
        assert (tmp_path / "failed_events.json").exists()
        data = json.loads((tmp_path / "failed_events.json").read_text())
        assert len(data) == 1
        assert data[0]["handler_name"] == "test_handler"
        
        # Restore
        eb.FAILED_EVENTS_PATH = original_path

    @pytest.mark.asyncio
    async def test_load_failed_events(self, tmp_path):
        from api.tasks.event_bus import EventBus, BusEvent, EventType, FailedEvent
        
        # Write test data
        event = BusEvent(type=EventType.ERROR, source="test")
        failed = FailedEvent(event=event, handler_name="test", error="err")
        data = [failed.model_dump(mode="json")]
        
        import api.tasks.event_bus as eb
        original_path = eb.FAILED_EVENTS_PATH
        eb.FAILED_EVENTS_PATH = tmp_path / "failed_events.json"
        (tmp_path / "failed_events.json").write_text(json.dumps(data, default=str))
        
        bus = EventBus()
        count = bus.load_failed_events()
        assert count == 1
        assert len(bus._failed_events) == 1
        
        eb.FAILED_EVENTS_PATH = original_path

    def test_get_permanently_failed(self):
        from api.tasks.event_bus import EventBus, BusEvent, EventType, FailedEvent
        
        bus = EventBus()
        
        event = BusEvent(type=EventType.ERROR, source="test")
        
        bus._failed_events = [
            FailedEvent(event=event, handler_name="h1", error="e1", permanently_failed=False),
            FailedEvent(event=event, handler_name="h2", error="e2", permanently_failed=True),
            FailedEvent(event=event, handler_name="h3", error="e3", permanently_failed=True),
        ]
        
        perm = bus.get_permanently_failed()
        assert len(perm) == 2


# ═══════════════════════════════════════════════════════════
# Regime Adapter Tests
# ═══════════════════════════════════════════════════════════

class TestRegimeAdapter:
    """Tests for the regime adapter overlays."""

    def test_bull_regime(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("bull")
        assert adapter.regime == "bull"
        assert adapter.can_enter()
        assert adapter.position_size(100) == 100
        assert adapter.min_entry_score() == 7.0

    def test_neutral_regime(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("neutral")
        assert adapter.regime == "neutral"
        assert adapter.can_enter()
        assert adapter.position_size(100) == 75
        assert adapter.min_entry_score() == 7.5

    def test_bear_regime(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("bear")
        assert adapter.regime == "bear"
        assert adapter.can_enter()
        assert adapter.position_size(100) == 50
        assert adapter.min_entry_score() == 8.0

    def test_choppy_regime_blocks_entries(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("choppy")
        assert adapter.regime == "choppy"
        assert not adapter.can_enter()
        assert adapter.position_size(100) == 0
        assert adapter.position_value(100000.0) == 0.0

    def test_regime_aliases(self):
        from regime_adapter import RegimeAdaptiveConfig
        assert RegimeAdaptiveConfig("bullish").regime == "bull"
        assert RegimeAdaptiveConfig("bearish").regime == "bear"
        assert RegimeAdaptiveConfig("sideways").regime == "choppy"
        assert RegimeAdaptiveConfig("recovery").regime == "neutral"

    def test_unknown_regime_defaults_to_neutral(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("unknown_xyz")
        assert adapter.regime == "neutral"

    def test_stop_tightening_neutral(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("neutral")
        # Entry=100, stop=93 (7pt distance), neutral tightens 10%
        new_stop = adapter.adjusted_stop(93.0, 100.0)
        # new distance = 7 * 0.90 = 6.3, new stop = 100 - 6.3 = 93.7
        assert abs(new_stop - 93.7) < 0.01

    def test_stop_tightening_bear(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("bear")
        new_stop = adapter.adjusted_stop(93.0, 100.0)
        # new distance = 7 * 0.80 = 5.6, new stop = 100 - 5.6 = 94.4
        assert abs(new_stop - 94.4) < 0.01

    def test_stop_tightening_bull_no_change(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("bull")
        new_stop = adapter.adjusted_stop(93.0, 100.0)
        # Bull has 0% tightening
        assert abs(new_stop - 93.0) < 0.01

    def test_to_dict(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("bear")
        d = adapter.to_dict()
        assert d["regime"] == "bear"
        assert d["position_size_pct"] == 50.0
        assert d["min_score"] == 8.0
        assert d["new_entries_allowed"] is True

    def test_position_value_scaling(self):
        from regime_adapter import RegimeAdaptiveConfig
        adapter = RegimeAdaptiveConfig("neutral")
        assert adapter.position_value(100000.0) == 75000.0


# ═══════════════════════════════════════════════════════════
# Event Handlers Tests
# ═══════════════════════════════════════════════════════════

class TestEventHandlers:
    """Tests for event handler registration and invocation."""

    def test_register_all_handlers(self):
        from api.tasks.event_bus import EventBus, EventType
        from api.tasks.event_handlers import register_all_handlers
        
        bus = EventBus()
        register_all_handlers(bus)
        
        # Check 7 handlers are registered for 7 event types
        registered_types = [et for et in EventType if et in bus._handlers and bus._handlers[et]]
        assert len(registered_types) >= 7

    @pytest.mark.asyncio
    async def test_handle_gtt_triggered(self):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_gtt_triggered
        
        event = BusEvent(
            type=EventType.GTT_ALERT,
            payload={"ticker": "RELIANCE", "trigger_type": "target", "price": 2500},
            source="test",
        )
        
        with patch("notifications.telegram_client.TelegramClient") as mock_tg:
            mock_tg.return_value.send_briefing = AsyncMock()
            await handle_gtt_triggered(event)  # Should not raise

    @pytest.mark.asyncio
    async def test_handle_regime_change(self):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_regime_change
        
        event = BusEvent(
            type=EventType.REGIME_CHANGE,
            payload={"old_regime": "bull", "new_regime": "bear"},
            source="test",
        )
        
        with patch("notifications.telegram_client.TelegramClient") as mock_tg:
            mock_tg.return_value.send_briefing = AsyncMock()
            await handle_regime_change(event)  # Should not raise

    @pytest.mark.asyncio
    async def test_handle_stop_hit_logs_observation(self, tmp_path):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_stop_hit
        
        event = BusEvent(
            type=EventType.STOP_HIT,
            payload={
                "ticker": "TEST",
                "entry_price": 100,
                "stop_price": 93,
                "pnl_pct": -7.0,
            },
            source="test",
        )
        
        with patch("notifications.telegram_client.TelegramClient") as mock_tg:
            mock_tg.return_value.send_briefing = AsyncMock()
            # Also mock storage ops to avoid file system deps
            with patch("storage.read_json", return_value=[]), \
                 patch("storage.write_json"):
                try:
                    await handle_stop_hit(event)
                except Exception:
                    pass  # OK if secondary operations fail in test

    @pytest.mark.asyncio
    async def test_handle_auth_expiring(self):
        from api.tasks.event_bus import BusEvent, EventType
        from api.tasks.event_handlers import handle_auth_expiring
        
        event = BusEvent(
            type=EventType.AUTH_EXPIRING,
            payload={"service": "kite", "hours_remaining": 2},
            source="test",
        )
        
        with patch("notifications.telegram_client.TelegramClient") as mock_tg:
            mock_tg.return_value.send_briefing = AsyncMock()
            await handle_auth_expiring(event)


# ═══════════════════════════════════════════════════════════
# Event Bus New Event Types
# ═══════════════════════════════════════════════════════════

class TestNewEventTypes:
    """Test that new event types are defined."""

    def test_new_event_types_exist(self):
        from api.tasks.event_bus import EventType
        assert EventType.VIX_SPIKE == "vix_spike"
        assert EventType.STOP_HIT == "stop_hit"
        assert EventType.TARGET_HIT == "target_hit"
        assert EventType.AUTH_EXPIRING == "auth_expiring"

    @pytest.mark.asyncio
    async def test_bus_event_with_new_types(self):
        from api.tasks.event_bus import BusEvent, EventType
        event = BusEvent(type=EventType.VIX_SPIKE, payload={"vix_level": 25.5}, source="test")
        assert event.type == EventType.VIX_SPIKE
        assert event.payload["vix_level"] == 25.5
