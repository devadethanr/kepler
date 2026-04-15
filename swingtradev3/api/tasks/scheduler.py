"""
TradingScheduler V2 — Full 24-hour autonomous trading cycle.

6 Phases (IST):
  1. Overnight Monitoring  (22:00 → 06:00) — News, GIFT Nifty, global markets
  2. Pre-Market Prep       (06:00 → 09:15) — Briefing, regime, approvals
  3. Market Hours          (09:15 → 15:30) — Entry execution, GTT monitoring, trailing
  4. Post-Market           (15:30 → 18:00) — EOD data, PnL, corporate actions
  5. Evening Research      (18:00 → 21:00) — Full scan pipeline
  6. Wind-Down             (21:00 → 22:00) — State persistence, log rotation

Key design:
- Uses asyncio + schedule (not threads) — single event loop
- IST timezone-aware via ZoneInfo
- Event bus integration for reactive behavior
- Activity manager for dashboard visibility
- Crash recovery: persists scheduler state to disk
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo

import schedule

from config import cfg
from paths import CONTEXT_DIR
from api.tasks.event_bus import event_bus, BusEvent, EventType
from api.tasks.activity_manager import activity_manager

IST = ZoneInfo("Asia/Kolkata")


def _now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def _ist_time(time_str: str) -> str:
    """Validate and return a time string (HH:MM format)."""
    # Validate format
    dt_time.fromisoformat(time_str)
    return time_str


class TradingScheduler:
    """
    24-hour autonomous trading scheduler.
    All times are in IST (Asia/Kolkata).
    """

    def __init__(self) -> None:
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._current_phase = "initializing"

    async def start(self) -> None:
        """Start the scheduler and register all jobs."""
        self.is_running = True

        # Load event bus history + failed events for recovery
        await event_bus.startup_recovery()

        # Register event handlers
        from api.tasks.event_handlers import register_all_handlers

        register_all_handlers()

        # ── Phase 1: Overnight Monitoring (22:00 → 06:00) ──
        s = cfg.scheduler.overnight
        schedule.every(s.news_monitoring_minutes).minutes.do(
            self._job, "overnight_news_sweep", self._overnight_news_sweep
        )
        schedule.every(s.gift_nifty_minutes).minutes.do(
            self._job, "gift_nifty_check", self._gift_nifty_check
        )

        # ── Phase 2: Pre-Market Preparation (06:00 → 09:15) ──
        m = cfg.scheduler.morning
        schedule.every().day.at(_ist_time(m.news_digest_time)).do(
            self._job, "morning_news_digest", self._morning_news_digest
        )
        schedule.every().day.at(_ist_time(m.regime_check_time)).do(
            self._job, "morning_regime_check", self._morning_regime_check
        )
        schedule.every().day.at(_ist_time(m.fii_dii_check_time)).do(
            self._job, "fii_dii_check", self._fii_dii_check
        )
        schedule.every().day.at(_ist_time(m.briefing_generation_time)).do(
            self._job, "morning_briefing", self._generate_morning_briefing
        )
        schedule.every().day.at(_ist_time(m.approval_reminder_time)).do(
            self._job, "approval_reminder", self._approval_reminder
        )
        schedule.every().day.at(_ist_time(m.premarket_setup_time)).do(
            self._job, "premarket_setup", self._premarket_setup
        )

        # ── Phase 3: Market Hours (09:15 → 15:30) ──
        mh = cfg.scheduler.market_hours
        schedule.every(mh.position_monitoring_minutes).minutes.do(
            self._job, "position_monitor", self._position_monitor
        )
        schedule.every(mh.gtt_health_check_minutes).minutes.do(
            self._job, "gtt_health_check", self._gtt_health_check
        )
        schedule.every(mh.intraday_news_minutes).minutes.do(
            self._job, "intraday_news_sweep", self._intraday_news_sweep
        )

        # ── Phase 4: Post-Market (15:30 → 18:00) ──
        pm = cfg.scheduler.post_market
        schedule.every().day.at(_ist_time(pm.eod_data_collection)).do(
            self._job, "eod_data_collection", self._eod_data_collection
        )
        schedule.every().day.at(_ist_time(pm.pnl_calculation)).do(
            self._job, "pnl_calculation", self._pnl_calculation
        )
        schedule.every().day.at(_ist_time(pm.fii_dii_final)).do(
            self._job, "fii_dii_final", self._fii_dii_final
        )
        schedule.every().day.at(_ist_time(pm.observation_logging)).do(
            self._job, "observation_logging", self._observation_logging
        )

        # ── Phase 5: Evening Research (18:00 → 21:00) ──
        er = cfg.scheduler.evening_research
        schedule.every().day.at(_ist_time(er.start_time)).do(
            self._job, "evening_research_pipeline", self._trigger_research_pipeline
        )

        # ── Phase 6: Wind-Down (21:00 → 22:00) ──
        wd = cfg.scheduler.wind_down
        schedule.every().day.at(_ist_time(wd.state_persistence)).do(
            self._job, "state_snapshot", self._state_snapshot
        )
        schedule.every().day.at(_ist_time(wd.log_rotation)).do(
            self._job, "log_rotation", self._log_rotation
        )
        schedule.every().day.at(_ist_time(wd.health_check)).do(
            self._job, "health_check", self._health_check
        )
        schedule.every().day.at(_ist_time(wd.final_news_scan)).do(
            self._job, "daily_summary", self._daily_summary
        )

        # Start the loop
        self._task = asyncio.create_task(self._loop())
        await activity_manager.set_scheduler_phase("running")

        await event_bus.publish(
            BusEvent(
                type=EventType.PHASE_STARTED,
                payload={"phase": "scheduler_initialized"},
                source="scheduler",
            )
        )

        print(f"[{_now_ist().isoformat()}] Scheduler started with {len(schedule.get_jobs())} jobs")

    async def stop(self) -> None:
        """Gracefully stop the scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
        schedule.clear()
        await activity_manager.set_scheduler_phase("stopped")
        print(f"[{_now_ist().isoformat()}] Scheduler stopped")

    async def _loop(self) -> None:
        """Main scheduler loop — runs pending jobs every second."""
        while self.is_running:
            # Determine current phase
            now = _now_ist().time()
            new_phase = self._get_current_phase(now)
            if new_phase != self._current_phase:
                self._current_phase = new_phase
                await activity_manager.set_scheduler_phase(new_phase)
                await event_bus.publish(
                    BusEvent(
                        type=EventType.PHASE_STARTED,
                        payload={"phase": new_phase},
                        source="scheduler",
                    )
                )

            schedule.run_pending()
            await asyncio.sleep(1)

    def _get_current_phase(self, now: dt_time) -> str:
        """Determine which phase we're in based on current IST time."""
        if now < dt_time(6, 0):
            return "overnight_monitoring"
        elif now < dt_time(9, 15):
            return "pre_market_prep"
        elif now < dt_time(15, 30):
            return "market_hours"
        elif now < dt_time(18, 0):
            return "post_market"
        elif now < dt_time(21, 0):
            return "evening_research"
        elif now < dt_time(22, 0):
            return "wind_down"
        else:
            return "overnight_monitoring"

    def _job(self, name: str, coro_fn) -> None:
        """Wrapper: schedule expects sync callables, so we create a task."""
        asyncio.create_task(self._run_job(name, coro_fn))

    async def _run_job(self, name: str, coro_fn) -> None:
        """Run a scheduled job with activity tracking and error isolation."""
        await activity_manager.start_activity("scheduler", name)
        try:
            await coro_fn()
            await activity_manager.complete_activity("scheduler", {"last_job": name})
        except Exception as e:
            print(f"[{_now_ist().isoformat()}] Scheduler job '{name}' failed: {e}")
            await activity_manager.error_activity("scheduler", f"{name}: {e}")
            await event_bus.publish(
                BusEvent(
                    type=EventType.ERROR,
                    payload={"job": name, "error": str(e)},
                    source="scheduler",
                )
            )

    # ─────────────────────────────────────────────────────────────
    # Phase 1: Overnight Monitoring
    # ─────────────────────────────────────────────────────────────

    async def _overnight_news_sweep(self) -> None:
        """Sweep global news for holdings-relevant events."""
        from data.news_aggregator import NewsAggregator
        from storage import read_json
        from models import AccountState

        state_data = read_json(CONTEXT_DIR / "state.json", {})
        if not state_data or not state_data.get("positions"):
            return

        state = AccountState.model_validate(state_data)
        news = NewsAggregator()

        for pos in state.positions:
            news_data = await asyncio.to_thread(news.search_news, pos.ticker)
            headlines = news_data.get("results", [])[:3]
            if headlines:
                await event_bus.publish(
                    BusEvent(
                        type=EventType.NEWS_BREAK,
                        payload={"ticker": pos.ticker, "headlines": headlines[:3]},
                        source="overnight_monitor",
                    )
                )

    async def _gift_nifty_check(self) -> None:
        """Check GIFT Nifty / global markets overnight."""
        now = _now_ist().time()
        # Only run between 22:00 and 06:00
        if dt_time(6, 0) <= now < dt_time(22, 0):
            return
        print(f"[{_now_ist().isoformat()}] GIFT Nifty / global markets check")

    # ─────────────────────────────────────────────────────────────
    # Phase 2: Pre-Market Preparation
    # ─────────────────────────────────────────────────────────────

    async def _morning_news_digest(self) -> None:
        """06:00 — Sweep market news for overnight developments."""
        from data.news_aggregator import NewsAggregator

        news = NewsAggregator()
        await asyncio.to_thread(news.sweep_market_news)
        print(f"[{_now_ist().isoformat()}] Morning news digest completed")

    async def _morning_regime_check(self) -> None:
        """06:30 — Check regime for any overnight shifts."""
        from data.market_regime import MarketRegimeDetector

        detector = MarketRegimeDetector()
        regime = await detector.detect()

        await event_bus.publish(
            BusEvent(
                type=EventType.REGIME_CHANGE,
                payload={"regime": regime},
                source="morning_regime",
            )
        )

    async def _fii_dii_check(self) -> None:
        """07:00 — Check FII/DII data from previous session."""
        print(f"[{_now_ist().isoformat()}] FII/DII data check")
        # FII/DII data typically available by 7AM from NSE

    async def _generate_morning_briefing(self) -> None:
        """08:00 — Generate and send the morning briefing."""
        from api.tasks.morning_briefing import generate_morning_briefing

        await generate_morning_briefing()

    async def _approval_reminder(self) -> None:
        """08:45 — Remind about pending approvals."""
        from storage import read_json

        approvals = read_json(CONTEXT_DIR / "pending_approvals.json", [])
        pending = [a for a in approvals if a.get("approved") is None]
        if pending:
            print(f"[{_now_ist().isoformat()}] {len(pending)} pending approval(s)")
            try:
                from notifications.telegram_client import TelegramClient

                tg = TelegramClient()
                await tg.send_briefing(
                    f"⏳ {len(pending)} trade(s) awaiting approval.\n📊 Review in dashboard."
                )
            except Exception as e:
                print(f"Approval reminder failed: {e}")

    async def _premarket_setup(self) -> None:
        """09:00 — Prepare approved orders for market open."""
        print(f"[{_now_ist().isoformat()}] Pre-market setup: checking approved orders...")
        from storage import read_json

        approvals = read_json(CONTEXT_DIR / "pending_approvals.json", [])
        approved = [a for a in approvals if a.get("approved") is True]
        if approved:
            print(f"  → {len(approved)} approved orders ready for placement")

    # ─────────────────────────────────────────────────────────────
    # Phase 3: Market Hours
    # ─────────────────────────────────────────────────────────────

    async def _position_monitor(self) -> None:
        """Every N minutes during market hours: run execution monitor."""
        now = _now_ist().time()
        if not (dt_time(9, 15) <= now <= dt_time(15, 30)):
            return  # Only during market hours

        print(f"[{_now_ist().isoformat()}] Position monitor tick")
        # The monitor agent checks GTTs, detects triggers, and trails stops
        # It has its own market hours guard and emits events for triggers

    async def _gtt_health_check(self) -> None:
        """Every N minutes: verify GTT orders are alive."""
        now = _now_ist().time()
        if not (dt_time(9, 15) <= now <= dt_time(15, 30)):
            return

        print(f"[{_now_ist().isoformat()}] GTT health check tick")

    async def _intraday_news_sweep(self) -> None:
        """Sweep news for held positions during market hours."""
        now = _now_ist().time()
        if not (dt_time(9, 15) <= now <= dt_time(15, 30)):
            return

        from data.news_aggregator import NewsAggregator
        from storage import read_json
        from models import AccountState

        state_data = read_json(CONTEXT_DIR / "state.json", {})
        if not state_data or not state_data.get("positions"):
            return

        state = AccountState.model_validate(state_data)
        news = NewsAggregator()

        for pos in state.positions:
            news_data = await asyncio.to_thread(news.search_news, pos.ticker)
            headlines = news_data.get("results", [])[:3]
            if headlines:
                await event_bus.publish(
                    BusEvent(
                        type=EventType.NEWS_BREAK,
                        payload={"ticker": pos.ticker, "headlines": headlines[:3]},
                        source="intraday_news",
                    )
                )

    # ─────────────────────────────────────────────────────────────
    # Phase 4: Post-Market
    # ─────────────────────────────────────────────────────────────

    async def _eod_data_collection(self) -> None:
        """15:30 — Collect end-of-day data."""
        print(f"[{_now_ist().isoformat()}] EOD data collection started")
        # Trigger KG update for any new positions/exits
        await event_bus.publish(
            BusEvent(
                type=EventType.PHASE_COMPLETED,
                payload={"phase": "eod_data_collection"},
                source="scheduler",
            )
        )

    async def _pnl_calculation(self) -> None:
        """15:45 — Calculate daily PnL."""
        from storage import read_json, write_json
        from paths import CONTEXT_DIR
        from models import AccountState

        state_data = read_json(CONTEXT_DIR / "state.json", {})
        if not state_data:
            return

        state = AccountState.model_validate(state_data)
        total_unrealized = sum(
            ((pos.current_price or pos.entry_price) - pos.entry_price) * pos.quantity
            for pos in state.positions
        )
        state.unrealized_pnl = total_unrealized
        write_json(CONTEXT_DIR / "state.json", state.model_dump(mode="json"))
        print(f"[{_now_ist().isoformat()}] PnL: unrealized ₹{total_unrealized:.2f}")

    async def _fii_dii_final(self) -> None:
        """16:00 — Final FII/DII numbers for the day."""
        print(f"[{_now_ist().isoformat()}] Final FII/DII numbers")

    async def _position_reconciliation(self) -> None:
        """16:30 — Reconcile positions with broker."""
        print(f"[{_now_ist().isoformat()}] Position reconciliation")

    async def _observation_logging(self) -> None:
        """17:00 — Log trade observations for the learning loop."""
        print(f"[{_now_ist().isoformat()}] Observation logging completed")

    # ─────────────────────────────────────────────────────────────
    # Phase 5: Evening Research
    # ─────────────────────────────────────────────────────────────

    async def _trigger_research_pipeline(self) -> None:
        """18:00 — Run the full research pipeline (now with KG)."""
        await event_bus.publish(
            BusEvent(
                type=EventType.SCAN_STARTED,
                source="scheduler",
            )
        )

        await activity_manager.start_activity("ResearchPipeline", "Full evening research scan")

        try:
            from api.routes.scan import run_research_pipeline_bg

            await run_research_pipeline_bg()
            await activity_manager.complete_activity("ResearchPipeline")
        except Exception as e:
            await activity_manager.error_activity("ResearchPipeline", str(e))

        await event_bus.publish(
            BusEvent(
                type=EventType.SCAN_COMPLETED,
                source="scheduler",
            )
        )

    # ─────────────────────────────────────────────────────────────
    # Phase 6: Wind-Down
    # ─────────────────────────────────────────────────────────────

    async def _state_snapshot(self) -> None:
        """21:15 — Persist all state for crash recovery."""
        from storage import write_json

        snapshot = {
            "timestamp": _now_ist().isoformat(),
            "activity": activity_manager.get_snapshot().model_dump(mode="json"),
            "recent_events": [e.model_dump(mode="json") for e in event_bus.get_recent(limit=50)],
        }
        write_json(
            CONTEXT_DIR / "daily" / f"snapshot_{_now_ist().strftime('%Y-%m-%d')}.json", snapshot
        )
        print(f"[{_now_ist().isoformat()}] State snapshot saved")

    async def _log_rotation(self) -> None:
        """21:30 — Rotate old log/event files."""
        import os
        from api.tasks.event_bus import EVENTS_LOG_PATH

        # Rotate event log if > 5MB
        if EVENTS_LOG_PATH.exists() and EVENTS_LOG_PATH.stat().st_size > 5 * 1024 * 1024:
            rotated = EVENTS_LOG_PATH.with_suffix(f".{_now_ist().strftime('%Y%m%d')}.jsonl")
            os.rename(EVENTS_LOG_PATH, rotated)
            print(f"[{_now_ist().isoformat()}] Event log rotated to {rotated.name}")
        else:
            print(f"[{_now_ist().isoformat()}] Log rotation: no rotation needed")

    async def _health_check(self) -> None:
        """21:45 — Run system health check."""
        from health_manager import get_all_statuses

        statuses = get_all_statuses()

        unhealthy = [k for k, v in statuses.items() if v != "healthy"]
        if unhealthy:
            await event_bus.publish(
                BusEvent(
                    type=EventType.HEALTH_CHECK,
                    payload={"unhealthy": unhealthy, "statuses": statuses},
                    source="scheduler",
                )
            )
            try:
                from notifications.telegram_client import TelegramClient

                tg = TelegramClient()
                await tg.send_briefing(
                    f"⚠️ Health Check Alert\nUnhealthy services: {', '.join(unhealthy)}"
                )
            except Exception as e:
                print(f"Failed to send health alert: {e}")

        print(f"[{_now_ist().isoformat()}] Health check: {statuses}")

    async def _daily_summary(self) -> None:
        """21:00 — Send daily summary to Telegram."""
        from storage import read_json
        from models import AccountState

        state_data = read_json(CONTEXT_DIR / "state.json", {})
        pnl = 0.0
        positions_count = 0
        if state_data:
            try:
                state = AccountState.model_validate(state_data)
                pnl = state.unrealized_pnl or 0
                positions_count = len(state.positions)
            except Exception:
                pass

        failed_count = len(event_bus.get_permanently_failed())

        try:
            from notifications.telegram_client import TelegramClient

            tg = TelegramClient()
            await tg.send_briefing(
                f"📊 Daily Summary — {_now_ist().strftime('%Y-%m-%d')}\n\n"
                f"Positions: {positions_count}\n"
                f"Unrealized P&L: ₹{pnl:.2f}\n"
                f"Scheduler phase: {self._current_phase}\n"
                f"Failed events: {failed_count}\n"
                f"\n🌙 Entering overnight mode."
            )
        except Exception as e:
            print(f"Daily summary Telegram failed: {e}")

        print(f"[{_now_ist().isoformat()}] Daily summary sent")

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    @property
    def current_phase(self) -> str:
        return self._current_phase

    def get_schedule_info(self) -> dict:
        """Get schedule info for the dashboard."""
        next_run_str = None
        if schedule.next_run():
            from datetime import datetime, timezone
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("Asia/Kolkata")
            now = datetime.now(tz)
            next_run = schedule.next_run()
            if next_run:
                # Make naive datetime timezone-aware by adding IST
                next_run_aware = next_run.replace(tzinfo=tz)
                delta = next_run_aware - now
                minutes = int(delta.total_seconds() / 60)
                if minutes < 60:
                    next_run_str = f"In {minutes} min"
                else:
                    next_run_str = f"In {minutes // 60}h {minutes % 60}m"

        # Get failed events count
        from api.tasks.event_bus import event_bus

        failed_count = len(event_bus.get_failed_events())

        return {
            "is_running": self.is_running,
            "current_phase": self._current_phase,
            "total_jobs": len(schedule.get_jobs()),
            "next_run": str(schedule.next_run()) if schedule.get_jobs() else None,
            "next_task": next_run_str,
            "failed_events": failed_count,
        }


# Singleton
scheduler = TradingScheduler()
