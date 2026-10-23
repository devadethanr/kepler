"""PolicyProposalWriter — Convert graph/learning insights into Postgres policy_overlay candidates.

Reads patterns from Memgraph (FailurePattern, Observation, Lesson nodes)
and writes policy_overlay proposals to Postgres for operator review.
Never mutates config.yaml directly.
"""

from __future__ import annotations

import json
from typing import Any

from context_graph.context_builder import ContextBuilder
from context_graph.repository import ContextGraphRepository
from memory.db import session_scope
from memory.repository import MemoryRepository
from policy.governor import PolicyGovernor


class PolicyProposalWriter:
    """Generate policy overlay proposals from graph learning."""

    def __init__(
        self,
        graph_repo: ContextGraphRepository | None = None,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self._builder = context_builder or ContextBuilder(graph_repo or ContextGraphRepository())

    def propose_from_failure_patterns(
        self,
        *,
        proposer: str = "system",
        reason: str = "auto_proposed_from_failure_patterns",
    ) -> list[dict[str, Any]]:
        """Scan failure patterns and propose overlays if thresholds are breached."""
        patterns = self._get_failure_patterns()
        proposals = []
        for pattern in patterns:
            event_type = pattern.get("event_type", "")
            severity = pattern.get("severity", "")

            if "order_submission" in event_type.lower() and severity == "critical":
                proposal = self.propose_overlay(
                    key="max_position_size_pct",
                    value=5.0,  # reduce risk
                    proposer=proposer,
                    reason=f"auto: repeated order failures detected — {pattern.get('label', '')}",
                )
                if proposal:
                    proposals.append(proposal)

            if "reconcile" in event_type.lower() or "connection" in event_type.lower():
                proposal = self.propose_overlay(
                    key="new_entries_enabled",
                    value=False,
                    proposer=proposer,
                    reason=f"auto: reliability issue detected — {pattern.get('label', '')}",
                )
                if proposal:
                    proposals.append(proposal)

        return proposals

    def propose_from_observations(
        self,
        *,
        proposer: str = "system",
    ) -> list[dict[str, Any]]:
        """Review recent observations for actionable pattern insights."""
        observations = self._get_recent_observations()
        proposals = []

        # If many observations mention sector concentration, propose a cap
        sector_mentions = {}
        for obs in observations:
            payload = self._parse_payload(obs.get("payload") or {})
            sector = str(payload.get("sector") or "")
            if sector:
                sector_mentions[sector] = sector_mentions.get(sector, 0) + 1

        for sector, count in sector_mentions.items():
            if count >= 3:
                proposal = self.propose_overlay(
                    key="max_same_sector_positions",
                    value=max(1, 5 - count),
                    proposer=proposer,
                    reason=f"auto: high concentration in {sector} from observations",
                )
                if proposal:
                    proposals.append(proposal)

        return proposals

    def propose_trail_adjustment(
        self,
        *,
        proposer: str = "system",
    ) -> list[dict[str, Any]]:
        """Analyze trade outcomes to propose trailing threshold changes."""
        trades = self._get_recent_trades()
        if len(trades) < 5:
            return []

        wins = [t for t in trades if float(t.get("pnl_pct") or 0) > 0]
        losses = [t for t in trades if float(t.get("pnl_pct") or 0) <= 0]

        proposals = []
        if len(losses) > len(wins) * 2 and len(trades) >= 8:
            # Many losses — tighten stop
            proposal = self.propose_overlay(
                key="trail_stop_at_pct",
                value=3.0,
                proposer=proposer,
                reason="auto: high loss ratio, tightening trailing stop",
            )
            if proposal:
                proposals.append(proposal)

        return proposals

    # ── helpers ──────────────────────────────────────────────────────

    def _get_failure_patterns(self) -> list[dict[str, Any]]:
        return self._builder.get_failure_patterns()

    def _get_recent_observations(self) -> list[dict[str, Any]]:
        return self._builder.get_recent_observations()

    def _parse_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str) and payload.strip():
            try:
                parsed = json.loads(payload)
            except json.JSONDecodeError:
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

    def _get_recent_trades(self) -> list[dict[str, Any]]:
        try:
            with session_scope() as session:
                repo = MemoryRepository(session)
                return repo.trades.get_trades_payload()[-20:]
        except Exception:
            return []

    def propose_overlay(
        self,
        *,
        key: str,
        value: Any,
        proposer: str,
        reason: str,
    ) -> dict[str, Any] | None:
        try:
            governor = PolicyGovernor()
            overlay = governor.propose_overlay(
                key=key,
                value=value,
                reason=reason,
                proposer=proposer,
            )
            return overlay.model_dump(mode="json")
        except Exception:
            return None
