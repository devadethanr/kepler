from __future__ import annotations

import asyncio
import signal
from contextlib import suppress
from typing import Any

from sqlalchemy import text

from api.tasks.event_bus import event_bus
from api.tasks.scheduler import scheduler
from auth.kite.client import has_kite_session
from broker.kite_stream import KiteBrokerStream
from broker.reducer import BrokerReducer
from config import cfg, runtime_flags
from context_graph.projector import GraphProjector
from context_graph.repository import GraphUnavailableError
from memory.bootstrap import initialize_memory_layer
from memory.db import get_engine

from .operator_controls import (
    list_pending_failed_event_retries,
    list_pending_reconcile_acks,
    mark_failed_event_retry,
    mark_reconcile_ack,
    set_block_new_entries,
    write_worker_status,
)
from .quote_cache import QuoteCache
from .reconciler import Reconciler
from .runtime_context import bind_broker_stream, bind_mutation_lock, bind_quote_cache
from .session_guards import entry_stream_required_for_new_entries
from .state_machine import WorkerExecutionStateMachine


WORKER_ADVISORY_LOCK_ID = 4200217
APPROVAL_POLL_SECONDS = 5
OPERATOR_CONTROL_POLL_SECONDS = 5
WORKER_HEARTBEAT_SECONDS = 5


class WorkerLockUnavailable(RuntimeError):
    pass


class WorkerLease:
    def __init__(self, connection) -> None:
        self._connection = connection

    @classmethod
    def acquire(cls) -> "WorkerLease":
        connection = get_engine().connect()
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": WORKER_ADVISORY_LOCK_ID},
            ).scalar()
        )
        if not acquired:
            connection.close()
            raise WorkerLockUnavailable("worker lock is already held")
        return cls(connection)

    def release(self) -> None:
        with suppress(Exception):
            self._connection.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": WORKER_ADVISORY_LOCK_ID},
            )
        self._connection.close()


