"""GraphProjector — Async bridge from Postgres execution_events to Memgraph.

Reads new execution_events from Postgres using a cursor, projects derived
graph nodes and edges into Memgraph.  Runs as a background task inside the
worker so that Memgraph stays in sync without blocking the execution hot path.

Direction: Postgres → Memgraph (one-way, async)
"""

from __future__ import annotations

import asyncio
from typing import Any

from context_graph.models import ProjectionResult
from context_graph.repository import ContextGraphRepository, GraphUnavailableError

from memory.db import session_scope
from memory.repository import MemoryRepository


GRAPH_PROJECTION_BATCH = 500
INTERVAL_SECONDS = 2.0

# High-frequency events with no graph value — skip to avoid clutter.
_SKIP_EVENT_TYPES: frozenset[str] = frozenset({
    "operator_control_updated",
})


class GraphProjector:
    """Cursor-based async projector: Postgres execution_events → Memgraph."""

    def __init__(
        self,
        *,
        graph_repo: ContextGraphRepository | None = None,
        batch_size: int = GRAPH_PROJECTION_BATCH,
        interval: float = INTERVAL_SECONDS,
    ) -> None:
        self._graph = graph_repo or ContextGraphRepository()
        self._batch_size = batch_size
        self._interval = interval
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def ensure_schema(self) -> None:
        """Ensure Memgraph schema (constraints, indexes)."""
        self._graph.ensure_schema()

    async def start(self) -> None:
        """Begin the projection loop as a background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="graph-projector")

    async def stop(self) -> None:
        """Signal the loop to stop and wait for it."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        """Main loop: poll for new events and project them."""
        await asyncio.sleep(2)  # let worker finish startup
        while self._running:
            try:
                result = await asyncio.to_thread(self._project_once)
                if result and result.projected > 0:
                    pass  # projection happened
            except GraphUnavailableError:
                pass  # Memgraph down — skip this cycle, will retry next loop
            except Exception:
                pass
            try:
                await asyncio.sleep(self._interval)
            except asyncio.CancelledError:
                break

    def _project_once(self) -> ProjectionResult:
        """Single projection pass: fetch new Postgres events → write to Memgraph.

        On the first run (cursor == 0) does a bulk sweep of ALL existing
        events so the initial projection finishes in seconds, not hours.
        """
        with session_scope() as pg_session:
            pg_repo = MemoryRepository(pg_session)
            cursor = self._graph.get_projection_cursor()

            projected = 0
            latest = cursor
            bulk_batch = 500

            while True:
                batch_size = max(self._batch_size, bulk_batch) if cursor == 0 else self._batch_size
                events = pg_repo.list_execution_events(
                    after_id=latest if latest > 0 else 0,
                    limit=batch_size,
                )
                if not events:
                    break

                for event in events:
                    eid = event.get("event_id")
                    if eid is not None and eid > latest:
                        latest = eid
                    self._project_event(event)
                    projected += 1

                # On first run, keep sweeping without persisting cursor until done
                if cursor > 0:
                    break

            if latest > cursor:
                self._graph.set_projection_cursor(latest)

        return ProjectionResult(projected=projected, latest_event_id=latest, status="ok")

    def _project_event(self, event: dict[str, Any]) -> None:
        """Project a single execution event into the Memgraph graph.

        Strategy:
        1. Always write the event as an ExecutionEvent node.
        2. Link the event to any tickers mentioned in the payload.
        3. For position-related events, upsert ticker as Stock with sector if available.
        """
        event_type = str(event.get("event_type") or "")
        etype = str(event.get("entity_type") or "")
        eid = str(event.get("entity_id") or "")
        payload = dict(event.get("payload") or {})

        # Collect all tickers from multiple possible sources
        tickers: set[str] = set()
        raw_tickers = payload.get("tickers") or []
        ticker_from_payload = str(payload.get("ticker") or "")
        if ticker_from_payload:
            raw_tickers = [*raw_tickers, ticker_from_payload]

        for raw in raw_tickers:
            norm = str(raw).strip().upper()
            if norm:
                tickers.add(norm)

        # Skip high-frequency events that add no graph value
        if event_type in _SKIP_EVENT_TYPES:
            return

        # Write the execution event into Memgraph
        try:
            self._graph.record_execution_event({
                "event_id": int(event.get("event_id") or 0),
                "event_type": event_type,
                "entity_type": etype,
                "entity_id": eid,
                "source": str(event.get("source") or "projector"),
                "payload": payload,
            })
        except GraphUnavailableError:
            return

        # Link execution event to stock nodes
        for t in tickers:
            try:
                self._graph.upsert_stock(t, source="projector")
                repo = self._graph  # ContextGraphRepository
                repo._run(
                    """
                    MATCH (e:ExecutionEvent {id: $event_id}), (s:Stock {id: $stock_id})
                    MERGE (e)-[rel:MENTIONS]->(s)
                    SET rel.source = $source,
                        rel.ingested_at = $ingested_at,
                        rel.projection_version = $pv
                    """,
                    {
                        "event_id": f"execution_event:{event.get('event_id')}",
                        "stock_id": f"stock:{t}",
                        "source": event_type,
                        "ingested_at": event.get("created_at", ""),
                        "pv": "phase11.v1",
                    },
                )
            except GraphUnavailableError:
                continue

        event_id_val = int(event.get("event_id") or 0)

        # Handle position materialization and state changes
        if etype == "position" and event_type in (
            "order_intent_position_materialized",
            "position_state_changed",
        ):
            self._project_position_event(eid, event_type, payload, tickers)

        # Handle approval events — link to approval entity
        if etype == "approval" and event_type in (
            "approval_updated",
            "approvals_replaced",
        ):
            self._project_approval_event(eid, payload, tickers)

        # Upsert research candidates if score data present
        if etype == "order_intent" and event_type == "order_intent_upserted":
            self._project_order_intent_event(event_id_val, eid, payload, tickers)

    def _project_position_event(
        self, entity_id: str, event_type: str, payload: dict[str, Any], tickers: set[str]
    ) -> None:
        """Project position events with position node in graph.

        Adds EXECUTED_AS edge for order_intent_position_materialized and
        CLOSED_AS edge for position_state_changed with new_state=closed.
        """
        ticker_str = next(iter(tickers), "UNKNOWN")
        new_state = str(payload.get("new_state", ""))
        now = str(payload.get("created_at", ""))
        try:
            self._run_cypher(
                """
                MATCH (s:Stock {id: $stock_id})
                MERGE (p:Position {ticker: $ticker})
                SET p.state = $state,
                    p.label = $ticker,
                    p.updated_at = $now
                MERGE (s)-[r:POSITION_FOR]->(p)
                SET r.ingested_at = $now,
                    r.projection_version = $pv
                """,
                {
                    "stock_id": f"stock:{ticker_str}",
                    "ticker": ticker_str,
                    "state": str(payload.get("state", payload.get("lifecycle_state", "open"))),
                    "now": now,
                    "pv": "phase11.v1",
                },
            )
            # EXECUTED_AS: OrderIntent → Position (on materialization)
            if event_type == "order_intent_position_materialized":
                self._run_cypher(
                    """
                    MATCH (oi:OrderIntent {id: $intent_id}), (p:Position {ticker: $ticker})
                    MERGE (oi)-[r:EXECUTED_AS]->(p)
                    SET r.source = $source,
                        r.ingested_at = $now,
                        r.projection_version = $pv
                    """,
                    {
                        "intent_id": f"order_intent:{entity_id}",
                        "ticker": ticker_str,
                        "source": "projector",
                        "now": now,
                        "pv": "phase11.v1",
                    },
                )
            # CLOSED_AS: OrderIntent → Position (when position is closed)
            if event_type == "position_state_changed" and new_state == "closed":
                self._run_cypher(
                    """
                    MATCH (oi:OrderIntent)-[:EXECUTED_AS]->(p:Position {ticker: $ticker})
                    MERGE (oi)-[r:CLOSED_AS]->(p)
                    SET r.source = $source,
                        r.ingested_at = $now,
                        r.projection_version = $pv
                    """,
                    {
                        "ticker": ticker_str,
                        "source": "projector",
                        "now": now,
                        "pv": "phase11.v1",
                    },
                )
        except GraphUnavailableError:
            pass

    def _project_approval_event(
        self, entity_id: str, payload: dict[str, Any], tickers: set[str]
    ) -> None:
        """Project approval state changes into graph."""
        status = str(payload.get("status", ""))
        ticker_str = next(iter(tickers), "UNKNOWN")
        try:
            self._run_cypher(
                """
                MATCH (s:Stock {id: $stock_id})
                MERGE (a:Approval {id: $approval_id})
                SET a.status = $status,
                    a.ticker = $ticker,
                    a.label = $ticker + ':' + $status,
                    a.updated_at = $now
                MERGE (s)-[r:APPROVAL_FOR]->(a)
                SET r.ingested_at = $now,
                    r.projection_version = $pv
                """,
                {
                    "stock_id": f"stock:{ticker_str}",
                    "approval_id": f"approval:{entity_id}",
                    "status": status,
                    "ticker": ticker_str,
                    "now": str(payload.get("created_at", "")),
                    "pv": "phase11.v1",
                },
            )
        except GraphUnavailableError:
            pass

    def _project_order_intent_event(
        self, event_id: int, entity_id: str, payload: dict[str, Any], tickers: set[str]
    ) -> None:
        """Project order intent state into graph."""
        status = str(payload.get("status", "proposed"))
        ticker_str = next(iter(tickers), "UNKNOWN")
        intent_node_id = f"order_intent:{entity_id}"
        try:
            self._run_cypher(
                """
                MATCH (s:Stock {id: $stock_id})
                MERGE (oi:OrderIntent {id: $intent_id})
                SET oi.status = $status,
                    oi.ticker = $ticker,
                    oi.label = $ticker + ':' + $status,
                    oi.updated_at = $now
                MERGE (s)-[r:ORDER_INTENT_FOR]->(oi)
                SET r.ingested_at = $now,
                    r.projection_version = $pv
                WITH oi
                MATCH (e:ExecutionEvent {id: $exec_event_id})
                MERGE (e)-[gen:GENERATED_INTENT]->(oi)
                SET gen.source = $source,
                    gen.ingested_at = $now,
                    gen.projection_version = $pv
                """,
                {
                    "stock_id": f"stock:{ticker_str}",
                    "intent_id": intent_node_id,
                    "exec_event_id": f"execution_event:{event_id}",
                    "status": status,
                    "ticker": ticker_str,
                    "now": str(payload.get("created_at", "")),
                    "pv": "phase11.v1",
                    "source": "projector",
                },
            )
        except GraphUnavailableError:
            pass

    # ── low-level helpers ────────────────────────────────────────────

    def _run_cypher(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self._graph._run(query, params)

    def close(self) -> None:
        """Close the underlying Memgraph driver connection."""
        self._graph.close()

    # Expose for testing
    @property
    def running(self) -> bool:
        return self._running