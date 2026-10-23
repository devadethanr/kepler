"""Read-only Phase 12 memory view client.

Agents use this layer for execution/context memory.  It can consume the
Toolbox sidecar when available, but always has a local typed fallback so
Toolbox or Memgraph downtime cannot affect runtime safety.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import text

from config import cfg
from context_graph.models import StockGraphContext
from context_graph.repository import ContextGraphRepository, GraphUnavailableError
from memory.db import session_scope
from memory.repository import MemoryRepository
from policy.effective_policy import resolve_effective_policy


class MemoryViewClient:
    """Read-only memory boundary for research and learning agents."""

    def __init__(self, *, graph_repo: ContextGraphRepository | None = None) -> None:
        self._graph = graph_repo
        self._toolsets: dict[str, Any] = {}

    # ── Toolbox optional path ───────────────────────────────────────

    def _toolbox_call(
        self,
        toolset: str,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> Any | None:
        if not cfg.toolbox.enabled:
            return None
        try:
            from toolbox_core import ToolboxSyncClient  # type: ignore

            if toolset not in self._toolsets:
                self._toolsets[toolset] = ToolboxSyncClient(cfg.toolbox.url).load_toolset(toolset)
            tool = self._toolsets[toolset][tool_name]
            return tool(**(parameters or {}))
        except Exception:
            return None

    # ── Postgres-backed views ───────────────────────────────────────

    @staticmethod
    def _query_view(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        with session_scope() as session:
            rows = session.execute(text(sql), params or {}).mappings().all()
            return [dict(row) for row in rows]

    def portfolio_risk_snapshot(self) -> dict[str, Any]:
        result = self._toolbox_call("allocator_readonly", "portfolio_risk_snapshot")
        if result:
            if isinstance(result, list):
                return dict(result[0]) if result else {}
            if isinstance(result, dict):
                return result
        rows = self._query_view("SELECT * FROM portfolio_risk_view LIMIT 1")
        return rows[0] if rows else {}

    def open_positions(self) -> list[dict[str, Any]]:
        result = self._toolbox_call("allocator_readonly", "open_positions")
        if isinstance(result, list):
            return [dict(item) for item in result]
        return self._query_view("SELECT * FROM open_positions_view ORDER BY ticker ASC")

    def execution_incidents(self, *, limit: int = 20) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 100))
        result = self._toolbox_call(
            "ops_readonly",
            "execution_incidents",
            {"limit": bounded},
        )
        if isinstance(result, list):
            return [dict(item) for item in result]
        return self._query_view(
            "SELECT * FROM execution_incidents_view LIMIT :limit",
            {"limit": bounded},
        )

    def effective_policy(self) -> dict[str, Any]:
        # Python resolver is authoritative because it merges config, overlays, and operator controls.
        return resolve_effective_policy().model_dump(mode="json")

    def session_readiness(self) -> dict[str, Any]:
        result = self._toolbox_call("ops_readonly", "session_readiness")
        if result:
            if isinstance(result, list):
                return dict(result[0]) if result else {}
            if isinstance(result, dict):
                return result
        rows = self._query_view("SELECT * FROM session_readiness_view LIMIT 1")
        return rows[0] if rows else {}

    def recent_trades(self, *, limit: int = 100) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 1000))
        result = self._toolbox_call(
            "posttrade_readonly",
            "recent_trades",
            {"limit": bounded},
        )
        if isinstance(result, list):
            return [dict(item) for item in result]
        return self._query_view(
            "SELECT * FROM recent_trades_view LIMIT :limit",
            {"limit": bounded},
        )

    def reconciliation_runs(self, *, limit: int = 20) -> list[dict[str, Any]]:
        bounded = max(1, min(int(limit), 100))
        result = self._toolbox_call(
            "ops_readonly",
            "reconciliation_runs",
            {"limit": bounded},
        )
        if isinstance(result, list):
            return [dict(item) for item in result]
        return self._query_view(
            "SELECT * FROM reconciliation_readiness_view LIMIT :limit",
            {"limit": bounded},
        )

    def operator_controls(self) -> list[dict[str, Any]]:
        result = self._toolbox_call("ops_readonly", "operator_controls")
        if isinstance(result, list):
            return [dict(item) for item in result]
        return self._query_view("SELECT * FROM operator_controls_view")

    # ── Memgraph-backed context and traversal ───────────────────────

    def _graph_repo(self) -> ContextGraphRepository:
        return self._graph or ContextGraphRepository()

    def get_stock_context(self, ticker: str) -> StockGraphContext:
        normalized = ticker.strip().upper()
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.stock_context(normalized)
        except GraphUnavailableError:
            return StockGraphContext(
                ticker=normalized,
                status="graph_unavailable",
                has_history=False,
                degraded_reason="context graph unavailable",
            )
        finally:
            if close:
                graph.close()

    def stock_context_graph_summary(self, ticker: str) -> dict[str, Any]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.stock_context_graph_summary(ticker)
        except GraphUnavailableError as exc:
            return {
                "ticker": ticker.strip().upper(),
                "status": "graph_unavailable",
                "degraded_reason": str(exc),
                "evidence": [],
            }
        finally:
            if close:
                graph.close()

    def candidate_memory_context(self, ticker: str, *, limit: int = 10) -> list[dict[str, Any]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.candidate_memory_context(ticker, limit=limit)
        except GraphUnavailableError:
            return []
        finally:
            if close:
                graph.close()

    def regime_snapshot_context(self, *, limit: int = 5) -> list[dict[str, Any]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.regime_snapshot_context(limit=limit)
        except GraphUnavailableError:
            return []
        finally:
            if close:
                graph.close()

    def similar_trades_context(
        self,
        ticker: str,
        *,
        setup_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.similar_trades_context(ticker, setup_type=setup_type, limit=limit)
        except GraphUnavailableError:
            return []
        finally:
            if close:
                graph.close()

    def trade_lesson_context(
        self,
        *,
        ticker: str | None = None,
        limit: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.trade_lesson_context(ticker=ticker, limit=limit)
        except GraphUnavailableError:
            return {"lessons": [], "observations": [], "failure_patterns": []}
        finally:
            if close:
                graph.close()

    def graph_neighbors(
        self,
        node_id: str,
        *,
        labels: list[str] | None = None,
        relationships: list[str] | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.get_graph_neighbors(
                node_id,
                allowed_labels=labels,
                allowed_relationships=relationships,
                limit=limit,
            )
        except GraphUnavailableError:
            return []
        finally:
            if close:
                graph.close()

    def graph_paths(
        self,
        start_node_id: str,
        *,
        relationships: list[str] | None = None,
        max_depth: int = 2,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.expand_graph_paths(
                start_node_id,
                allowed_relationships=relationships,
                max_depth=max_depth,
                limit=limit,
            )
        except GraphUnavailableError:
            return []
        finally:
            if close:
                graph.close()

    def candidate_evidence_trace(
        self,
        ticker: str,
        *,
        run_id: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        graph = self._graph_repo()
        close = self._graph is None
        try:
            return graph.get_candidate_evidence_trace(ticker, run_id=run_id, limit=limit)
        except GraphUnavailableError:
            return {"ticker": ticker.strip().upper(), "candidate": None, "evidence": []}
        finally:
            if close:
                graph.close()

    def research_context_packet(self, ticker: str, *, setup_type: str | None = None) -> dict[str, Any]:
        """Compact all-source context used in LLM prompts."""
        return {
            "ticker": ticker.strip().upper(),
            "stock": self.stock_context_graph_summary(ticker),
            "candidate_memory": self.candidate_memory_context(ticker, limit=10),
            "regime": self.regime_snapshot_context(limit=5),
            "similar_trades": self.similar_trades_context(
                ticker,
                setup_type=setup_type,
                limit=10,
            ),
            "portfolio_risk": self.portfolio_risk_snapshot(),
            "open_positions": self.open_positions(),
            "effective_policy": self.effective_policy(),
        }

    def latest_trade_payload(self) -> dict[str, Any] | None:
        trades = self.recent_trades(limit=1)
        if trades:
            return dict(trades[0].get("payload") or trades[0])
        with session_scope() as session:
            trades_payload = MemoryRepository(session).get_trades_payload()
        return trades_payload[0] if trades_payload else None


@lru_cache(maxsize=1)
def get_memory_view_client() -> MemoryViewClient:
    return MemoryViewClient()
