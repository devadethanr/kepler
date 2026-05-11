from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import cfg
from context_graph.models import GraphDashboardPayload, GraphEdge, GraphNode, StockGraphContext

try:
    from neo4j import GraphDatabase
except Exception:  # pragma: no cover - exercised when dependency is missing locally
    GraphDatabase = None  # type: ignore[assignment]


IST = ZoneInfo("Asia/Kolkata")
PROJECTION_VERSION = "phase11.v1"
CURSOR_NAME = "execution_events"
GRAPH_LABELS = {
    "Stock",
    "Sector",
    "Index",
    "ResearchRun",
    "ResearchCandidate",
    "NewsArticle",
    "SignalSnapshot",
    "TechnicalSnapshot",
    "FundamentalSnapshot",
    "SentimentSnapshot",
    "RegimeSnapshot",
    "TradeMemory",
    "Observation",
    "Lesson",
    "FailurePattern",
    "SkillVersion",
    "ExecutionEvent",
}


class GraphUnavailableError(RuntimeError):
    """Raised when Memgraph is disabled or not reachable."""


def _now_ist() -> datetime:
    return datetime.now(IST)


def _iso(value: Any | None = None) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return str(value)
    else:
        parsed = _now_ist()
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST).isoformat()


def _payload_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_payload_json(payload).encode("utf-8")).hexdigest()


def _clean_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-", ":", "."} else "_" for ch in value)


def _label_for(properties: dict[str, Any], labels: list[str]) -> str:
    for key in ("label", "ticker", "name", "title", "event_type", "id"):
        value = properties.get(key)
        if value:
            text = str(value)
            return text if len(text) <= 80 else f"{text[:77]}..."
    return labels[0] if labels else "Node"


