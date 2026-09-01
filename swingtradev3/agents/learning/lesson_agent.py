from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncGenerator, Literal
from zoneinfo import ZoneInfo

from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from pydantic import BaseModel, Field

from cognition.llm_client import CognitionLLMClient
from config import cfg
from context_graph.policy_proposal_writer import PolicyProposalWriter
from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory.repository import MemoryRepository
from memory_views import MemoryViewClient

IST = ZoneInfo("Asia/Kolkata")
PolicyKey = Literal[
    "min_score_threshold",
    "max_position_size_pct",
    "new_entries_enabled",
    "max_same_sector_positions",
    "trail_stop_at_pct",
    "trail_to_pct",
    "debate_top_n",
]


class PolicyProposalSchema(BaseModel):
    key: PolicyKey
    value: bool | int | float
    reason: str
    trade_ids: list[str] = Field(default_factory=list)


class LessonResponse(BaseModel):
    proposals: list[PolicyProposalSchema] = Field(default_factory=list)


class LessonAgent(BaseAgent):
    """Create bounded policy proposals from reviewed trades; never activate them."""

    def __init__(self, name: str = "LessonAgent") -> None:
        super().__init__(name=name)

    async def propose_monthly_overlays(self) -> dict[str, object]:
        period_id = datetime.now(IST).strftime("%Y-%m")
        with session_scope() as session:
            repo = MemoryRepository(session)
            if repo.execution_event_exists(
                event_type="monthly_policy_analysis_completed",
                entity_type="learning_period",
                entity_id=period_id,
            ):
                return {"status": "already_completed", "period": period_id}

        memory_views = MemoryViewClient()
        trades = [
            {**item, **dict(item.get("payload") or {})}
            for item in memory_views.recent_trades(limit=1000)
        ]
        if len(trades) < cfg.learning.min_trades_for_lesson:
            return {
                "status": "insufficient_trades",
                "trade_count": len(trades),
                "required": cfg.learning.min_trades_for_lesson,
            }

        lesson_context = memory_views.trade_lesson_context(limit=100)
        response = await CognitionLLMClient(role="learning").generate_structured(
            prompt=json.dumps(
                {"trades": trades, "memory": lesson_context},
                default=str,
            ),
            system_instruction=(
                "Act as a conservative policy analyst. Find repeated evidence across closed "
                "trades and graph observations. Return at most the configured number of bounded "
                "PolicyProposalSchema items. Use only allowed keys and cite trade IDs. Proposals "
                "remain inactive until an operator approves them. Do not edit files or policy."
            ),
            response_model=LessonResponse,
            fallback_factory=LessonResponse,
        )

        writer = PolicyProposalWriter()
        proposals: list[dict[str, object]] = []
        skipped_without_evidence = 0
        known_trade_ids = {
            str(trade.get("trade_id") or "")
            for trade in trades
            if str(trade.get("trade_id") or "")
        }
        graph_status = "written"
        graph: ContextGraphRepository | None = None
        try:
            graph = ContextGraphRepository()
        except Exception:
            graph_status = "graph_unavailable"

        for index, proposal in enumerate(
            response.proposals[: int(cfg.learning.max_lessons_per_month)],
            start=1,
        ):
            evidence_trade_ids = sorted(set(proposal.trade_ids) & known_trade_ids)
            if len(evidence_trade_ids) < 2:
                skipped_without_evidence += 1
                continue
            overlay = writer.propose_overlay(
                key=proposal.key,
                value=proposal.value,
                proposer="lesson_agent",
                reason=proposal.reason,
            )
            if not overlay:
                continue
            proposals.append(overlay)
            if graph is not None:
                try:
                    graph.upsert_lesson(
                        lesson_id=f"{period_id}:{proposal.key}:{index}",
                        lesson_text=proposal.reason,
                        category="policy_proposal",
                        observation_ids=self._observation_ids(
                            lesson_context,
                            evidence_trade_ids,
                        ),
                        payload={
                            **proposal.model_dump(mode="json"),
                            "overlay_id": overlay.get("overlay_id"),
                            "advisory_only": True,
                        },
                        observed_at=datetime.now(IST),
                        source="lesson_agent",
                    )
                except Exception:
                    graph_status = "graph_unavailable"
        if graph is not None:
            graph.close()

        with session_scope() as session:
            MemoryRepository(session).append_execution_event(
                event_type="monthly_policy_analysis_completed",
                entity_type="learning_period",
                entity_id=period_id,
                source="lesson_agent",
                payload={
                    "proposal_count": len(proposals),
                    "proposal_ids": [item.get("overlay_id") for item in proposals],
                    "graph_status": graph_status,
                    "skipped_without_evidence": skipped_without_evidence,
                    "requires_operator_approval": True,
                },
            )
        return {
            "status": "completed",
            "period": period_id,
            "proposal_count": len(proposals),
            "proposals": proposals,
            "graph_status": graph_status,
            "skipped_without_evidence": skipped_without_evidence,
        }

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        result = await self.propose_monthly_overlays()
        yield Event(
            author=self.name,
            content=types.Content(
                role="assistant",
                parts=[types.Part(text=json.dumps(result, default=str))],
            ),
        )

    @staticmethod
    def _observation_ids(
        lesson_context: dict[str, list[dict[str, object]]],
        trade_ids: list[str],
    ) -> list[str]:
        wanted = {str(trade_id) for trade_id in trade_ids}
        matched: list[str] = []
        for observation in lesson_context.get("observations", []):
            payload = observation.get("payload")
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    payload = {}
            if not isinstance(payload, dict):
                continue
            if str(payload.get("trade_id") or "") not in wanted:
                continue
            observation_id = str(observation.get("id") or "").removeprefix("observation:")
            if observation_id:
                matched.append(observation_id)
        return matched


lesson_agent = LessonAgent()