class WorkerRuntime:
    def __init__(self) -> None:
        self._lease: WorkerLease | None = None
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task[Any]] = []
        self._execution_lock = asyncio.Lock()
        self._state_machine = WorkerExecutionStateMachine()
        self._broker_reducer = BrokerReducer()
        self._broker_stream = KiteBrokerStream(self._broker_reducer)
        self._quote_cache = QuoteCache(
            broker_stream=self._broker_stream,
            exchange=cfg.trading.exchange,
        )
        self._reconciler = Reconciler(
            broker_reducer=self._broker_reducer,
            broker_stream=self._broker_stream,
            quote_cache=self._quote_cache,
            exchange=cfg.trading.exchange,
        )
        self._reconciler.register_stop_event(self._stop_event)
        self._graph_projector = GraphProjector()
        self._started = False

    async def start(self) -> None:
        initialize_memory_layer()
        self._lease = WorkerLease.acquire()
        bind_mutation_lock(self._execution_lock)
        bind_broker_stream(self._broker_stream)
        bind_quote_cache(self._quote_cache)
        if self._broker_live_enabled() and self._broker_sync_enabled():
            try:
                startup_report = await self._reconciler.run_startup_reconciliation(
                    wait_for_stream_seconds=0.0,
                )
            except Exception as exc:
                if self._lease is not None:
                    self._lease.release()
                    self._lease = None
                raise RuntimeError(f"worker startup reconciliation failed: {exc}") from exc
            tracked_tickers = list(
                startup_report.get("positions", {}).get("tracked_tickers", [])
            )
            self._broker_stream.set_tracked_tickers(
                tracked_tickers,
                exchange=cfg.trading.exchange,
            )
            if not startup_report.get("ready", False):
                set_block_new_entries(
                    reason=str(startup_report.get("reason") or "startup_not_ready"),
                    source="worker_startup",
                    detail={"drift": startup_report.get("drift", {})},
                )
        await self._maintain_broker_stream()
        if self._broker_live_enabled() and self._broker_sync_enabled():
            # G6: second-phase readiness — confirm the WebSocket actually
            # connected within the configured window; flip block_new_entries
            # if it did not.
            try:
                await self._reconciler.run_post_stream_readiness_check(
                    require_stream=entry_stream_required_for_new_entries()
                )
            except Exception as exc:
                print(f"worker post-stream readiness check failed: {exc}")
        else:
            await self._reconciler.relax_runtime_guards_for_non_live(
                source="worker_non_live_startup"
            )
        await scheduler.start()

        # Phase 11: start graph projector (non-blocking, Memgraph optional)
        try:
            self._graph_projector.ensure_schema()
        except GraphUnavailableError:
            print("GraphProjector: schema unavailable — will retry in loop")
        # Always start the loop — it handles Memgraph being down gracefully
        await self._graph_projector.start()

        self._started = True
        await self._write_status()
        self._tasks = [
            asyncio.create_task(self._approval_loop(), name="worker-approval-loop"),
            asyncio.create_task(self._operator_control_loop(), name="worker-operator-control-loop"),
            asyncio.create_task(self._heartbeat_loop(), name="worker-heartbeat-loop"),
        ]
        if self._broker_live_enabled():
            self._tasks.extend(
                [
                    asyncio.create_task(
                        self._reconciler.run_orders_loop(), name="worker-reconcile-orders-loop"
                    ),
                    asyncio.create_task(
                        self._reconciler.run_positions_loop(),
                        name="worker-reconcile-positions-loop",
                    ),
                    asyncio.create_task(
                        self._reconciler.run_gtts_loop(), name="worker-reconcile-gtts-loop"
                    ),
                    asyncio.create_task(
                        self._reconciler.run_quote_freshness_loop(),
                        name="worker-reconcile-quote-loop",
                    ),
                    asyncio.create_task(
                        self._reconciler.run_broker_connection_loop(),
                        name="worker-reconcile-connection-loop",
                    ),
                    asyncio.create_task(
                        self._reconciler.run_daily_loss_loop(),
                        name="worker-reconcile-daily-loss-loop",
                    ),
                ]
            )
        elif self._broker_stream_enabled():
            self._tasks.append(
                asyncio.create_task(
                    self._reconciler.run_quote_freshness_loop(),
                    name="worker-reconcile-quote-loop",
                )
            )

    async def stop(self) -> None:
        if not self._started and self._lease is None:
            return
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks = []

        if self._started:
            await scheduler.stop()
            self._broker_stream.stop()
            write_worker_status(
                {
                    "is_running": False,
                    "current_phase": scheduler.current_phase,
                    "total_jobs": 0,
                    "next_run": None,
                    "next_task": None,
                    "failed_events": len(event_bus.get_failed_events(refresh_from_disk=True)),
                }
            )
        if self._lease is not None:
            self._lease.release()
            self._lease = None
        bind_broker_stream(None)
        bind_mutation_lock(None)
        bind_quote_cache(None)

        # Phase 11: stop graph projector and close driver gracefully
        try:
            await self._graph_projector.stop()
        except Exception:
            pass
        try:
            self._graph_projector.close()
        except Exception:
            pass
        self._started = False

    async def run_forever(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.add_signal_handler(sig, self._stop_event.set)

        await self.start()
        await self._stop_event.wait()

    async def _approval_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                async with self._execution_lock:
                    queued = self._state_machine.pending_execution_requests()
                    if queued:
                        await self._state_machine.execute_requested_approvals()
                    await self._state_machine.advance_active_executions()
                    # Phase 7 (P2): drain any operator-requested flatten. Same
                    # lock, so it serializes against approval submissions and
                    # protection recovery.
                    await self._state_machine.process_flatten_request()
            except Exception as exc:
                print(f"worker approval loop failed: {exc}")
            await asyncio.sleep(APPROVAL_POLL_SECONDS)

    async def _operator_control_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._process_operator_controls_once()
            except Exception as exc:
                print(f"worker operator-control loop failed: {exc}")
            await asyncio.sleep(OPERATOR_CONTROL_POLL_SECONDS)

    async def _process_operator_controls_once(self) -> None:
        for control in list_pending_failed_event_retries():
            control_key = str(control["control_key"])
            event_id = str(control.get("value", {}).get("event_id", "")).strip()
            if not event_id:
                mark_failed_event_retry(
                    control_key,
                    status="failed",
                    detail="missing_event_id",
                )
                continue
            success = await event_bus.retry_failed_event(event_id)
            mark_failed_event_retry(
                control_key,
                status="completed" if success else "failed",
                detail=None if success else "event_not_found",
            )

        pending_reconcile_acks = list_pending_reconcile_acks()
        if not pending_reconcile_acks:
            return

        async with self._execution_lock:
            for control in pending_reconcile_acks:
                control_key = str(control["control_key"])
                value = dict(control.get("value") or {})
                position_id = str(value.get("position_id") or "").strip().upper()
                resolution = str(value.get("resolution") or "").strip().lower()
                if not position_id or resolution not in {"broker_close", "retain"}:
                    mark_reconcile_ack(
                        control_key,
                        status="failed",
                        detail="invalid_reconcile_ack_request",
                    )
                    continue

                try:
                    result = await self._state_machine.resolve_reconcile_required(
                        position_id=position_id,
                        resolution=resolution,
                        source="worker_operator_control",
                    )
                except Exception as exc:
                    mark_reconcile_ack(
                        control_key,
                        status="failed",
                        detail=str(exc),
                    )
                    continue

                if result.get("status") == "rejected":
                    mark_reconcile_ack(
                        control_key,
                        status="failed",
                        result=result,
                        detail=str(result.get("reason") or "rejected"),
                    )
                    continue

                mark_reconcile_ack(
                    control_key,
                    status="completed",
                    result=result,
                )

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._maintain_broker_stream()
                await self._write_status()
            except Exception as exc:
                print(f"worker heartbeat failed: {exc}")
            await asyncio.sleep(WORKER_HEARTBEAT_SECONDS)

    async def _write_status(self) -> None:
        info = scheduler.get_schedule_info()
        info["owner"] = "worker"
        info["heartbeat"] = "alive"
        info["safety_counters"] = {
            "coordinator": self._state_machine.safety_counters(),
            "reconciler": self._reconciler.safety_counters(),
        }
        write_worker_status(info)

    async def _maintain_broker_stream(self) -> None:
        if not self._broker_stream_enabled():
            self._broker_stream.stop()
            return
        if not has_kite_session():
            self._broker_stream.stop()
            return
        await asyncio.to_thread(self._broker_stream.ensure_running)

    def _broker_stream_enabled(self) -> bool:
        return self._broker_live_enabled() or cfg.trading.mode.value == "paper"

    def _broker_live_enabled(self) -> bool:
        return cfg.trading.mode.value == "live" and runtime_flags.live_trading_enabled

    def _broker_sync_enabled(self) -> bool:
        return (
            self._broker_live_enabled()
            and has_kite_session()
        )