class ContextGraphRepository:
    """Single Memgraph access layer for context, research, and learning memory."""

    def __init__(
        self,
        *,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        database: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        graph_cfg = cfg.context_graph
        self.enabled = graph_cfg.enabled if enabled is None else enabled
        self.uri = uri or graph_cfg.uri
        self.user = graph_cfg.user if user is None else user
        self.password = graph_cfg.password if password is None else password
        self.database = database or graph_cfg.database
        self._driver: Any | None = None

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def _auth(self) -> tuple[str, str]:
        return (self.user or "", self.password or "")

    def _client(self) -> Any:
        if not self.enabled:
            raise GraphUnavailableError("context graph is disabled")
        if GraphDatabase is None:
            raise GraphUnavailableError("neo4j driver is not installed")
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=self._auth(),
                connection_timeout=cfg.context_graph.connect_timeout_seconds,
            )
        return self._driver

    def _run(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            with self._client().session(database=self.database) as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except GraphUnavailableError:
            raise
        except Exception as exc:
            raise GraphUnavailableError(str(exc)) from exc

    def health(self) -> dict[str, Any]:
        try:
            self._client().verify_connectivity()
            return {"status": "ok", "uri": self.uri, "database": self.database}
        except Exception as exc:
            return {"status": "degraded", "uri": self.uri, "error": str(exc)}

    def ensure_schema(self) -> None:
        """Create uniqueness constraints and indexes in Memgraph."""
        statements = [
            "CREATE CONSTRAINT ON (n:Stock) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:Sector) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:ResearchRun) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:ResearchCandidate) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:NewsArticle) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:SentimentSnapshot) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:Observation) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:TradeMemory) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:FailurePattern) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:SkillVersion) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:ExecutionEvent) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:ProjectionCursor) ASSERT n.name IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:Index) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:SignalSnapshot) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:TechnicalSnapshot) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:FundamentalSnapshot) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:Lesson) ASSERT n.id IS UNIQUE;",
            "CREATE CONSTRAINT ON (n:RegimeSnapshot) ASSERT n.id IS UNIQUE;",
            "CREATE INDEX ON :Stock(ticker);",
            "CREATE INDEX ON :ResearchRun(observed_at);",
            "CREATE INDEX ON :NewsArticle(observed_at);",
            "CREATE INDEX ON :RegimeSnapshot(regime);",
            "CREATE INDEX ON :SignalSnapshot(observed_at);",
            "CREATE INDEX ON :TechnicalSnapshot(observed_at);",
            "CREATE INDEX ON :FundamentalSnapshot(observed_at);",
            "CREATE INDEX ON :TradeMemory(observed_at);",
        ]
        for statement in statements:
            try:
                self._run(statement)
            except GraphUnavailableError as exc:
                message = str(exc).lower()
                if "already exists" in message or "exists" in message:
                    continue
                raise

    def _meta(
        self,
        *,
        source: str,
        source_id: str,
        payload: dict[str, Any],
        observed_at: Any | None = None,
        confidence: float | None = None,
        postgres_table: str | None = None,
        postgres_pk: str | int | None = None,
    ) -> dict[str, Any]:
        return {
            "source": source,
            "source_id": source_id,
            "postgres_table": postgres_table,
            "postgres_pk": str(postgres_pk) if postgres_pk is not None else None,
            "observed_at": _iso(observed_at),
            "ingested_at": _now_ist().isoformat(),
            "payload_hash": _payload_hash(payload),
            "payload_json": _payload_json(payload),
            "confidence": 0.0 if confidence is None else float(confidence),
            "projection_version": PROJECTION_VERSION,
        }

    def upsert_stock(
        self,
        ticker: str,
        *,
        sector: str | None = None,
        payload: dict[str, Any] | None = None,
        source: str = "context_graph",
    ) -> None:
        normalized = ticker.strip().upper()
        if not normalized:
            return
        body = dict(payload or {})
        props = {
            "id": f"stock:{normalized}",
            "ticker": normalized,
            "label": normalized,
            **self._meta(source=source, source_id=normalized, payload=body),
        }
        self._run(
            """
            MERGE (s:Stock {id: $id})
            SET s += $props
            """,
            {"id": props["id"], "props": props},
        )
        if sector:
            self.upsert_sector(sector, source=source)
            self._run(
                """
                MATCH (s:Stock {id: $stock_id}), (sec:Sector {id: $sector_id})
                MERGE (s)-[r:BELONGS_TO_SECTOR]->(sec)
                SET r.source = $source,
                    r.observed_at = $observed_at,
                    r.ingested_at = $ingested_at,
                    r.projection_version = $projection_version
                """,
                {
                    "stock_id": props["id"],
                    "sector_id": f"sector:{_clean_key(sector.lower())}",
                    "source": source,
                    "observed_at": props["observed_at"],
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def upsert_sector(self, sector: str, *, source: str = "context_graph") -> None:
        name = sector.strip()
        if not name:
            return
        payload = {"sector": name}
        props = {
            "id": f"sector:{_clean_key(name.lower())}",
            "name": name,
            "label": name,
            **self._meta(source=source, source_id=name, payload=payload),
        }
        self._run(
            """
            MERGE (s:Sector {id: $id})
            SET s += $props
            """,
            {"id": props["id"], "props": props},
        )

    def upsert_index(
        self,
        name: str,
        *,
        index_type: str = "index",
        payload: dict[str, Any] | None = None,
        source: str = "context_graph",
    ) -> None:
        normalized = name.strip().upper()
        if not normalized:
            return
        body = dict(payload or {})
        props = {
            "id": f"index:{normalized}",
            "name": normalized,
            "index_type": index_type,
            "label": normalized,
            **self._meta(source=source, source_id=normalized, payload=body),
        }
        self._run(
            """
            MERGE (i:Index {id: $id})
            SET i += $props
            """,
            {"id": props["id"], "props": props},
        )

    def upsert_research_run(
        self,
        *,
        run_id: str,
        scan_date: str,
        analyzed_at: Any,
        regime: dict[str, Any],
        diagnostics: dict[str, Any],
        qualified_count: int,
        total_screened: int,
        shortlist: list[dict[str, Any]],
        scan_results: list[dict[str, Any]],
        stock_data: dict[str, Any] | None = None,
        source: str = "research_pipeline",
    ) -> None:
        payload = {
            "scan_date": scan_date,
            "regime": regime,
            "diagnostics": diagnostics,
            "qualified_count": qualified_count,
            "total_screened": total_screened,
            "shortlist_count": len(shortlist),
        }
        regime_name = str(regime.get("regime") or regime.get("market_regime") or "unknown")
        props = {
            "id": run_id,
            "scan_date": scan_date,
            "regime": regime_name,
            "qualified_count": int(qualified_count),
            "total_screened": int(total_screened),
            "shortlist_count": len(shortlist),
            "label": f"Research {scan_date}",
            **self._meta(source=source, source_id=run_id, payload=payload, observed_at=analyzed_at),
        }
        self._run(
            """
            MERGE (r:ResearchRun {id: $id})
            SET r += $props
            """,
            {"id": run_id, "props": props},
        )
        self.upsert_regime_snapshot(
            regime=regime,
            observed_at=analyzed_at,
            run_id=run_id,
            source=source,
        )

        shortlisted = {str(item.get("ticker") or "").upper() for item in shortlist}
        all_candidates = scan_results or shortlist
        for candidate in all_candidates:
            ticker = str(candidate.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            enriched = dict(candidate)
            enriched["shortlisted"] = ticker in shortlisted
            if stock_data and ticker in stock_data:
                enriched["stock_data"] = stock_data[ticker]
            self.upsert_research_candidate(
                run_id=run_id,
                ticker=ticker,
                candidate=enriched,
                observed_at=analyzed_at,
                source=source,
            )

    def upsert_regime_snapshot(
        self,
        *,
        regime: dict[str, Any],
        observed_at: Any,
        run_id: str | None = None,
        source: str = "regime",
    ) -> None:
        regime_name = str(regime.get("regime") or regime.get("market_regime") or "unknown")
        source_id = run_id or f"regime:{_iso(observed_at)}"
        props = {
            "id": f"regime:{_clean_key(source_id)}",
            "regime": regime_name,
            "label": regime_name,
            **self._meta(source=source, source_id=source_id, payload=regime, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (r:RegimeSnapshot {id: $id})
            SET r += $props
            """,
            {"id": props["id"], "props": props},
        )
        if run_id:
            self._run(
                """
                MATCH (run:ResearchRun {id: $run_id}), (reg:RegimeSnapshot {id: $regime_id})
                MERGE (run)-[rel:UNDER_REGIME]->(reg)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "run_id": run_id,
                    "regime_id": props["id"],
                    "source": source,
                    "ingested_at": _now_ist().isoformat(),
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def upsert_research_candidate(
        self,
        *,
        run_id: str,
        ticker: str,
        candidate: dict[str, Any],
        observed_at: Any,
        source: str = "research_pipeline",
    ) -> None:
        sector = candidate.get("sector")
        self.upsert_stock(ticker, sector=str(sector) if sector else None, payload=candidate, source=source)
        score = float(candidate.get("score") or 0.0)
        setup_type = str(candidate.get("setup_type") or "unknown")
        candidate_id = f"research_candidate:{run_id}:{ticker}"
        props = {
            "id": candidate_id,
            "ticker": ticker,
            "score": score,
            "setup_type": setup_type,
            "shortlisted": bool(candidate.get("shortlisted")),
            "label": f"{ticker} {score:g}",
            **self._meta(
                source=source,
                source_id=candidate_id,
                payload=candidate,
                observed_at=observed_at,
                confidence=score / 10.0 if score else 0.0,
            ),
        }
        self._run(
            """
            MERGE (c:ResearchCandidate {id: $id})
            SET c += $props
            WITH c
            MATCH (s:Stock {id: $stock_id}), (r:ResearchRun {id: $run_id})
            MERGE (c)-[for_stock:CANDIDATE_FOR]->(s)
            SET for_stock.source = $source,
                for_stock.ingested_at = $ingested_at,
                for_stock.projection_version = $projection_version
            MERGE (c)-[in_run:ANALYZED_IN]->(r)
            SET in_run.source = $source,
                in_run.ingested_at = $ingested_at,
                in_run.projection_version = $projection_version
            MERGE (s)-[seen:ANALYZED_IN]->(r)
            SET seen.source = $source,
                seen.ingested_at = $ingested_at,
                seen.projection_version = $projection_version
            """,
            {
                "id": candidate_id,
                "props": props,
                "stock_id": f"stock:{ticker}",
                "run_id": run_id,
                "source": source,
                "ingested_at": props["ingested_at"],
                "projection_version": PROJECTION_VERSION,
            },
        )
        if sector:
            self._run(
                """
                MATCH (c:ResearchCandidate {id: $candidate_id}),
                      (sec:Sector {id: $sector_id})
                MERGE (c)-[rel:BELONGS_TO_SECTOR]->(sec)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "candidate_id": candidate_id,
                    "sector_id": f"sector:{_clean_key(str(sector).lower())}",
                    "source": source,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def upsert_news_items(
        self,
        items: Iterable[dict[str, Any]],
        *,
        source: str = "news_aggregator",
    ) -> None:
        for item in items:
            self.upsert_news_item(dict(item), source=source)

    def upsert_news_item(self, item: dict[str, Any], *, source: str = "news_aggregator") -> None:
        source_id = str(
            item.get("news_id")
            or item.get("source_id")
            or item.get("canonical_url")
            or item.get("url")
            or item.get("raw_hash")
            or item.get("title")
            or ""
        )
        if not source_id:
            return
        news_id = source_id if len(source_id) <= 120 else _payload_hash({"source_id": source_id})
        observed_at = item.get("published_at_ist") or item.get("published_at_utc") or item.get("fetched_at_ist")
        props = {
            "id": f"news:{news_id}",
            "title": str(item.get("title") or "")[:500],
            "provider": str(item.get("provider") or item.get("source") or "unknown"),
            "source_type": str(item.get("source_type") or "unknown"),
            "category": str(item.get("category") or "unknown"),
            "url": str(item.get("canonical_url") or item.get("url") or ""),
            "label": str(item.get("title") or news_id)[:80],
            **self._meta(
                source=source,
                source_id=news_id,
                payload=item,
                observed_at=observed_at,
                confidence=float(item.get("confidence") or 0.0),
                postgres_table="news_articles" if item.get("news_id") else None,
                postgres_pk=item.get("news_id"),
            ),
        }
        self._run(
            """
            MERGE (n:NewsArticle {id: $id})
            SET n += $props
            """,
            {"id": props["id"], "props": props},
        )
        for ticker in item.get("tickers") or []:
            normalized = str(ticker).strip().upper()
            if not normalized:
                continue
            self.upsert_stock(normalized, source=source)
            self._run(
                """
                MATCH (n:NewsArticle {id: $news_id}), (s:Stock {id: $stock_id})
                MERGE (n)-[rel:AFFECTS_STOCK]->(s)
                SET rel.source = $source,
                    rel.confidence = $confidence,
                    rel.observed_at = $observed_at,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "news_id": props["id"],
                    "stock_id": f"stock:{normalized}",
                    "source": source,
                    "confidence": props["confidence"],
                    "observed_at": props["observed_at"],
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def upsert_sentiment_snapshot(
        self,
        *,
        text_hash: str,
        result: dict[str, Any],
        text: str | None = None,
        source: str = "sentiment_analyzer",
    ) -> None:
        payload = {"result": result, "text": (text or "")[:2000]}
        props = {
            "id": f"sentiment:{text_hash}",
            "label": str(result.get("label") or "sentiment"),
            "score": float(result.get("score") or result.get("sentiment_score") or 0.0),
            "sentiment_label": str(result.get("label") or result.get("sentiment_label") or "unknown"),
            **self._meta(source=source, source_id=text_hash, payload=payload),
        }
        self._run(
            """
            MERGE (s:SentimentSnapshot {id: $id})
            SET s += $props
            """,
            {"id": props["id"], "props": props},
        )

    def upsert_signal_snapshot(
        self,
        *,
        ticker: str,
        signal_type: str,
        payload: dict[str, Any],
        observed_at: Any = None,
        source: str = "signal_analyzer",
    ) -> None:
        source_id = str(payload.get("signal_id") or f"{ticker}:{signal_type}:{_iso(observed_at)}")
        props = {
            "id": f"signal:{source_id}",
            "ticker": ticker.upper(),
            "signal_type": signal_type,
            "label": f"{ticker}:{signal_type}",
            **self._meta(source=source, source_id=source_id, payload=payload, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (s:SignalSnapshot {id: $id})
            SET s += $props
            """,
            {"id": props["id"], "props": props},
        )
        normalized = ticker.strip().upper()
        if normalized:
            self.upsert_stock(normalized, source=source)
            self._run(
                """
                MATCH (st:Stock {id: $stock_id}), (sig:SignalSnapshot {id: $signal_id})
                MERGE (st)-[rel:HAS_SIGNAL]->(sig)
                SET rel.source = $source,
                    rel.signal_type = $signal_type,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "stock_id": f"stock:{normalized}",
                    "signal_id": props["id"],
                    "source": source,
                    "signal_type": signal_type,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def upsert_technical_snapshot(
        self,
        *,
        ticker: str,
        payload: dict[str, Any],
        observed_at: Any = None,
        source: str = "technical_analyzer",
    ) -> None:
        source_id = str(payload.get("tech_id") or f"{ticker}:{_iso(observed_at)}")
        normalized = ticker.strip().upper()
        props = {
            "id": f"technical:{source_id}",
            "ticker": normalized,
            "label": f"{normalized} technical",
            **self._meta(source=source, source_id=source_id, payload=payload, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (t:TechnicalSnapshot {id: $id})
            SET t += $props
            """,
            {"id": props["id"], "props": props},
        )
        if normalized:
            self.upsert_stock(normalized, source=source)

    def upsert_fundamental_snapshot(
        self,
        *,
        ticker: str,
        payload: dict[str, Any],
        observed_at: Any = None,
        source: str = "fundamental_analyzer",
    ) -> None:
        source_id = str(payload.get("fund_id") or f"{ticker}:{_iso(observed_at)}")
        normalized = ticker.strip().upper()
        props = {
            "id": f"fundamental:{source_id}",
            "ticker": normalized,
            "label": f"{normalized} fundamentals",
            **self._meta(source=source, source_id=source_id, payload=payload, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (f:FundamentalSnapshot {id: $id})
            SET f += $props
            """,
            {"id": props["id"], "props": props},
        )
        if normalized:
            self.upsert_stock(normalized, source=source)

    def upsert_trade_memory(
        self,
        *,
        trade_id: str,
        ticker: str,
        payload: dict[str, Any],
        entry_price: float = 0.0,
        exit_price: float = 0.0,
        pnl_pct: float = 0.0,
        setup_type: str | None = None,
        sector: str | None = None,
        observed_at: Any = None,
        similar_trade_ids: list[str] | None = None,
        source: str = "trade_reviewer",
    ) -> None:
        normalized = ticker.strip().upper()
        props = {
            "id": f"trade_memory:{trade_id}",
            "trade_id": trade_id,
            "ticker": normalized,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_pct": pnl_pct,
            "setup_type": setup_type or "",
            "sector": sector or "",
            "label": f"{normalized} {setup_type or 'trade'} {pnl_pct:+.1f}%",
            **self._meta(source=source, source_id=trade_id, payload=payload, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (tm:TradeMemory {id: $id})
            SET tm += $props
            """,
            {"id": props["id"], "props": props},
        )
        if normalized:
            self.upsert_stock(normalized, source=source)
            self._run(
                """
                MATCH (tm:TradeMemory {id: $tm_id}), (s:Stock {id: $stock_id})
                MERGE (tm)-[rel:ABOUT_STOCK]->(s)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "tm_id": props["id"],
                    "stock_id": f"stock:{normalized}",
                    "source": source,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )
        if similar_trade_ids:
            for other_id in similar_trade_ids:
                if other_id == trade_id:
                    continue
                self._run(
                    """
                    MATCH (a:TradeMemory {id: $a_id}), (b:TradeMemory {id: $b_id})
                    MERGE (a)-[rel:SIMILAR_TO]->(b)
                    SET rel.source = $source,
                        rel.ingested_at = $ingested_at,
                        rel.projection_version = $projection_version
                    """,
                    {
                        "a_id": f"trade_memory:{trade_id}",
                        "b_id": f"trade_memory:{other_id}",
                        "source": source,
                        "ingested_at": props["ingested_at"],
                        "projection_version": PROJECTION_VERSION,
                    },
                )

    def upsert_lesson(
        self,
        *,
        lesson_id: str,
        lesson_text: str,
        category: str = "general",
        ticker: str | None = None,
        observation_ids: list[str] | None = None,
        payload: dict[str, Any] | None = None,
        observed_at: Any = None,
        source: str = "learning_agent",
    ) -> None:
        body = dict(payload or {})
        props = {
            "id": f"lesson:{lesson_id}",
            "lesson_text": lesson_text[:2000],
            "category": category,
            "ticker": (ticker or "").upper(),
            "label": f"{category}: {lesson_text[:60]}",
            **self._meta(source=source, source_id=lesson_id, payload=body, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (l:Lesson {id: $id})
            SET l += $props
            """,
            {"id": props["id"], "props": props},
        )
        if ticker:
            normalized = ticker.strip().upper()
            self.upsert_stock(normalized, source=source)
        if observation_ids:
            for obs_id in observation_ids:
                self._run(
                    """
                    MATCH (l:Lesson {id: $lesson_id}), (o:Observation {id: $obs_id})
                    MERGE (l)-[rel:SUPPORTS_LESSON]->(o)
                    SET rel.source = $source,
                        rel.ingested_at = $ingested_at,
                        rel.projection_version = $projection_version
                    """,
                    {
                        "lesson_id": props["id"],
                        "obs_id": f"observation:{obs_id}",
                        "source": source,
                        "ingested_at": props["ingested_at"],
                        "projection_version": PROJECTION_VERSION,
                    },
                )

    def record_observation(
        self,
        *,
        observation_type: str,
        ticker: str | None,
        payload: dict[str, Any],
        source: str,
    ) -> None:
        observed_at = payload.get("timestamp") or payload.get("created_at") or _now_ist().isoformat()
        source_id = str(payload.get("observation_id") or _payload_hash(payload))
        props = {
            "id": f"observation:{source_id}",
            "observation_type": observation_type,
            "ticker": (ticker or "").upper(),
            "label": f"{observation_type}:{(ticker or 'market').upper()}",
            **self._meta(source=source, source_id=source_id, payload=payload, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (o:Observation {id: $id})
            SET o += $props
            """,
            {"id": props["id"], "props": props},
        )
        if ticker:
            normalized = ticker.upper()
            self.upsert_stock(normalized, source=source)
            self._run(
                """
                MATCH (o:Observation {id: $obs_id}), (s:Stock {id: $stock_id})
                MERGE (o)-[rel:MENTIONS]->(s)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "obs_id": props["id"],
                    "stock_id": f"stock:{normalized}",
                    "source": source,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

    def record_execution_event(self, event: dict[str, Any]) -> None:
        payload = dict(event.get("payload") or {})
        event_id = int(event["event_id"])
        event_type = str(event.get("event_type") or "unknown")
        entity_type = str(event.get("entity_type") or "unknown")
        entity_id = str(event.get("entity_id") or event_id)
        source = str(event.get("source") or "postgres")
        props = {
            "id": f"execution_event:{event_id}",
            "event_id": event_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "label": event_type,
            **self._meta(
                source=source,
                source_id=str(event_id),
                payload=payload,
                observed_at=event.get("created_at"),
                postgres_table="execution_events",
                postgres_pk=event_id,
            ),
        }
        self._run(
            """
            MERGE (e:ExecutionEvent {id: $id})
            SET e += $props
            """,
            {"id": props["id"], "props": props},
        )

        tickers = payload.get("tickers") or []
        ticker = payload.get("ticker")
        if ticker:
            tickers = [*tickers, ticker]
        for raw_ticker in tickers:
            normalized = str(raw_ticker).strip().upper()
            if not normalized:
                continue
            self.upsert_stock(normalized, source=source)
            self._run(
                """
                MATCH (e:ExecutionEvent {id: $event_id}), (s:Stock {id: $stock_id})
                MERGE (e)-[rel:MENTIONS]->(s)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "event_id": props["id"],
                    "stock_id": f"stock:{normalized}",
                    "source": source,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )

        if event_type == "news_item_ingested":
            self.upsert_news_item({**payload, "news_id": entity_id}, source=source)
            self._run(
                """
                MATCH (e:ExecutionEvent {id: $event_id}), (n:NewsArticle {id: $news_id})
                MERGE (e)-[rel:PRODUCED_OBSERVATION]->(n)
                SET rel.source = $source,
                    rel.ingested_at = $ingested_at,
                    rel.projection_version = $projection_version
                """,
                {
                    "event_id": props["id"],
                    "news_id": f"news:{entity_id}",
                    "source": source,
                    "ingested_at": props["ingested_at"],
                    "projection_version": PROJECTION_VERSION,
                },
            )
        elif "incident" in event_type or entity_type == "failure_incident":
            self.upsert_failure_pattern(event=event, source=source)

    def upsert_failure_pattern(self, *, event: dict[str, Any], source: str) -> None:
        payload = dict(event.get("payload") or {})
        event_id = str(event.get("event_id") or event.get("entity_id") or _payload_hash(payload))
        props = {
            "id": f"failure:{event_id}",
            "event_type": str(event.get("event_type") or "failure"),
            "severity": str(payload.get("severity") or "warning"),
            "label": str(payload.get("reason") or event.get("event_type") or "Failure"),
            **self._meta(source=source, source_id=event_id, payload=payload, observed_at=event.get("created_at")),
        }
        self._run(
            """
            MERGE (f:FailurePattern {id: $id})
            SET f += $props
            WITH f
            MATCH (e:ExecutionEvent {id: $event_id})
            MERGE (e)-[rel:FAILED_DURING]->(f)
            SET rel.source = $source,
                rel.ingested_at = $ingested_at,
                rel.projection_version = $projection_version
            """,
            {
                "id": props["id"],
                "props": props,
                "event_id": f"execution_event:{event_id}",
                "source": source,
                "ingested_at": props["ingested_at"],
                "projection_version": PROJECTION_VERSION,
            },
        )

    def upsert_skill_version(
        self,
        *,
        version_id: str,
        name: str,
        content: str = "",
        payload: dict[str, Any] | None = None,
        observed_at: Any = None,
        source: str = "strategy_manager",
    ) -> None:
        body = dict(payload or {})
        props = {
            "id": f"skill:{version_id}",
            "name": name,
            "version_id": version_id,
            "content_preview": content[:500],
            "label": name,
            **self._meta(source=source, source_id=version_id, payload=body, observed_at=observed_at),
        }
        self._run(
            """
            MERGE (sv:SkillVersion {id: $id})
            SET sv += $props
            """,
            {"id": props["id"], "props": props},
        )

    def get_projection_cursor(self, name: str = CURSOR_NAME) -> int:
        records = self._run(
            "MATCH (c:ProjectionCursor {name: $name}) RETURN c.last_event_id AS cursor",
            {"name": name},
        )
        if not records:
            return 0
        return int(records[0].get("cursor") or 0)

    def set_projection_cursor(self, last_event_id: int, name: str = CURSOR_NAME) -> None:
        payload = {"name": name, "last_event_id": int(last_event_id)}
        self._run(
            """
            MERGE (c:ProjectionCursor {name: $name})
            SET c.last_event_id = $last_event_id,
                c.updated_at = $updated_at,
                c.payload_hash = $payload_hash,
                c.projection_version = $projection_version
            """,
            {
                "name": name,
                "last_event_id": int(last_event_id),
                "updated_at": _now_ist().isoformat(),
                "payload_hash": _payload_hash(payload),
                "projection_version": PROJECTION_VERSION,
            },
        )

    def dashboard_graph(
        self,
        *,
        node_limit: int | None = None,
        edge_limit: int | None = None,
    ) -> GraphDashboardPayload:
        nodes_limit = node_limit or cfg.context_graph.dashboard_node_limit
        edges_limit = edge_limit or cfg.context_graph.dashboard_edge_limit
        node_records = self._run(
            """
            MATCH (n)
            WHERE any(label IN labels(n) WHERE label IN $labels)
            RETURN n.id AS id, labels(n) AS labels, properties(n) AS properties
            ORDER BY coalesce(n.ingested_at, n.observed_at, n.updated_at, "") DESC
            LIMIT $limit
            """,
            {"labels": sorted(GRAPH_LABELS), "limit": int(nodes_limit)},
        )
        nodes = []
        node_ids = set()
        for record in node_records:
            properties = dict(record.get("properties") or {})
            labels = [str(label) for label in record.get("labels") or []]
            node_id = str(record.get("id") or "")
            if not node_id:
                continue
            node_ids.add(node_id)
            node_type = next((label for label in labels if label in GRAPH_LABELS), labels[0] if labels else "Node")
            nodes.append(
                GraphNode(
                    id=node_id,
                    label=_label_for(properties, labels),
                    type=node_type,
                    properties=properties,
                )
            )
        edge_records = []
        if node_ids:
            edge_records = self._run(
                """
                MATCH (a)-[r]->(b)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN a.id AS source, b.id AS target, type(r) AS label, properties(r) AS properties
                LIMIT $limit
                """,
                {"node_ids": sorted(node_ids), "limit": int(edges_limit)},
            )
        edges = [
            GraphEdge(
                source=str(record.get("source")),
                target=str(record.get("target")),
                label=str(record.get("label")),
                properties=dict(record.get("properties") or {}),
            )
            for record in edge_records
            if record.get("source") and record.get("target")
        ]
        return GraphDashboardPayload(
            status="ok",
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            generated_at_ist=_now_ist().isoformat(),
        )

    def stock_context(self, ticker: str) -> StockGraphContext:
        normalized = ticker.strip().upper()
        records = self._run(
            """
            MATCH (s:Stock {id: $stock_id})
            OPTIONAL MATCH (c:ResearchCandidate)-[:CANDIDATE_FOR]->(s)
            OPTIONAL MATCH (c)-[:ANALYZED_IN]->(r:ResearchRun)
            WITH s, c, r
            ORDER BY coalesce(c.observed_at, "") DESC
            WITH s, collect({
                score: c.score,
                setup_type: c.setup_type,
                shortlisted: c.shortlisted,
                observed_at: c.observed_at,
                run_id: r.id,
                payload_json: c.payload_json
            })[..5] AS research
            OPTIONAL MATCH (n:NewsArticle)-[:AFFECTS_STOCK]->(s)
            WITH s, research, n
            ORDER BY coalesce(n.observed_at, "") DESC
            WITH s, research, collect({
                title: n.title,
                provider: n.provider,
                category: n.category,
                observed_at: n.observed_at,
                url: n.url
            })[..5] AS news
            OPTIONAL MATCH (o:Observation)-[:MENTIONS]->(s)
            WITH research, news, o
            ORDER BY coalesce(o.observed_at, "") DESC
            RETURN research,
                   news,
                   collect({
                       type: o.observation_type,
                       observed_at: o.observed_at,
                       payload_json: o.payload_json
                   })[..5] AS observations
            """,
            {"stock_id": f"stock:{normalized}"},
        )
        if not records:
            return StockGraphContext(ticker=normalized, generated_at_ist=_now_ist().isoformat())
        record = records[0]
        research = [item for item in record.get("research") or [] if item.get("score") is not None]
        news = [item for item in record.get("news") or [] if item.get("title")]
        observations = [item for item in record.get("observations") or [] if item.get("type")]
        return StockGraphContext(
            ticker=normalized,
            has_history=bool(research or news or observations),
            research=research,
            news=news,
            observations=observations,
            generated_at_ist=_now_ist().isoformat(),
        )

    def latest_research_summary(self) -> dict[str, Any] | None:
        records = self._run(
            """
            MATCH (r:ResearchRun)
            RETURN properties(r) AS properties
            ORDER BY coalesce(r.observed_at, r.ingested_at, "") DESC
            LIMIT 1
            """
        )
        if not records:
            return None
        props = dict(records[0].get("properties") or {})
        payload_json = props.get("payload_json")
        payload: dict[str, Any] = {}
        if payload_json:
            try:
                payload = json.loads(str(payload_json))
            except json.JSONDecodeError:
                payload = {}
        return {
            "scan_date": props.get("scan_date") or payload.get("scan_date"),
            "regime": payload.get("regime") or {"regime": props.get("regime")},
            "total_screened": props.get("total_screened") or payload.get("total_screened"),
            "qualified_count": props.get("qualified_count") or payload.get("qualified_count"),
            "shortlist_count": props.get("shortlist_count") or payload.get("shortlist_count"),
            "analyzed_at": props.get("observed_at"),
        }

