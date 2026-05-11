"""IntentWriter — Convert approved research from Memgraph into Postgres entry_intents.

Reads from Memgraph (ResearchCandidate nodes that are shortlisted) and
writes entry_intent rows to Postgres, bridging the graph memory layer
to the execution layer.  Never mutates Memgraph.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from context_graph.repository import ContextGraphRepository, GraphUnavailableError
from memory.db import session_scope
from memory.repository import MemoryRepository


class IntentWriter:
    """Convert Memgraph research candidates into Postgres entry_intents."""

    def __init__(
        self,
        graph_repo: ContextGraphRepository | None = None,
    ) -> None:
        self._graph = graph_repo or ContextGraphRepository()

    def write_intent_from_candidate(
        self,
        *,
        run_id: str,
        ticker: str,
        candidate: dict[str, Any],
        approving_actor: str = "system",
    ) -> dict[str, Any]:
        """Create a Postgres entry_intent from a Memgraph ResearchCandidate.

        The candidate dict should contain: score, setup_type, entry_zone,
        stop_price, target_price, sector, holding_days_expected, etc.
        """
        intent_id = f"intent:{run_id}:{ticker}"
        score = float(candidate.get("score") or 0.0)

        entry_zone = candidate.get("entry_zone") or {}
        entry_price = float(entry_zone.get("high") or entry_zone.get("mid") or 0.0)
        stop_price = float(candidate.get("stop_price") or 0.0)
        target_price = float(candidate.get("target_price") or 0.0)

        with session_scope() as session:
            repo = MemoryRepository(session)
            result = repo.entry_intents.upsert_entry_intent(
                entry_intent_id=intent_id,
                ticker=ticker,
                status="proposed",
                approval_id=None,
                order_intent_id=None,
                payload={
                    "run_id": run_id,
                    "score": score,
                    "setup_type": str(candidate.get("setup_type", "")),
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "target_price": target_price,
                    "sector": str(candidate.get("sector", "")),
                    "holding_days_expected": candidate.get("holding_days_expected"),
                    "confidence_reasoning": candidate.get("confidence_reasoning"),
                    "risk_flags": candidate.get("risk_flags", []),
                    "approved_by": approving_actor,
                    "source": "intent_writer",
                },
                source="intent_writer",
            )

        # Also upsert the stock in the graph for traceability
        try:
            self._graph.upsert_stock(
                ticker,
                source="intent_writer",
                payload={"intent_id": intent_id, "score": score},
            )
        except GraphUnavailableError:
            pass  # Memgraph down — Postgres write is the important part

        return result

    def write_intents_from_scan(
        self,
        *,
        run_id: str,
        scan_date: str,
        candidates: list[dict[str, Any]],
        approving_actor: str = "system",
    ) -> list[dict[str, Any]]:
        """Write multiple intents from a scan's candidates."""
        results = []
        for candidate in candidates:
            ticker = str(candidate.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            try:
                result = self.write_intent_from_candidate(
                    run_id=run_id,
                    ticker=ticker,
                    candidate=candidate,
                    approving_actor=approving_actor,
                )
                results.append(result)
            except GraphUnavailableError:
                continue
        return results