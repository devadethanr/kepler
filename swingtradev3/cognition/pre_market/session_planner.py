from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import cfg, runtime_flags
from cognition.types import SessionExecutionPlan, SessionPlanItem
from memory.db import session_scope
from memory.repository import MemoryRepository
from memory_views import MemoryViewClient


IST = ZoneInfo("Asia/Kolkata")
SOURCE = "phase13_session_planner"


class SessionPlanner:
    """Pre-market activation planner for operator-approved Phase 13 intents."""

    def __init__(self, memory_views: MemoryViewClient | None = None) -> None:
        self._memory_views = memory_views or MemoryViewClient()

    def build_plan(
        self,
        *,
        trading_date: date | str | None = None,
        approvals: list[dict[str, Any]] | None = None,
        apply: bool = False,
        persist: bool = True,
    ) -> SessionExecutionPlan:
        generated_at = datetime.now(IST)
        trading_day = _parse_trading_date(trading_date) or generated_at.date()
        session_readiness = self._safe_session_readiness()
        portfolio_snapshot = self._safe_portfolio_snapshot()
        effective_policy = self._safe_effective_policy()
        approved = approvals if approvals is not None else self._approved_approvals()

        blocked_reasons = self._blocked_reasons(
            session_readiness=session_readiness,
            portfolio_snapshot=portfolio_snapshot,
            effective_policy=effective_policy,
        )

        items: list[SessionPlanItem] = []
        for approval in approved:
            ticker = str(approval.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            if blocked_reasons:
                action = "defer"
                reason = "; ".join(blocked_reasons)
            elif not _has_cash_for_minimum_entry(approval, portfolio_snapshot):
                action = "defer"
                reason = "insufficient_cash_for_minimum_entry"
            else:
                action = "activate"
                reason = "approved_intent_ready_for_session_activation"
            items.append(
                SessionPlanItem(
                    entry_intent_id=approval.get("entry_intent_id"),
                    approval_id=approval.get("approval_id"),
                    order_intent_id=approval.get("order_intent_id"),
                    ticker=ticker,
                    action=action,
                    reason=reason,
                    payload=dict(approval),
                )
            )

        status = _plan_status(items, blocked_reasons, apply)
        plan = SessionExecutionPlan(
            plan_id=f"session-plan:{trading_day.isoformat()}:{generated_at.strftime('%H%M%S')}",
            trading_date=trading_day.isoformat(),
            status=status,
            generated_at=generated_at,
            items=items,
            blocked_reasons=blocked_reasons,
            session_readiness=session_readiness,
        )

        if persist:
            self._persist_plan(plan)
        if apply and not blocked_reasons:
            self._apply_plan(plan)
        return plan

    def _approved_approvals(self) -> list[dict[str, Any]]:
        with session_scope() as session:
            approvals = MemoryRepository(session).get_pending_approvals_payload()
        return [
            approval
            for approval in approvals
            if approval.get("approved") is True
            and str(approval.get("status") or "").lower() in {"approved", "pending"}
        ]

    def _safe_session_readiness(self) -> dict[str, Any]:
        try:
            return dict(self._memory_views.session_readiness() or {})
        except Exception as exc:
            return {"status": "degraded", "reason": exc.__class__.__name__}

    def _safe_portfolio_snapshot(self) -> dict[str, Any]:
        try:
            return dict(self._memory_views.portfolio_risk_snapshot() or {})
        except Exception:
            return {}

    def _safe_effective_policy(self) -> dict[str, Any]:
        try:
            return dict(self._memory_views.effective_policy() or {})
        except Exception:
            return {}

    def _blocked_reasons(
        self,
        *,
        session_readiness: dict[str, Any],
        portfolio_snapshot: dict[str, Any],
        effective_policy: dict[str, Any],
    ) -> list[str]:
        del portfolio_snapshot
        reasons: list[str] = []
        live_block = runtime_flags.live_entry_block_reason(cfg.trading.mode)
        if live_block:
            reasons.append(live_block)
        if runtime_flags.exit_only_mode:
            reasons.append("EXIT_ONLY_MODE=true")
        if effective_policy and not bool(effective_policy.get("new_entries_enabled", True)):
            reasons.append("effective_policy:new_entries_enabled=false")
        if bool(session_readiness.get("exit_only_mode") is True):
            reasons.append("session_readiness:exit_only_mode=true")
        if bool(session_readiness.get("block_new_entries") is True):
            reasons.append("session_readiness:block_new_entries=true")
        worker_status = session_readiness.get("worker_status")
        if isinstance(worker_status, dict) and worker_status.get("status") == "degraded":
            reasons.append("session_readiness:worker_degraded")
        return sorted(set(reasons))

    def _persist_plan(self, plan: SessionExecutionPlan) -> None:
        with session_scope() as session:
            MemoryRepository(session).upsert_session_execution_plan(
                plan_id=plan.plan_id,
                trading_date=plan.trading_date,
                status=plan.status,
                payload=plan.model_dump(mode="json"),
                source=SOURCE,
            )

    def _apply_plan(self, plan: SessionExecutionPlan) -> None:
        with session_scope() as session:
            repo = MemoryRepository(session)
            for item in plan.items:
                if item.action != "activate" or not item.order_intent_id:
                    continue
                approval_payload = dict(item.payload)
                approval_payload["approved"] = True
                approval_payload["execution_requested"] = True
                approval_payload["execution_request_id"] = item.order_intent_id.rsplit(":", 1)[-1]
                approval_payload["status"] = "queued"
                repo.update_approval_payload(
                    str(item.approval_id),
                    approval_payload,
                    source=SOURCE,
                )
                repo.upsert_order_intent(
                    order_intent_id=str(item.order_intent_id),
                    ticker=item.ticker,
                    status="queued",
                    approval_id=str(item.approval_id) if item.approval_id else None,
                    entry_intent_id=str(item.entry_intent_id) if item.entry_intent_id else None,
                    broker_order_id=None,
                    broker_tag=approval_payload.get("broker_tag"),
                    payload=approval_payload,
                    source=SOURCE,
                )


def _parse_trading_date(value: date | str | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _has_cash_for_minimum_entry(
    approval: dict[str, Any],
    portfolio_snapshot: dict[str, Any],
) -> bool:
    cash = _to_float(portfolio_snapshot.get("cash_inr"))
    if cash is None:
        return True
    entry_zone = dict(approval.get("entry_zone") or {})
    entry = _to_float(entry_zone.get("high") or entry_zone.get("low"))
    if entry is None or entry <= 0:
        return False
    return cash >= entry


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _plan_status(
    items: list[SessionPlanItem],
    blocked_reasons: list[str],
    apply: bool,
) -> str:
    if not items:
        return "empty"
    if blocked_reasons:
        return "blocked"
    if apply and any(item.action == "activate" for item in items):
        return "applied"
    if any(item.action == "activate" for item in items):
        return "ready"
    return "deferred"

