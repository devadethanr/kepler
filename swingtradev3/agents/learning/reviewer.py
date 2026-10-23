from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from pydantic import BaseModel

from cognition.llm_client import CognitionLLMClient
from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory.repository import MemoryRepository
from memory_views import MemoryViewClient

IST = ZoneInfo("Asia/Kolkata")


class TradeReviewSchema(BaseModel):
    observation: str
    lesson: str
    thesis_held: bool
    exit_reason: str


class TradeReviewerAgent(BaseAgent):
    """Review each newly closed trade and persist bounded graph memory."""

    def __init__(self, name: str = "TradeReviewer") -> None:
        super().__init__(name=name)

    async def review_pending(self, *, limit: int = 20) -> dict[str, object]:
        """Review every bounded, unreviewed closed trade in oldest-first order."""
        recent_trades = MemoryViewClient().recent_trades(limit=limit)
        completed: list[dict[str, object]] = []
        for trade in reversed(recent_trades):
            result = await self.review_trade(trade, recent_trades=recent_trades)
            if result.get("status") == "completed":
                completed.append(result)
        return {
            "status": "completed",
            "reviewed": len(completed),
            "trade_ids": [str(item["trade_id"]) for item in completed],
        }

    async def review_latest(self) -> dict[str, object]:
        memory_client = MemoryViewClient()
        recent_trades = memory_client.recent_trades(limit=20)
        if not recent_trades:
            return {"status": "no_trades"}

        return await self.review_trade(recent_trades[0], recent_trades=recent_trades)

    async def review_trade(
        self,
        trade: dict[str, object],
        *,
        recent_trades: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        """Review one closed trade idempotently."""
        memory_client = MemoryViewClient()
        recent_trades = recent_trades or [trade]

        payload = {**trade, **dict(trade.get("payload") or {})}
        trade_id = str(payload.get("trade_id") or "").strip()
        ticker = str(payload.get("ticker") or "UNKNOWN").strip().upper()
        if not trade_id:
            return {"status": "invalid_trade", "ticker": ticker}

        with session_scope() as session:
            repo = MemoryRepository(session)
            if repo.execution_event_exists(
                event_type="post_trade_review_completed",
                entity_type="trade",
                entity_id=trade_id,
            ):
                return {"status": "already_reviewed", "trade_id": trade_id, "ticker": ticker}

        research_context = memory_client.research_context_packet(
            ticker=ticker,
            setup_type=str(payload.get("setup_type") or "") or None,
        )
        review = await CognitionLLMClient(role="learning").generate_structured(
            prompt=json.dumps(
                {"trade": payload, "context": research_context},
                default=str,
            ),
            system_instruction=(
                "Review one closed NSE swing trade using only supplied evidence. Compare the "
                "outcome with the original thesis, entry timing, protection, and exit. Return a "
                "concise TradeReviewSchema. Do not propose or execute an order."
            ),
            response_model=TradeReviewSchema,
            fallback_factory=lambda: self._fallback_review(payload),
        )
        observed_at = datetime.now(IST)
        observation_id = f"trade_review:{trade_id}"
        review_payload = {
            "observation_id": observation_id,
            "trade_id": trade_id,
            "ticker": ticker,
            "review": review.model_dump(mode="json"),
            "trade": payload,
            "timestamp": observed_at.isoformat(),
        }
        graph_status = "written"
        graph: ContextGraphRepository | None = None
        try:
            graph = ContextGraphRepository()
            graph.record_observation(
                observation_type="trade_review",
                ticker=ticker,
                payload=review_payload,
                source="trade_reviewer",
            )
            graph.upsert_trade_memory(
                trade_id=trade_id,
                ticker=ticker,
                payload=review_payload,
                entry_price=float(payload.get("entry_price") or 0.0),
                exit_price=float(payload.get("exit_price") or 0.0),
                pnl_pct=float(payload.get("pnl_pct") or 0.0),
                setup_type=str(payload.get("setup_type") or "") or None,
                sector=str(payload.get("sector") or "") or None,
                observed_at=observed_at,
                similar_trade_ids=self._similar_trade_ids(payload, recent_trades),
                source="trade_reviewer",
            )
        except Exception:
            graph_status = "graph_unavailable"
        finally:
            if graph is not None:
                graph.close()

        with session_scope() as session:
            MemoryRepository(session).append_execution_event(
                event_type="post_trade_review_completed",
                entity_type="trade",
                entity_id=trade_id,
                source="trade_reviewer",
                payload={
                    "ticker": ticker,
                    "observation_id": observation_id,
                    "graph_status": graph_status,
                    "advisory_only": True,
                },
            )
        return {
            "status": "completed",
            "trade_id": trade_id,
            "ticker": ticker,
            "observation_id": observation_id,
            "graph_status": graph_status,
            "review": review.model_dump(mode="json"),
        }

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        result = await self.review_latest()
        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=json.dumps(result, default=str))],
            ),
        )

    @staticmethod
    def _fallback_review(payload: dict[str, object]) -> TradeReviewSchema:
        pnl_pct = float(payload.get("pnl_pct") or 0.0)
        exit_reason = str(payload.get("exit_reason") or "unknown")
        outcome = "profitable" if pnl_pct > 0 else "loss-making" if pnl_pct < 0 else "flat"
        return TradeReviewSchema(
            observation=f"Trade closed {outcome} at {pnl_pct:.2f}% via {exit_reason}.",
            lesson="Review thesis evidence and protection behavior before changing policy.",
            thesis_held=pnl_pct > 0,
            exit_reason=exit_reason,
        )

    @staticmethod
    def _similar_trade_ids(
        trade: dict[str, object],
        trades: list[dict[str, object]],
    ) -> list[str]:
        current_id = str(trade.get("trade_id") or "")
        setup_type = str(trade.get("setup_type") or "")
        sector = str(trade.get("sector") or "")
        similar: list[str] = []
        for row in trades[1:]:
            candidate = {**row, **dict(row.get("payload") or {})}
            candidate_id = str(candidate.get("trade_id") or "")
            if not candidate_id or candidate_id == current_id:
                continue
            if (setup_type and candidate.get("setup_type") == setup_type) or (
                sector and candidate.get("sector") == sector
            ):
                similar.append(candidate_id)
            if len(similar) >= 5:
                break
        return similar


learning_reviewer = TradeReviewerAgent()
