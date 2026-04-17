"""
Event Bus — Lightweight async pub/sub for inter-agent communication.

Provides:
- Typed events (SchedulerEvent, TradeEvent, AlertEvent, etc.)
- Async handler registration
- Event history for recovery after restarts
- Fire-and-forget semantics (handlers run as tasks, don't block publisher)
- Failed event persistence + auto-retry with exponential backoff
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field

from paths import CONTEXT_DIR


# ─────────────────────────────────────────────────────────────
# Event Types
# ─────────────────────────────────────────────────────────────


class EventType(str, Enum):
    # Scheduler lifecycle
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"

    # Research pipeline
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"
    STOCK_SCORED = "stock_scored"
    SHORTLIST_READY = "shortlist_ready"

    # Execution
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    STOP_TRAILED = "stop_trailed"
    POSITION_CLOSED = "position_closed"
    GTT_ALERT = "gtt_alert"

    # Market events (reactive)
    REGIME_CHANGE = "regime_change"
    NEWS_BREAK = "news_break"
    PRICE_ALERT = "price_alert"
    VIX_SPIKE = "vix_spike"
    STOP_HIT = "stop_hit"
    TARGET_HIT = "target_hit"
    AUTH_EXPIRING = "auth_expiring"

    # System
    HEALTH_CHECK = "health_check"
    ERROR = "error"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"


class BusEvent(BaseModel):
    """A single event on the bus."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "system"


class FailedEvent(BaseModel):
    """An event whose handler(s) failed."""

    event: BusEvent
    handler_name: str
    error: str
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = Field(default_factory=datetime.now)
    last_retry_at: datetime | None = None
    permanently_failed: bool = False


# ─────────────────────────────────────────────────────────────
# Event Bus
# ─────────────────────────────────────────────────────────────

# Type alias for handlers
HandlerFn = Callable[[BusEvent], Coroutine[Any, Any, None]]

EVENTS_LOG_PATH = CONTEXT_DIR / "event_log.jsonl"
FAILED_EVENTS_PATH = CONTEXT_DIR / "failed_events.json"

# Retry backoff: 5s, 25s, 125s (5^1, 5^2, 5^3)
RETRY_BASE_SECONDS = 5
RETRY_MULTIPLIER = 5


