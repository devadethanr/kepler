from __future__ import annotations

import asyncio
import signal
from contextlib import suppress
from typing import Any

from sqlalchemy import text

from api.tasks.event_bus import event_bus
from api.tasks.scheduler import scheduler
from memory.bootstrap import initialize_memory_layer
from memory.db import get_engine

from .operator_controls import (
    list_pending_failed_event_retries,
    mark_failed_event_retry,
    write_worker_status,
)
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
        self._started = False

    async def start(self) -> None:
        initialize_memory_layer()
        self._lease = WorkerLease.acquire()
        await scheduler.start()
        self._started = True
        await self._write_status()
        self._tasks = [
            asyncio.create_task(self._approval_loop(), name="worker-approval-loop"),
            asyncio.create_task(self._operator_control_loop(), name="worker-operator-control-loop"),
            asyncio.create_task(self._heartbeat_loop(), name="worker-heartbeat-loop"),
        ]

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
                queued = self._state_machine.pending_execution_requests()
                if queued:
                    async with self._execution_lock:
                        await self._state_machine.execute_requested_approvals()
            except Exception as exc:
                print(f"worker approval loop failed: {exc}")
            await asyncio.sleep(APPROVAL_POLL_SECONDS)

    async def _operator_control_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
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
            except Exception as exc:
                print(f"worker operator-control loop failed: {exc}")
            await asyncio.sleep(OPERATOR_CONTROL_POLL_SECONDS)

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._write_status()
            except Exception as exc:
                print(f"worker heartbeat failed: {exc}")
            await asyncio.sleep(WORKER_HEARTBEAT_SECONDS)

    async def _write_status(self) -> None:
        info = scheduler.get_schedule_info()
        info["owner"] = "worker"
        info["heartbeat"] = "alive"
        write_worker_status(info)
