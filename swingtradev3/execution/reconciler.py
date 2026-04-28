from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from contextlib import asynccontextmanager, nullcontext
from datetime import datetime, timedelta
from typing import Any

from auth.kite.client import has_kite_session
from broker.kite_rest import fetch_gtts, fetch_holdings, fetch_orders, fetch_positions
from broker.kite_stream import KiteBrokerStream
from broker.reducer import BrokerReducer
from broker.types import (
    BrokerPositionSnapshot,
    normalize_kite_position_snapshots,
    normalize_status,
)
from config import cfg
from memory.db import session_scope
from memory.repositories import MemoryRepository

from .operator_controls import (
    clear_block_new_entries,
    read_block_new_entries,
    set_block_new_entries,
    write_reconciliation_status,
)
from .protection_manager import ProtectionManager
from .quote_cache import QuoteCache
from .runtime_context import get_mutation_lock


OPEN_ORDER_INTENT_STATUSES = {
    "submitting",
    "submitted",
    "entry_open",
    "entry_partially_filled",
}
OPEN_BROKER_ORDER_STATUSES = {
    "open",
    "open_pending",
    "modify_pending",
    "modify_validation_pending",
    "trigger_pending",
    "cancel_pending",
    "put_order_req_received",
    "after_market_order_req_received",
    "validation_pending",
    "trigger pending",
}

logger = logging.getLogger("execution.reconciler")


def _now() -> datetime:
    return datetime.now()


def _run_id(kind: str, started_at: str) -> str:
    return f"reconcile:{kind}:{started_at}"


