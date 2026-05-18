from __future__ import annotations

from cognition.pre_market.session_planner import SessionPlanner


class PlannerMemoryViews:
    def __init__(self, *, blocked: bool = False, cash: float = 100000.0) -> None:
        self.blocked = blocked
        self.cash = cash

    def session_readiness(self):
        return {"block_new_entries": self.blocked, "exit_only_mode": False}

    def portfolio_risk_snapshot(self):
        return {"cash_inr": self.cash}

    def effective_policy(self):
        return {"new_entries_enabled": True}


def _approval() -> dict[str, object]:
    return {
        "approval_id": "approval:SBIN:phase13",
        "entry_intent_id": "entry-intent:SBIN:phase13",
        "order_intent_id": "order-intent:SBIN:phase13",
        "ticker": "SBIN",
        "approved": True,
        "status": "approved",
        "entry_zone": {"low": 100.0, "high": 105.0},
    }


def test_session_planner_marks_approved_intent_ready_for_activation():
    plan = SessionPlanner(memory_views=PlannerMemoryViews()).build_plan(
        trading_date="2026-05-17",
        approvals=[_approval()],
        persist=False,
    )

    assert plan.status == "ready"
    assert plan.items[0].action == "activate"


def test_session_planner_defers_when_session_readiness_blocks_entries():
    plan = SessionPlanner(memory_views=PlannerMemoryViews(blocked=True)).build_plan(
        trading_date="2026-05-17",
        approvals=[_approval()],
        persist=False,
    )

    assert plan.status == "blocked"
    assert plan.items[0].action == "defer"
    assert "session_readiness:block_new_entries=true" in plan.blocked_reasons


def test_session_planner_defers_when_cash_is_insufficient():
    plan = SessionPlanner(memory_views=PlannerMemoryViews(cash=50.0)).build_plan(
        trading_date="2026-05-17",
        approvals=[_approval()],
        persist=False,
    )

    assert plan.status == "deferred"
    assert plan.items[0].reason == "insufficient_cash_for_minimum_entry"