class EventBus:
    """
    Async event bus with persistent event log and failed event recovery.

    Usage:
        bus = EventBus()
        bus.subscribe(EventType.SCAN_COMPLETED, my_handler)
        await bus.publish(BusEvent(type=EventType.SCAN_COMPLETED, payload={...}))
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[HandlerFn]] = {}
        self._history: list[BusEvent] = []
        self._failed_events: list[FailedEvent] = []
        self._max_history = 500

    def subscribe(self, event_type: EventType, handler: HandlerFn) -> None:
        """Register a handler for an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: HandlerFn) -> None:
        """Remove a handler."""
        if event_type in self._handlers:
            self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]

    async def publish(self, event: BusEvent) -> None:
        """
        Publish an event. All handlers run as fire-and-forget tasks.
        Event is persisted to disk for crash recovery.
        """
        # Persist to event log
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
        self._persist_event(event)

        # Dispatch to handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            asyncio.create_task(self._safe_call(handler, event))

    async def _safe_call(self, handler: HandlerFn, event: BusEvent) -> None:
        """Call a handler with error isolation. On failure, persist as failed event."""
        try:
            await handler(event)
        except Exception as e:
            print(f"EventBus: handler {handler.__name__} failed for {event.type}: {e}")
            failed = FailedEvent(
                event=event,
                handler_name=handler.__name__,
                error=str(e),
            )
            self._failed_events.append(failed)
            self._persist_failed_events()
            # Schedule auto-retry
            asyncio.create_task(self._auto_retry(failed, handler))

    async def _auto_retry(self, failed: FailedEvent, handler: HandlerFn) -> None:
        """Auto-retry a failed event with exponential backoff."""
        while failed.retry_count < failed.max_retries and not failed.permanently_failed:
            failed.retry_count += 1
            delay = RETRY_BASE_SECONDS * (RETRY_MULTIPLIER ** (failed.retry_count - 1))
            print(
                f"EventBus: retry #{failed.retry_count} for {failed.handler_name} "
                f"in {delay}s (event: {failed.event.type})"
            )
            await asyncio.sleep(delay)

            try:
                await handler(failed.event)
                # Success — remove from failed list
                print(f"EventBus: retry #{failed.retry_count} succeeded for {failed.handler_name}")
                self._failed_events = [f for f in self._failed_events if f is not failed]
                self._persist_failed_events()
                return
            except Exception as e:
                failed.error = str(e)
                failed.last_retry_at = datetime.now()
                self._persist_failed_events()

        # All retries exhausted — mark permanently failed
        if not failed.permanently_failed:
            failed.permanently_failed = True
            self._persist_failed_events()
            print(
                f"EventBus: PERMANENTLY FAILED — {failed.handler_name} for "
                f"{failed.event.type} after {failed.max_retries} retries"
            )
            # Try to send Telegram alert
            await self._alert_permanent_failure(failed)

    async def _alert_permanent_failure(self, failed: FailedEvent) -> None:
        """Send Telegram alert for permanently failed events."""
        try:
            from notifications.telegram_client import TelegramClient

            tg = TelegramClient()
            count = sum(1 for f in self._failed_events if f.permanently_failed)
            await tg.send_briefing(
                f"⚠️ {count} event(s) permanently failed after retries.",
                f"Latest: {failed.handler_name} → {failed.event.type}",
                f"Error: {failed.error}",
                "📊 Check dashboard for details.",
            )
        except Exception as e:
            print(f"EventBus: failed to send Telegram alert: {e}")

    def _persist_event(self, event: BusEvent) -> None:
        """Append event to JSONL log file."""
        try:
            EVENTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with EVENTS_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as e:
            print(f"EventBus: failed to persist event: {e}")

    def _persist_failed_events(self) -> None:
        """Persist failed events to JSON file."""
        try:
            FAILED_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = [fe.model_dump(mode="json") for fe in self._failed_events]
            FAILED_EVENTS_PATH.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            print(f"EventBus: failed to persist failed events: {e}")

    def _reload_history_from_disk(self) -> None:
        self._history = []
        if not EVENTS_LOG_PATH.exists():
            return
        try:
            lines = EVENTS_LOG_PATH.read_text().strip().split("\n")
            for line in lines[-self._max_history :]:
                if line.strip():
                    self._history.append(BusEvent.model_validate_json(line))
        except Exception as e:
            print(f"EventBus: failed to reload history: {e}")

    def _reload_failed_events_from_disk(self) -> None:
        if not FAILED_EVENTS_PATH.exists():
            self._failed_events = []
            return
        try:
            data = json.loads(FAILED_EVENTS_PATH.read_text())
            self._failed_events = [FailedEvent.model_validate(fe) for fe in data]
        except Exception as e:
            print(f"EventBus: failed to reload failed events: {e}")

    def get_recent(
        self,
        event_type: EventType | None = None,
        limit: int = 20,
        *,
        refresh_from_disk: bool = False,
    ) -> list[BusEvent]:
        """Get recent events, optionally filtered by type."""
        if refresh_from_disk:
            self._reload_history_from_disk()
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def get_failed_events(self, *, refresh_from_disk: bool = False) -> list[FailedEvent]:
        """Get all failed events."""
        if refresh_from_disk:
            self._reload_failed_events_from_disk()
        return list(self._failed_events)

    def retry_failed_event_by_handler(self, handler_name: str, event_id: str) -> bool:
        """Legacy helper: retry a failed event by handler name and event id."""
        for failed in self._failed_events:
            if failed.event.id != event_id or failed.handler_name != handler_name:
                continue
            handlers = self._handlers.get(failed.event.type, [])
            target = next((handler for handler in handlers if handler.__name__ == handler_name), None)
            if target is not None:
                if failed.permanently_failed:
                    failed.permanently_failed = False
                    failed.retry_count = 0
                    failed.last_retry_at = None
                asyncio.create_task(self._auto_retry(failed, target))
                return True
        return False

    def get_permanently_failed(self, *, refresh_from_disk: bool = False) -> list[FailedEvent]:
        """Get only permanently failed events (for dashboard alert banner)."""
        if refresh_from_disk:
            self._reload_failed_events_from_disk()
        return [f for f in self._failed_events if f.permanently_failed]

    async def retry_failed_event(self, event_id: str) -> bool:
        """Manual retry of a failed event from the dashboard."""
        for failed in self._failed_events:
            if failed.event.id == event_id:
                handlers = self._handlers.get(failed.event.type, [])
                target = [h for h in handlers if h.__name__ == failed.handler_name]
                if target:
                    failed.permanently_failed = False
                    failed.retry_count = 0
                    failed.last_retry_at = None
                    self._persist_failed_events()
                    asyncio.create_task(self._auto_retry(failed, target[0]))
                    return True
                self._failed_events = [f for f in self._failed_events if f is not failed]
                self._persist_failed_events()
                return True
        return False

    def load_history(self) -> None:
        """Load event history from disk on startup."""
        self._reload_history_from_disk()

    def load_failed_events(self) -> int:
        """Load failed events from disk on startup. Returns count loaded."""
        self._reload_failed_events_from_disk()
        return len(self._failed_events)

    async def startup_recovery(self) -> None:
        """On startup: load failed events + send Telegram alert if any."""
        self.load_history()
        count = self.load_failed_events()
        if count > 0:
            perm_count = len(self.get_permanently_failed())
            print(f"EventBus: recovered {count} failed events ({perm_count} permanent)")
            try:
                from notifications.telegram_client import TelegramClient

                tg = TelegramClient()
                await tg.send_briefing(
                    f"⚠️ {count} failed event(s) recovered from previous session.",
                    f"{perm_count} permanently failed.",
                    "📊 Check Agent Activity in dashboard.",
                )
            except Exception as e:
                print(f"EventBus: failed to send recovery alert: {e}")


# Singleton
event_bus = EventBus()