class Reconciler:
    """Phase 6 reconciliation + recovery service.

    Four deterministic loops (orders / positions / GTTs / quote freshness) against
    the broker; compares each snapshot to Postgres state, records drift, and flips
    ``block_new_entries`` when drift is critical. Also exposes a one-shot startup
    readiness check and a post-stream connectivity check that the worker gates
    live trading on. All write paths acquire the mutation lock bound by bootstrap
    to serialize with the coordinator and protection manager.
    """

    LOOP_ORDERS = "orders"
    LOOP_POSITIONS = "positions"
    LOOP_GTTS = "gtts"
    LOOP_QUOTES = "quote_freshness"
    LOOP_CONNECTION = "broker_connection"
    LOOP_DAILY_LOSS = "daily_loss"
    LOOP_STREAM = "stream"
    LOOP_AUTH = "auth"
    NON_LIVE_BLOCK_REASONS = (
        "stream_unavailable",
        "broker_disconnected",
        "stale_auth",
        "stale_quotes",
        "orders_drift",
        "positions_drift",
        "gtts_drift",
        "orders_loop_failures",
        "positions_loop_failures",
        "gtts_loop_failures",
        "quote_freshness_loop_failures",
        "broker_connection_loop_failures",
    )
    NON_LIVE_INCIDENT_IDS = (
        "stream_unavailable",
        "broker_disconnected",
        "stale_auth",
        "stale_quotes",
        "reconcile_orders",
        "reconcile_positions",
        "reconcile_gtts",
        "orders_loop_failures",
        "positions_loop_failures",
        "gtts_loop_failures",
        "quote_freshness_loop_failures",
        "broker_connection_loop_failures",
    )
    NON_LIVE_NON_BLOCKING_LOOPS = {
        LOOP_ORDERS,
        LOOP_POSITIONS,
        LOOP_GTTS,
        LOOP_QUOTES,
        LOOP_CONNECTION,
        LOOP_STREAM,
        LOOP_AUTH,
    }

    def __init__(
        self,
        *,
        broker_reducer: BrokerReducer,
        broker_stream: KiteBrokerStream,
        quote_cache: QuoteCache,
        protection_manager: ProtectionManager | None = None,
        exchange: str = "NSE",
    ) -> None:
        self._reducer = broker_reducer
        self._stream = broker_stream
        self._quote_cache = quote_cache
        self._protection = protection_manager or ProtectionManager()
        self._exchange = exchange
        self._stop_event: asyncio.Event | None = None
        self._consecutive_failures: dict[str, int] = {}
        # Phase 7: track disconnect onset so the grace window is measured against
        # the first observed disconnect rather than the loop-tick cadence.
        self._disconnect_since: datetime | None = None
        active_block_reasons = {
            str(item).strip()
            for item in (read_block_new_entries() or {}).get("active_reasons", [])
            if str(item).strip()
        }
        self._broker_block_active = "broker_disconnected" in active_block_reasons
        self._daily_loss_block_active = "daily_loss_limit" in active_block_reasons

    # ------------------------------------------------------------------
    # Config accessors (G10)
    # ------------------------------------------------------------------

    @property
    def _conf(self):
        return cfg.execution.reconciliation

    @property
    def _live_broker_enforcement_enabled(self) -> bool:
        return cfg.trading.mode.value == "live"

    # ------------------------------------------------------------------
    # Mutation lock helper (G2)
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def _acquire_lock(self):
        lock = get_mutation_lock()
        if lock is None:
            async with nullcontext():
                yield
        else:
            async with lock:
                yield

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def run_startup_reconciliation(
        self,
        *,
        wait_for_stream_seconds: float | None = None,
    ) -> dict[str, Any]:
        started_at = _now().isoformat()
        run_id = _run_id("startup", started_at)
        self._write_run(run_id, "started", {"started_at": started_at}, source="reconciler_startup")

        report: dict[str, Any] = {
            "started_at": started_at,
            "auth_valid": False,
            "stream_connected": False,
            "orders": {},
            "positions": {},
            "gtts": {},
            "drift": {"orders": 0, "positions": 0, "gtts": 0},
            "open_incidents": [],
            "ready": False,
        }

        auth_valid = has_kite_session()
        report["auth_valid"] = auth_valid
        if not auth_valid:
            return self._finalize_startup(run_id, started_at, report, ready=False, reason="auth_invalid")

        wait_seconds = (
            wait_for_stream_seconds
            if wait_for_stream_seconds is not None
            else 0.0
        )
        stream_connected = await self._await_stream(wait_seconds)
        report["stream_connected"] = stream_connected

        try:
            order_result = await self._reconcile_orders_once(source="reconciler_startup")
            report["orders"] = order_result
            report["drift"]["orders"] = order_result["drift"]["count"]

            positions_result = await self._reconcile_positions_once(source="reconciler_startup")
            report["positions"] = positions_result
            report["drift"]["positions"] = positions_result["drift"]["count"]

            gtt_result = await self._reconcile_gtts_once(source="reconciler_startup")
            report["gtts"] = gtt_result
            report["drift"]["gtts"] = gtt_result["drift"]["count"]
        except Exception as exc:
            logger.exception("startup reconciliation failed: %s", exc)
            self._finalize_startup(
                run_id, started_at, report, ready=False, reason=f"startup_sync_failed:{exc}"
            )
            raise RuntimeError(f"startup sync failed: {exc}") from exc

        with session_scope() as session:
            repo = MemoryRepository(session)
            open_incidents = repo.list_failure_incidents(status="open")
        critical_incidents = [
            item
            for item in open_incidents
            if str(item.get("severity") or "").lower() == "critical"
        ]
        report["open_incidents"] = open_incidents
        report["critical_incident_count"] = len(critical_incidents)

        ready = (
            auth_valid
            and not critical_incidents
            and report["drift"]["orders"] == 0
            and report["drift"]["positions"] == 0
        )
        reason = None if ready else "drift_or_critical_incident"
        return self._finalize_startup(run_id, started_at, report, ready=ready, reason=reason)

    async def run_post_stream_readiness_check(
        self,
        *,
        wait_for_stream_seconds: float | None = None,
    ) -> dict[str, Any]:
        """Phase 6 G6: second-phase startup check after stream.start().

        Confirms the WebSocket actually connected within timeout. Flips
        ``block_new_entries(reason="stream_unavailable")`` if it did not.
        """
        started_at = _now().isoformat()
        run_id = _run_id("stream_ready", started_at)
        self._write_run(
            run_id,
            "started",
            {"started_at": started_at, "source": "reconciler_post_stream"},
            source="reconciler_post_stream",
        )
        wait_seconds = (
            wait_for_stream_seconds
            if wait_for_stream_seconds is not None
            else float(self._conf.startup_stream_wait_seconds)
        )
        connected = await self._await_stream(wait_seconds)
        payload = {
            "started_at": started_at,
            "completed_at": _now().isoformat(),
            "wait_seconds": wait_seconds,
            "stream_connected": connected,
        }
        self._write_run(run_id, "completed", payload, source="reconciler_post_stream")
        if not connected:
            set_block_new_entries(
                reason="stream_unavailable",
                source="reconciler_post_stream",
                detail={"wait_seconds": wait_seconds},
            )
            self._open_incident(
                incident_id="stream_unavailable",
                severity="critical",
                payload={"at": _now().isoformat(), "wait_seconds": wait_seconds},
            )
        else:
            clear_block_new_entries(source="reconciler_post_stream", reason="stream_unavailable")
            self._resolve_incident("stream_unavailable", source="reconciler_post_stream")
        return payload

    async def _await_stream(self, timeout_seconds: float) -> bool:
        if self._stream is None:
            return False
        if timeout_seconds <= 0:
            return bool(getattr(self._stream, "_connected", False))
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            if getattr(self._stream, "_connected", False):
                return True
            await asyncio.sleep(0.5)
        return bool(getattr(self._stream, "_connected", False))

    def _finalize_startup(
        self,
        run_id: str,
        started_at: str,
        report: dict[str, Any],
        *,
        ready: bool,
        reason: str | None,
    ) -> dict[str, Any]:
        completed_at = _now().isoformat()
        report["completed_at"] = completed_at
        report["ready"] = ready
        if reason:
            report["reason"] = reason
        status = "completed" if ready else "failed"
        self._write_run(run_id, status, report, source="reconciler_startup")
        write_reconciliation_status(
            {
                "phase": "startup",
                "ready": ready,
                "reason": reason,
                "drift": report["drift"],
                "stream_connected": report["stream_connected"],
            },
            source="reconciler_startup",
        )
        if not ready:
            set_block_new_entries(
                reason=reason or "startup_failed",
                source="reconciler_startup",
                detail={"drift": report["drift"], "incident_count": len(report.get("open_incidents", []))},
            )
        return report

    async def relax_runtime_guards_for_non_live(self, *, source: str) -> None:
        """Clear live-broker latches when the worker is running outside live mode."""
        if self._live_broker_enforcement_enabled:
            return
        async with self._acquire_lock():
            for reason in self.NON_LIVE_BLOCK_REASONS:
                clear_block_new_entries(source=source, reason=reason)
            for incident_id in self.NON_LIVE_INCIDENT_IDS:
                self._resolve_incident(incident_id, source=source)
        self._broker_block_active = False
        self._disconnect_since = None

    # ------------------------------------------------------------------
    # Runtime loops
    # ------------------------------------------------------------------

    def register_stop_event(self, stop_event: asyncio.Event) -> None:
        self._stop_event = stop_event

    async def run_orders_loop(self) -> None:
        while self._should_continue():
            try:
                if has_kite_session():
                    await self._reconcile_orders_once(source="reconciler_orders_loop")
                    self._record_success(self.LOOP_ORDERS)
            except Exception as exc:
                logger.warning("reconciler orders loop failed: %s", exc)
                self._record_failure(self.LOOP_ORDERS, exc)
            await self._sleep(self._conf.order_interval_seconds)

    async def run_positions_loop(self) -> None:
        while self._should_continue():
            try:
                if has_kite_session():
                    result = await self._reconcile_positions_once(source="reconciler_positions_loop")
                    tickers = result.get("tracked_tickers") or []
                    if tickers and self._stream is not None:
                        self._stream.set_tracked_tickers(tickers, exchange=self._exchange)
                    self._record_success(self.LOOP_POSITIONS)
            except Exception as exc:
                logger.warning("reconciler positions loop failed: %s", exc)
                self._record_failure(self.LOOP_POSITIONS, exc)
            await self._sleep(self._conf.position_interval_seconds)

    async def run_gtts_loop(self) -> None:
        while self._should_continue():
            try:
                if has_kite_session():
                    await self._reconcile_gtts_once(source="reconciler_gtts_loop")
                    self._record_success(self.LOOP_GTTS)
            except Exception as exc:
                logger.warning("reconciler GTT loop failed: %s", exc)
                self._record_failure(self.LOOP_GTTS, exc)
            await self._sleep(self._conf.gtt_interval_seconds)

    async def run_quote_freshness_loop(self) -> None:
        while self._should_continue():
            try:
                await self._check_quote_freshness(source="reconciler_quote_loop")
                await self._check_auth_freshness(source="reconciler_quote_loop")
                self._record_success(self.LOOP_QUOTES)
            except Exception as exc:
                logger.warning("reconciler quote freshness loop failed: %s", exc)
                self._record_failure(self.LOOP_QUOTES, exc)
            await self._sleep(self._conf.quote_freshness_seconds)

    async def run_broker_connection_loop(self) -> None:
        """Phase 7 (P7): runtime broker-disconnect kill switch.

        Flips ``block_new_entries`` when the stream has been down for more than
        ``cfg.execution.safety.disconnect_grace_seconds``. Clears on reconnect.
        """
        interval = float(cfg.execution.safety.disconnect_check_interval_seconds)
        while self._should_continue():
            try:
                await self._check_broker_connection(source="reconciler_connection_loop")
                self._record_success(self.LOOP_CONNECTION)
            except Exception as exc:
                logger.warning("reconciler connection loop failed: %s", exc)
                self._record_failure(self.LOOP_CONNECTION, exc)
            await self._sleep(interval)

    async def run_daily_loss_loop(self) -> None:
        """Phase 7 (P3): realized-daily-loss kill switch.

        Runs every ``daily_loss_check_interval_seconds``; blocks new entries
        and flips ``exit_only_mode`` on breach.
        """
        interval = float(cfg.execution.safety.daily_loss_check_interval_seconds)
        while self._should_continue():
            try:
                await self._check_daily_loss(source="reconciler_daily_loss_loop")
                self._record_success(self.LOOP_DAILY_LOSS)
            except Exception as exc:
                logger.warning("reconciler daily loss loop failed: %s", exc)
                self._record_failure(self.LOOP_DAILY_LOSS, exc)
            await self._sleep(interval)

    def _should_continue(self) -> bool:
        return self._stop_event is None or not self._stop_event.is_set()

    async def _sleep(self, seconds: float) -> None:
        if self._stop_event is None:
            await asyncio.sleep(seconds)
            return
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return

    def safety_counters(self) -> dict[str, Any]:
        return {
            "loop_failures": dict(self._consecutive_failures),
            "broker_connection": {
                "disconnect_since": (
                    self._disconnect_since.isoformat() if self._disconnect_since is not None else None
                ),
                "kill_switch_active": self._broker_block_active,
            },
            "daily_loss": {
                "kill_switch_active": self._daily_loss_block_active,
            },
        }

    # ------------------------------------------------------------------
    # Consecutive-failure tracking (G9)
    # ------------------------------------------------------------------

    def _record_success(self, loop_name: str) -> None:
        if self._consecutive_failures.get(loop_name):
            self._consecutive_failures[loop_name] = 0
            if (
                not self._live_broker_enforcement_enabled
                and loop_name in self.NON_LIVE_NON_BLOCKING_LOOPS
            ):
                return
            clear_block_new_entries(
                source="reconciler",
                reason=f"{loop_name}_loop_failures",
            )
            self._resolve_incident(f"{loop_name}_loop_failures", source="reconciler")

    def _record_failure(self, loop_name: str, exc: Exception) -> None:
        count = self._consecutive_failures.get(loop_name, 0) + 1
        self._consecutive_failures[loop_name] = count
        if (
            not self._live_broker_enforcement_enabled
            and loop_name in self.NON_LIVE_NON_BLOCKING_LOOPS
        ):
            return
        threshold = int(self._conf.consecutive_failure_threshold)
        if count >= threshold:
            self._open_incident(
                incident_id=f"{loop_name}_loop_failures",
                severity="critical",
                payload={
                    "at": _now().isoformat(),
                    "loop": loop_name,
                    "consecutive_failures": count,
                    "threshold": threshold,
                    "latest_error": str(exc),
                },
            )
            set_block_new_entries(
                reason=f"{loop_name}_loop_failures",
                source="reconciler",
                detail={"consecutive_failures": count, "threshold": threshold},
            )

    # ------------------------------------------------------------------
    # Orders reconciliation (G1 correct orphan detection, G2 lock)
    # ------------------------------------------------------------------

    async def _reconcile_orders_once(self, *, source: str) -> dict[str, Any]:
        started_at = _now().isoformat()
        run_id = _run_id("orders", started_at)
        self._write_run(run_id, "started", {"started_at": started_at}, source=source)
        try:
            orders_payload = await asyncio.to_thread(fetch_orders)
        except Exception as exc:
            self._write_run(run_id, "failed", {"error": str(exc), "started_at": started_at}, source=source)
            self._open_incident(
                incident_id="reconcile_orders",
                severity="warning",
                payload={"detail": str(exc), "at": _now().isoformat(), "source": source},
            )
            raise

        # G1 + G2: drift detection must read DB state BEFORE apply so
        # "orphan on broker" can compare the broker truth against existing DB
        # linkage, not against rows the apply will itself insert. The apply
        # itself is serialized via the mutation lock.
        drift = self._detect_order_drift(orders_payload)
        async with self._acquire_lock():
            snapshot_result = await asyncio.to_thread(
                self._reducer.apply_orders_snapshot,
                orders_payload,
                source=source,
            )

        payload = {
            "started_at": started_at,
            "completed_at": _now().isoformat(),
            "source": source,
            "snapshot": snapshot_result,
            "drift": drift,
        }
        self._write_run(run_id, "completed", payload, source=source)
        if drift["count"] > 0:
            self._respond_to_drift(
                kind="orders",
                drift=drift,
                source=source,
                severity="warning" if drift["count"] < 3 else "critical",
            )
        else:
            self._maybe_clear_block("orders")
        return payload

    def _detect_order_drift(self, broker_orders: list[dict[str, Any]]) -> dict[str, Any]:
        """Correct orphan + missing detection (G1 fix).

        Orphan: broker order whose DB row has ``order_intent_id IS NULL``
        AND is not the exit leg of a known protective trigger.

        Missing: DB open ``order_intent`` whose broker_order_id/broker_tag is
        not present in the current broker snapshot.
        """
        broker_by_id: dict[str, dict[str, Any]] = {}
        broker_by_tag: dict[str, dict[str, Any]] = {}
        open_broker_orders: list[dict[str, Any]] = []
        for order in broker_orders or []:
            order_id = str(order.get("order_id") or "").strip()
            tag = str(order.get("tag") or "").strip()
            if order_id:
                broker_by_id[order_id] = order
            if tag:
                broker_by_tag[tag] = order
            if normalize_status(order.get("status")) in OPEN_BROKER_ORDER_STATUSES:
                open_broker_orders.append(order)

        with session_scope() as session:
            repo = MemoryRepository(session)
            db_intents = [
                item
                for item in repo.list_order_intents()
                if str(item.get("status") or "").strip().lower() in OPEN_ORDER_INTENT_STATUSES
            ]
            db_broker_orders = repo.list_broker_orders()
            protective_triggers = repo.list_protective_triggers()

        missing: list[dict[str, Any]] = []
        for intent in db_intents:
            payload = dict(intent.get("payload") or {})
            broker_order_id = str(
                intent.get("broker_order_id") or payload.get("broker_order_id") or ""
            ).strip()
            broker_tag = str(intent.get("broker_tag") or payload.get("broker_tag") or "").strip()
            matched = False
            if broker_order_id and broker_order_id in broker_by_id:
                matched = True
            elif broker_tag and broker_tag in broker_by_tag:
                matched = True
            if not matched:
                missing.append(
                    {
                        "order_intent_id": intent.get("order_intent_id"),
                        "ticker": intent.get("ticker"),
                        "status": intent.get("status"),
                        "broker_order_id": broker_order_id or None,
                        "broker_tag": broker_tag or None,
                    }
                )

        # Build linkage maps for orphan detection.
        db_order_links = {
            str(item.get("broker_order_id") or "").strip(): item.get("order_intent_id")
            for item in db_broker_orders
            if str(item.get("broker_order_id") or "").strip()
        }
        protective_exit_orders: set[str] = set()
        for trigger in protective_triggers:
            trigger_payload = dict(trigger.get("payload") or {})
            exit_order_id = str(trigger_payload.get("exit_order_id") or "").strip()
            if exit_order_id:
                protective_exit_orders.add(exit_order_id)

        orphans: list[dict[str, Any]] = []
        for order in open_broker_orders:
            order_id = str(order.get("order_id") or "").strip()
            if not order_id:
                continue
            # Legitimate GTT-triggered exit order: not drift.
            if order_id in protective_exit_orders:
                continue
            linked_intent_id = db_order_links.get(order_id)
            # If DB has no record at all, or has a record but the intent link
            # is empty (unknown origin), and it's not a known exit order,
            # it's a genuine orphan — operator should investigate.
            if linked_intent_id:
                continue
            orphans.append(
                {
                    "broker_order_id": order_id,
                    "ticker": str(order.get("tradingsymbol") or "").upper() or None,
                    "status": normalize_status(order.get("status")),
                    "tag": str(order.get("tag") or "").strip() or None,
                    "in_db": order_id in db_order_links,
                }
            )

        return {
            "count": len(missing) + len(orphans),
            "missing_on_broker": missing,
            "orphan_on_broker": orphans,
        }

    # ------------------------------------------------------------------
    # Positions reconciliation (G3 gated apply)
    # ------------------------------------------------------------------

    async def _reconcile_positions_once(self, *, source: str) -> dict[str, Any]:
        started_at = _now().isoformat()
        run_id = _run_id("positions", started_at)
        self._write_run(run_id, "started", {"started_at": started_at}, source=source)

        try:
            positions_payload = await asyncio.to_thread(fetch_positions)
            holdings_payload = await asyncio.to_thread(fetch_holdings)
        except Exception as exc:
            self._write_run(run_id, "failed", {"error": str(exc), "started_at": started_at}, source=source)
            self._open_incident(
                incident_id="reconcile_positions",
                severity="warning",
                payload={"detail": str(exc), "at": _now().isoformat(), "source": source},
            )
            raise

        snapshots = normalize_kite_position_snapshots(positions_payload, holdings_payload)
        drift = self._detect_position_drift(snapshots)
        tracked_tickers = sorted({snap.ticker for snap in snapshots})

        # G3: if ANY position we hold is missing from broker snapshot, the
        # destructive apply would delete it. Hold broker truth at arm's length:
        # surgically mark all drifted positions reconcile_required, refresh
        # prices on undisputed positions only, and require operator ack to exit.
        has_critical_drift = bool(drift["missing_on_broker"])

        if has_critical_drift:
            drifted_tickers = {
                str(item["ticker"]).upper()
                for item in drift["missing_on_broker"] + drift["quantity_mismatch"]
                if item.get("ticker")
            }
            async with self._acquire_lock():
                self._mark_positions_reconcile_required(drift, source=source)
                price_refresh = await asyncio.to_thread(
                    self._reducer.apply_position_price_refresh,
                    snapshots,
                    excluded_tickers=drifted_tickers,
                    source=source,
                )
            snapshot_result = {
                "status": "held",
                "reason": "critical_drift",
                "drifted": sorted(drifted_tickers),
                "price_refresh": price_refresh,
            }
        else:
            async with self._acquire_lock():
                snapshot_result = await asyncio.to_thread(
                    self._reducer.apply_position_snapshot,
                    positions_payload,
                    holdings_payload,
                    source=source,
                )
                if drift["quantity_mismatch"]:
                    self._mark_positions_reconcile_required(drift, source=source)

        payload = {
            "started_at": started_at,
            "completed_at": _now().isoformat(),
            "source": source,
            "snapshot": snapshot_result,
            "drift": drift,
            "tracked_tickers": tracked_tickers,
            "apply_held": has_critical_drift,
        }
        self._write_run(run_id, "completed", payload, source=source)

        if has_critical_drift:
            self._respond_to_drift(
                kind="positions", drift=drift, source=source, severity="critical"
            )
        elif drift["quantity_mismatch"]:
            self._respond_to_drift(
                kind="positions", drift=drift, source=source, severity="warning"
            )
        else:
            self._maybe_clear_block("positions")
        return payload

    def _detect_position_drift(
        self, snapshots: list[BrokerPositionSnapshot]
    ) -> dict[str, Any]:
        broker_by_ticker: dict[str, BrokerPositionSnapshot] = {
            snap.ticker.upper(): snap for snap in snapshots
        }

        with session_scope() as session:
            repo = MemoryRepository(session)
            db_positions = repo.list_positions()

        tolerance = int(self._conf.position_quantity_tolerance)
        quantity_mismatch: list[dict[str, Any]] = []
        missing_on_broker: list[dict[str, Any]] = []
        for position in db_positions:
            ticker = str(position.get("ticker") or "").upper()
            if not ticker:
                continue
            db_qty = int(position.get("quantity") or 0)
            broker_snap = broker_by_ticker.get(ticker)
            if broker_snap is None:
                if db_qty > 0:
                    missing_on_broker.append(
                        {
                            "position_id": position.get("position_id"),
                            "ticker": ticker,
                            "db_quantity": db_qty,
                            "broker_quantity": 0,
                            "reason": "missing_on_broker",
                        }
                    )
                continue
            broker_qty = int(getattr(broker_snap, "quantity", 0) or 0)
            if abs(db_qty - broker_qty) > tolerance:
                quantity_mismatch.append(
                    {
                        "position_id": position.get("position_id"),
                        "ticker": ticker,
                        "db_quantity": db_qty,
                        "broker_quantity": broker_qty,
                        "reason": "quantity_mismatch",
                    }
                )

        db_tickers = {str(item.get("ticker") or "").upper() for item in db_positions}
        orphan_on_broker: list[dict[str, Any]] = []
        for ticker, snap in broker_by_ticker.items():
            if ticker in db_tickers:
                continue
            broker_qty = int(getattr(snap, "quantity", 0) or 0)
            if broker_qty <= 0:
                continue
            orphan_on_broker.append(
                {
                    "ticker": ticker,
                    "broker_quantity": broker_qty,
                    "source_kind": getattr(snap, "source_kind", None),
                }
            )

        return {
            "count": len(quantity_mismatch) + len(missing_on_broker) + len(orphan_on_broker),
            "quantity_mismatch": quantity_mismatch,
            "missing_on_broker": missing_on_broker,
            "orphan_on_broker": orphan_on_broker,
        }

    def _mark_positions_reconcile_required(
        self,
        drift: dict[str, Any],
        *,
        source: str,
    ) -> None:
        affected: list[tuple[str, dict[str, Any]]] = []
        for item in drift.get("quantity_mismatch", []) + drift.get("missing_on_broker", []):
            position_id = str(item.get("position_id") or item.get("ticker") or "").upper()
            if position_id:
                affected.append((position_id, item))
        if not affected:
            return
        with session_scope() as session:
            repo = MemoryRepository(session)
            for position_id, item in affected:
                repo.update_position_state(
                    position_id=position_id,
                    new_state="reconcile_required",
                    source=source,
                    detail=(
                        f"{item.get('reason', 'position_drift')}:"
                        f"db={item.get('db_quantity')},"
                        f"broker={item.get('broker_quantity')}"
                    ),
                )

    # ------------------------------------------------------------------
    # GTT reconciliation
    # ------------------------------------------------------------------

    async def _reconcile_gtts_once(self, *, source: str) -> dict[str, Any]:
        started_at = _now().isoformat()
        run_id = _run_id("gtts", started_at)
        self._write_run(run_id, "started", {"started_at": started_at}, source=source)

        try:
            gtt_payload = await asyncio.to_thread(fetch_gtts)
        except Exception as exc:
            self._write_run(run_id, "failed", {"error": str(exc), "started_at": started_at}, source=source)
            self._open_incident(
                incident_id="reconcile_gtts",
                severity="warning",
                payload={"detail": str(exc), "at": _now().isoformat(), "source": source},
            )
            raise

        async with self._acquire_lock():
            snapshot_result = await asyncio.to_thread(
                self._reducer.apply_gtt_snapshot,
                gtt_payload,
                source=source,
            )
        drift = self._detect_gtt_drift(gtt_payload)

        watchdog_result: dict[str, Any] | None = None
        try:
            async with self._acquire_lock():
                watchdog_result = await self._protection.run_watchdog()
        except Exception as exc:
            logger.warning("protection watchdog failed during gtt reconciliation: %s", exc)
            self._open_incident(
                incident_id="reconcile_gtts",
                severity="warning",
                payload={"detail": f"watchdog_failed:{exc}", "at": _now().isoformat(), "source": source},
            )

        payload = {
            "started_at": started_at,
            "completed_at": _now().isoformat(),
            "source": source,
            "snapshot": snapshot_result,
            "drift": drift,
            "watchdog": watchdog_result,
        }
        self._write_run(run_id, "completed", payload, source=source)
        if drift["count"] > 0:
            self._respond_to_drift(
                kind="gtts",
                drift=drift,
                source=source,
                severity="warning",
            )
        else:
            self._maybe_clear_block("gtts")
        return payload

    def _detect_gtt_drift(self, broker_gtts: list[dict[str, Any]]) -> dict[str, Any]:
        broker_active: dict[str, dict[str, Any]] = {}
        for gtt in broker_gtts or []:
            status = str(gtt.get("status") or "").strip().lower()
            trigger_id = str(gtt.get("id") or gtt.get("trigger_id") or "").strip()
            if not trigger_id:
                continue
            if status == "active":
                broker_active[trigger_id] = gtt

        with session_scope() as session:
            repo = MemoryRepository(session)
            db_positions = repo.list_positions()

        missing_protection: list[dict[str, Any]] = []
        for position in db_positions:
            state = str(position.get("state") or "").strip().lower()
            if state != "open":
                # Skip positions in closing/closed/reconcile_required/operator_intervention —
                # they may legitimately lack an active GTT.
                continue
            payload = dict(position.get("payload") or {})
            oco_gtt_id = str(payload.get("oco_gtt_id") or "").strip()
            if not oco_gtt_id:
                missing_protection.append(
                    {
                        "position_id": position.get("position_id"),
                        "ticker": position.get("ticker"),
                        "reason": "no_oco_gtt_id",
                    }
                )
                continue
            if oco_gtt_id not in broker_active:
                missing_protection.append(
                    {
                        "position_id": position.get("position_id"),
                        "ticker": position.get("ticker"),
                        "reason": "broker_gtt_not_active",
                        "oco_gtt_id": oco_gtt_id,
                    }
                )
        return {
            "count": len(missing_protection),
            "missing_protection": missing_protection,
        }

    # ------------------------------------------------------------------
    # Quote freshness
    # ------------------------------------------------------------------

    async def _check_quote_freshness(self, *, source: str) -> dict[str, Any]:
        started_at = _now().isoformat()
        with session_scope() as session:
            repo = MemoryRepository(session)
            tickers = [
                str(position.get("ticker") or "").upper()
                for position in repo.list_positions()
                if str(position.get("state") or "").lower() in {"open", "closing"}
            ]
        tickers = [t for t in tickers if t]
        if not tickers:
            write_reconciliation_status(
                {
                    "phase": "quote_freshness",
                    "checked_at": started_at,
                    "tickers": [],
                    "stale_ratio": 0.0,
                },
                source=source,
            )
            return {"tickers": [], "stale_ratio": 0.0}

        freshness = self._quote_cache.check_freshness(
            tickers,
            max_age_seconds=float(self._conf.quote_max_age_seconds),
        )

        for stale_entry in freshness.get("stale", []):
            ticker = str(stale_entry.get("ticker") or "").upper()
            if not ticker:
                continue
            await self._quote_cache.fetch_rest_fallback(ticker, exchange=self._exchange)

        post_refresh = self._quote_cache.check_freshness(
            tickers,
            max_age_seconds=float(self._conf.quote_max_age_seconds),
        )

        write_reconciliation_status(
            {
                "phase": "quote_freshness",
                "checked_at": started_at,
                "tickers": tickers,
                "stale_ratio": post_refresh["stale_ratio"],
                "stream_connected": post_refresh["stream_connected"],
                "missing_count": len(post_refresh["missing"]),
                "stale_count": len(post_refresh["stale"]),
            },
            source=source,
        )

        if not self._live_broker_enforcement_enabled:
            async with self._acquire_lock():
                clear_block_new_entries(source=source, reason="stale_quotes")
                self._resolve_incident("stale_quotes", source=source)
            return post_refresh

        if post_refresh["stale_ratio"] >= float(self._conf.quote_stale_ratio_threshold):
            self._open_incident(
                incident_id="stale_quotes",
                severity="warning",
                payload={
                    "checked_at": started_at,
                    "stale": post_refresh["stale"],
                    "missing": post_refresh["missing"],
                    "stream_connected": post_refresh["stream_connected"],
                },
            )
            set_block_new_entries(
                reason="stale_quotes",
                source=source,
                detail={
                    "stale_ratio": post_refresh["stale_ratio"],
                    "stale_count": len(post_refresh["stale"]),
                    "missing_count": len(post_refresh["missing"]),
                },
            )
        else:
            self._maybe_clear_block("stale_quotes")
            self._resolve_incident("stale_quotes", source=source)
        return post_refresh

    # ------------------------------------------------------------------
    # Auth freshness (G8)
    # ------------------------------------------------------------------

    async def _check_auth_freshness(self, *, source: str) -> None:
        from .auth_preflight import is_session_fresh

        if not self._live_broker_enforcement_enabled:
            async with self._acquire_lock():
                clear_block_new_entries(source=source, reason="stale_auth")
                self._resolve_incident("stale_auth", source=source)
            return

        # Only act when we have a session; "no session" is a separate path that
        # the broker-live gate already covers. The preflight helper would return
        # ``(False, "missing")`` which is a different (noisier) signal.
        if not has_kite_session():
            return

        fresh, reason, age_hours = is_session_fresh(
            max_age_hours=float(self._conf.auth_max_age_hours)
        )
        if fresh:
            clear_block_new_entries(source=source, reason="stale_auth")
            self._resolve_incident("stale_auth", source=source)
            return

        # missing_timestamp and stale both trip the kill switch.
        detail: dict[str, Any] = {"stale_reason": reason}
        if age_hours is not None:
            detail["session_age_hours"] = age_hours
        self._open_incident(
            incident_id="stale_auth",
            severity="critical",
            payload={
                "at": _now().isoformat(),
                "max_age_hours": float(self._conf.auth_max_age_hours),
                **detail,
            },
        )
        set_block_new_entries(reason="stale_auth", source=source, detail=detail)

    # ------------------------------------------------------------------
    # Phase 7: broker-disconnect runtime kill switch (P7)
    # ------------------------------------------------------------------

    async def _check_broker_connection(self, *, source: str) -> dict[str, Any]:
        stream = self._stream
        if stream is None:
            return {"status": "no_stream"}
        status = stream.connection_status()
        now = _now()
        connected = bool(status.get("connected"))
        exhausted = bool(status.get("reconnect_exhausted"))
        grace = float(cfg.execution.safety.disconnect_grace_seconds)

        if connected and not exhausted:
            # Reset disconnect tracker and clear any prior kill-switch.
            self._disconnect_since = None
            if self._broker_block_active:
                async with self._acquire_lock():
                    clear_block_new_entries(source=source, reason="broker_disconnected")
                    self._resolve_incident("broker_disconnected", source=source)
                    self._broker_block_active = False
            return {"status": "connected", **status}

        if self._disconnect_since is None:
            self._disconnect_since = now

        downtime_seconds = (now - self._disconnect_since).total_seconds()

        # reconnect_exhausted is an immediate trip regardless of grace window.
        if exhausted or downtime_seconds >= grace:
            if not self._broker_block_active:
                async with self._acquire_lock():
                    self._open_incident(
                        incident_id="broker_disconnected",
                        severity="critical",
                        payload={
                            "at": now.isoformat(),
                            "downtime_seconds": downtime_seconds,
                            "reconnect_exhausted": exhausted,
                            "last_connect_at": status.get("last_connect_at"),
                            "last_disconnect_at": status.get("last_disconnect_at"),
                        },
                    )
                    set_block_new_entries(
                        reason="broker_disconnected",
                        source=source,
                        detail={
                            "downtime_seconds": downtime_seconds,
                            "reconnect_exhausted": exhausted,
                        },
                    )
                    self._broker_block_active = True
            return {"status": "disconnected", "downtime_seconds": downtime_seconds, **status}

        return {"status": "in_grace", "downtime_seconds": downtime_seconds, **status}

    # ------------------------------------------------------------------
    # Phase 7: daily-loss runtime kill switch (P3)
    # ------------------------------------------------------------------

    async def _check_daily_loss(self, *, source: str) -> dict[str, Any]:
        # Deferred import: risk.daily_loss reads the trades table every tick but
        # shouldn't be an import-time dep of the reconciler module.
        from execution.operator_controls import set_exit_only_mode
        from risk.daily_loss import daily_loss_snapshot

        snapshot = await asyncio.to_thread(daily_loss_snapshot)
        if snapshot is None:
            return {"status": "no_data"}

        threshold_pct = float(cfg.risk.max_daily_loss_pct)
        breached = bool(snapshot.get("breached"))
        if breached:
            if not self._daily_loss_block_active:
                async with self._acquire_lock():
                    self._open_incident(
                        incident_id="daily_loss_limit",
                        severity="critical",
                        payload={
                            "at": _now().isoformat(),
                            "realized_pnl": snapshot["realized_pnl"],
                            "equity": snapshot["equity"],
                            "loss_pct": snapshot["loss_pct"],
                            "threshold_pct": threshold_pct,
                        },
                    )
                    set_block_new_entries(
                        reason="daily_loss_limit",
                        source=source,
                        detail={
                            "realized_pnl": snapshot["realized_pnl"],
                            "loss_pct": snapshot["loss_pct"],
                            "threshold_pct": threshold_pct,
                        },
                    )
                    set_exit_only_mode(
                        enabled=True,
                        source=source,
                        reason="daily_loss_limit",
                    )
                    self._daily_loss_block_active = True
        # No auto-clear: per spec, the daily-loss block is sticky for the rest
        # of the trading day and is cleared by the next morning's premarket job.
        return snapshot

    # ------------------------------------------------------------------
    # Drift response / helpers
    # ------------------------------------------------------------------

    def _respond_to_drift(
        self,
        *,
        kind: str,
        drift: dict[str, Any],
        source: str,
        severity: str,
    ) -> None:
        self._open_incident(
            incident_id=f"reconcile_{kind}",
            severity=severity,
            payload={
                "at": _now().isoformat(),
                "source": source,
                "drift": drift,
            },
        )
        # Phase 6 spec: "if drift is detected, mark affected positions
        # reconcile_required and block new entries until resolved." Regardless
        # of severity — the severity only governs incident classification.
        set_block_new_entries(
            reason=f"{kind}_drift",
            source=source,
            detail={"drift_count": drift.get("count", 0), "kind": kind, "severity": severity},
        )

    def _maybe_clear_block(self, kind: str) -> None:
        """With G4 multi-reason block, clearing is now safe per-kind.

        clear_block_new_entries(reason=...) only removes the specific reason from
        the active-reasons set; the block flag stays true if other reasons remain.
        """
        clear_block_new_entries(
            source="reconciler",
            reason=f"{kind}_drift",
            detail={"cleared_for": kind},
        )
        # Also resolve the matching incident if present.
        self._resolve_incident(f"reconcile_{kind}", source="reconciler")

    def _open_incident(
        self,
        *,
        incident_id: str,
        severity: str,
        payload: dict[str, Any],
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_failure_incident(
                incident_id=incident_id,
                status="open",
                severity=severity,
                payload=payload,
                source="reconciler",
            )

    def _resolve_incident(self, incident_id: str, *, source: str) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            existing = repo.get_failure_incident(incident_id)
            if existing is None or existing.get("status") != "open":
                return
            repo.upsert_failure_incident(
                incident_id=incident_id,
                status="resolved",
                severity=str(existing.get("severity") or "warning"),
                payload={"resolved_at": _now().isoformat(), "source": source},
                source="reconciler",
            )

    def _write_run(
        self,
        run_id: str,
        status: str,
        payload: dict[str, Any],
        *,
        source: str,
    ) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            repo.upsert_reconciliation_run(
                reconciliation_run_id=run_id,
                status=status,
                payload=payload,
                source=source,
            )
