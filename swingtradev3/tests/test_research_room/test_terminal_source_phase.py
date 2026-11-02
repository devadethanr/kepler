"""Real durable admission/publication sequences, without inference or broker access."""

from uuid import uuid4

from research_room.store import Budget
from research_room.worker import no_mail_reason


def setup(store):
    room = store.create(
        "Which records are available?", "ACME", str(uuid4()), {"model": 4, "tool": 1, "seconds": 60}
    )
    store.claim("worker", 60)
    budget = Budget(store, room["id"], "worker")
    budget.begin_turn("analyst")
    assert budget.admit("tool", role="analyst")
    budget.release("tool")
    assert not budget.admit("tool", role="analyst")
    return room, budget


def test_denied_tool_then_normal_silent_no_mail_records_actual_limit(store):
    room, budget = setup(store)
    reason, code = no_mail_reason(budget, [])
    assert code == "tool_limit"
    assert "tool budget" in reason
    store.finish(room["id"], "worker", "abstention", reason, reason_code=code)
    assert store.get(room["id"])["termination_reason"] == "tool_limit"
    assert store.events(room["id"])[-1]["data"]["reason_code"] == "tool_limit"


def test_later_publication_and_later_turn_do_not_inherit_old_denial(store):
    room, budget = setup(store)
    message = store.event(room["id"], "worker", "publication", "message", {"text": "later"})
    assert no_mail_reason(budget, [message])[1] == "no_pending_mail"
    budget.begin_turn("analyst")
    assert no_mail_reason(budget, [])[1] == "no_pending_mail"
    store.finish(
        room["id"], "worker", "failed", "unrelated process failure", reason_code="peer_failure"
    )
    assert store.get(room["id"])["status"] == "failed"
    assert store.get(room["id"])["termination_reason"] == "peer_failure"


def test_cancel_and_outcome_keep_precedence_over_denial(store):
    room, budget = setup(store)
    store.cancel(room["id"])
    reason, code = no_mail_reason(budget, [])
    store.finish(room["id"], "worker", "abstention", reason, reason_code=code)
    assert store.get(room["id"])["termination_reason"] == "cancelled"

    room, _ = setup(store)
    store.finish(room["id"], "worker", "conclusion", "Valid causal outcome", reason_code="outcome")
    assert store.get(room["id"])["termination_reason"] == "outcome"
