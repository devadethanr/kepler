"""ContextBuilder — Read Memgraph for agent prompts and research context.

Provides structured retrieval methods that return data suitable for
embedding in LLM prompts.  All reads go through ContextGraphRepository;
no raw Cypher leaks into calling code.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from context_graph.models import StockGraphContext
from context_graph.repository import ContextGraphRepository, GraphUnavailableError


class ContextBuilder:
    """Builds research context from the Memgraph graph for LLM agents."""

    def __init__(
        self,
        repo: ContextGraphRepository | None = None,
        *,
        max_news: int = 5,
        max_observations: int = 5,
        max_research: int = 5,
    ) -> None:
        self._repo = repo or ContextGraphRepository()
        self._max_news = max_news
        self._max_observations = max_observations
        self._max_research = max_research

    # ── stock context ────────────────────────────────────────────────

    def get_stock_context(self, ticker: str) -> StockGraphContext:
        """Full stock context: research history, news, observations."""
        try:
            return self._repo.stock_context(ticker)
        except GraphUnavailableError:
            return StockGraphContext(
                ticker=ticker.upper(),
                has_history=False,
                generated_at_ist=datetime.now().isoformat(),
            )

    def get_stock_score_history(self, ticker: str) -> list[dict[str, Any]]:
        """Score progression across research runs for a ticker."""
        normalized = ticker.strip().upper()
        try:
            records = self._repo._run(
                """
                MATCH (c:ResearchCandidate)-[:CANDIDATE_FOR]->(s:Stock {id: $stock_id})
                MATCH (c)-[:ANALYZED_IN]->(r:ResearchRun)
                RETURN c.score AS score,
                       c.setup_type AS setup_type,
                       c.shortlisted AS shortlisted,
                       c.observed_at AS observed_at,
                       r.scan_date AS scan_date
                ORDER BY c.observed_at DESC
                LIMIT $limit
                """,
                {"stock_id": f"stock:{normalized}", "limit": self._max_research},
            )
            return [
                {
                    "score": float(rec.get("score") or 0),
                    "setup_type": rec.get("setup_type", ""),
                    "shortlisted": bool(rec.get("shortlisted", False)),
                    "observed_at": rec.get("observed_at"),
                    "scan_date": rec.get("scan_date"),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    def get_sector_stocks(self, sector: str) -> list[dict[str, Any]]:
        """All stocks in a sector with their latest research scores."""
        normalized_sector = sector.strip().lower()
        try:
            records = self._repo._run(
                """
                MATCH (s:Stock)-[:BELONGS_TO_SECTOR]->(sec:Sector {id: $sector_id})
                OPTIONAL MATCH (c:ResearchCandidate)-[:CANDIDATE_FOR]->(s)
                WITH s, c ORDER BY c.observed_at DESC
                WITH s, head(collect(c)) AS latest
                RETURN s.ticker AS ticker,
                       s.id AS id,
                       latest.score AS latest_score,
                       latest.setup_type AS latest_setup
                ORDER BY s.ticker
                """,
                {"sector_id": f"sector:{normalized_sector}"},
            )
            return [
                {
                    "ticker": rec.get("ticker", "").replace("stock:", ""),
                    "latest_score": float(rec.get("latest_score") or 0),
                    "latest_setup": rec.get("latest_setup", ""),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    # ── regime context ───────────────────────────────────────────────

    def get_current_regime(self) -> dict[str, Any] | None:
        """Latest regime snapshot and associated research runs."""
        try:
            records = self._repo._run(
                """
                MATCH (r:RegimeSnapshot)
                RETURN r.regime AS regime,
                       r.observed_at AS observed_at,
                       r.id AS id
                ORDER BY r.observed_at DESC
                LIMIT 1
                """
            )
            if not records:
                return None
            rec = records[0]
            return {
                "regime": rec.get("regime", "unknown"),
                "observed_at": rec.get("observed_at"),
                "id": rec.get("id"),
            }
        except GraphUnavailableError:
            return None

    def get_regime_history(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Recent regime changes."""
        try:
            records = self._repo._run(
                """
                MATCH (r:RegimeSnapshot)
                RETURN r.regime AS regime,
                       r.observed_at AS observed_at,
                       r.id AS id
                ORDER BY r.observed_at DESC
                LIMIT $limit
                """,
                {"limit": limit},
            )
            return [
                {
                    "regime": rec.get("regime", "unknown"),
                    "observed_at": rec.get("observed_at"),
                    "id": rec.get("id"),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    # ── news context ─────────────────────────────────────────────────

    def get_recent_news(self, ticker: str | None = None, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Recent news articles, optionally filtered by ticker."""
        limit = limit or self._max_news
        try:
            if ticker:
                normalized = ticker.strip().upper()
                records = self._repo._run(
                    """
                    MATCH (n:NewsArticle)-[:AFFECTS_STOCK]->(s:Stock {id: $stock_id})
                    RETURN n.title AS title,
                           n.provider AS provider,
                           n.category AS category,
                           n.url AS url,
                           n.observed_at AS observed_at,
                           n.confidence AS confidence
                    ORDER BY n.observed_at DESC
                    LIMIT $limit
                    """,
                    {"stock_id": f"stock:{normalized}", "limit": limit},
                )
            else:
                records = self._repo._run(
                    """
                    MATCH (n:NewsArticle)
                    RETURN n.title AS title,
                           n.provider AS provider,
                           n.category AS category,
                           n.url AS url,
                           n.observed_at AS observed_at,
                           n.confidence AS confidence
                    ORDER BY n.observed_at DESC
                    LIMIT $limit
                    """,
                    {"limit": limit},
                )
            return [
                {
                    "title": rec.get("title", ""),
                    "provider": rec.get("provider", ""),
                    "category": rec.get("category", ""),
                    "url": rec.get("url", ""),
                    "observed_at": rec.get("observed_at"),
                    "confidence": float(rec.get("confidence") or 0),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    # ── lessons & failure patterns ───────────────────────────────────

    def get_recent_observations(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Recent observations from the graph."""
        limit = limit or self._max_observations
        try:
            records = self._repo._run(
                """
                MATCH (o:Observation)
                RETURN o.observation_type AS type,
                       o.ticker AS ticker,
                       o.observed_at AS observed_at,
                       o.payload_json AS payload
                ORDER BY o.observed_at DESC
                LIMIT $limit
                """,
                {"limit": limit},
            )
            return [
                {
                    "type": rec.get("type", ""),
                    "ticker": rec.get("ticker", ""),
                    "observed_at": rec.get("observed_at"),
                    "payload": rec.get("payload"),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    def get_failure_patterns(self) -> list[dict[str, Any]]:
        """Failure patterns for learning."""
        try:
            records = self._repo._run(
                """
                MATCH (f:FailurePattern)
                RETURN f.id AS id,
                       f.event_type AS event_type,
                       f.severity AS severity,
                       f.label AS label,
                       f.observed_at AS observed_at,
                       f.payload_json AS payload
                ORDER BY f.observed_at DESC
                LIMIT 20
                """
            )
            return [
                {
                    "id": rec.get("id", ""),
                    "event_type": rec.get("event_type", ""),
                    "severity": rec.get("severity", ""),
                    "label": rec.get("label", ""),
                    "observed_at": rec.get("observed_at"),
                    "payload": rec.get("payload"),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    def get_similar_trades(self, ticker: str) -> list[dict[str, Any]]:
        """Trades with similar characteristics from Memgraph."""
        normalized = ticker.strip().upper()
        try:
            records = self._repo._run(
                """
                MATCH (tm:TradeMemory)-[:SIMILAR_TO]->(other:TradeMemory)
                MATCH (tm)-[:ABOUT_STOCK]->(s:Stock {id: $stock_id})
                RETURN other.id AS id,
                       other.ticker AS ticker,
                       other.entry_price AS entry_price,
                       other.exit_price AS exit_price,
                       other.pnl_pct AS pnl_pct,
                       other.holding_days AS holding_days,
                       other.observed_at AS observed_at
                ORDER BY other.pnl_pct DESC
                LIMIT 10
                """,
                {"stock_id": f"stock:{normalized}"},
            )
            return [
                {
                    "id": rec.get("id", ""),
                    "ticker": rec.get("ticker", ""),
                    "entry_price": float(rec.get("entry_price") or 0),
                    "exit_price": float(rec.get("exit_price") or 0),
                    "pnl_pct": float(rec.get("pnl_pct") or 0),
                    "holding_days": int(rec.get("holding_days") or 0),
                    "observed_at": rec.get("observed_at"),
                }
                for rec in records
            ]
        except GraphUnavailableError:
            return []

    # ── latest research ──────────────────────────────────────────────

    def latest_research_summary(self) -> dict[str, Any] | None:
        """Summary of the most recent research run."""
        try:
            return self._repo.latest_research_summary()
        except GraphUnavailableError:
            return None

    # ── health ───────────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Graph health check."""
        try:
            return self._repo.health()
        except Exception as exc:
            return {"status": "unreachable", "error": str(exc)}