"""Concrete conversation sequences and prompt peer shutdown without model calls."""

import threading
import time

import pytest

from research_room.worker import causal_outcome, initial_turns
from research_room.store import Budget
from uuid import uuid4


def message(ident, agent, stance, reply="", assessment="none"):
    return {"id": str(ident), "seq": ident, "agent": agent,
            "data": {"recipient": "skeptic" if agent == "analyst" else "analyst",
                     "kind": "challenge" if assessment == "objects" else "claim",
                     "stance": stance, "reply_to": str(reply), "assessment": assessment}}


def exchange(recipient, incoming, response):
    return {"recipient": recipient, "message_ids": [str(incoming)],
            "response_id": str(response)}


def test_latest_objection_waits_for_actual_recipient_response():
    public = [message(1, "analyst", "conclusion"),
              message(2, "skeptic", "continue"),
              message(3, "analyst", "conclusion", 2),
              message(4, "skeptic", "disagreement", 3, "objects")]
    exchanges = [exchange("analyst", 2, 3), exchange("skeptic", 3, 4)]
    assert causal_outcome(public, exchanges) is None
    # Delivery without a committed response is not a response opportunity completed.
    assert causal_outcome(public, exchanges + [exchange("analyst", 4, "missing")]) is None
    public.append(message(5, "analyst", "abstention", 4, "uncertain"))
    exchanges.append(exchange("analyst", 4, 5))
    assert causal_outcome(public, exchanges) == "disagreement"


def test_final_slot_agreement_and_unresolved_objection_are_distinct():
    public = [message(1, "analyst", "conclusion"),
              message(2, "skeptic", "continue"),
              message(3, "analyst", "conclusion", 2),
              message(4, "skeptic", "conclusion", 3, "supports")]
    exchanges = [exchange("analyst", 2, 3), exchange("skeptic", 3, 4)]
    # This sequence is valid even if message four consumes the last allowed slot.
    assert causal_outcome(public, exchanges) == "conclusion"
    public[-1] = message(4, "skeptic", "disagreement", 3, "objects")
    assert causal_outcome(public, exchanges) is None


def test_final_slot_can_acknowledge_initial_proposal_without_redundant_turn():
    public = [message(1, "analyst", "conclusion"),
              message(2, "skeptic", "continue"),
              message(3, "skeptic", "conclusion", 1, "supports")]
    assert causal_outcome(public, [exchange("skeptic", 1, 3)]) == "conclusion"


def test_budget_denial_preserves_specific_continuation_exhaustion(store):
    room = store.create("What supports ACME?", "ACME", str(uuid4()),
                        {"model": 1, "tool": 2, "seconds": 60})
    store.claim("owner", 60)
    budget = Budget(store, room["id"], "owner")
    assert budget.admit("model")
    budget.release("model", {"input_tokens": 4, "output_tokens": 5})
    assert not budget.admit("model")
    assert "budget" in budget.last_denial
    assert store.get(room["id"])["counts"]["model"] == 1


def test_direct_id_retains_access_beyond_newest_thirty(store):
    first = None
    for _ in range(31):
        room = store.create("What supports ACME?", "ACME", str(uuid4()),
                            {"model": 1, "tool": 1, "seconds": 60})
        first = first or room["id"]
        store.cancel(room["id"])
    assert len(store.list()) == 30
    assert first not in {r["id"] for r in store.list()}
    assert store.get(first)["status"] == "cancelled"


@pytest.mark.parametrize("failing_role", [0, 1])
def test_initial_failure_signals_peer_without_role_order_wait(failing_role):
    stop = threading.Event()
    peer_started = threading.Event()
    peer_stopped = threading.Event()

    def peer():
        peer_started.set()
        assert stop.wait(2), "peer was not promptly signalled"
        peer_stopped.set()

    def failure():
        assert peer_started.wait(1)
        raise RuntimeError("participant failed")

    tasks = [peer, peer]
    tasks[failing_role] = failure
    start = time.monotonic()
    with pytest.raises(RuntimeError, match="participant failed"):
        initial_turns(tasks, stop)
    assert peer_stopped.is_set()
    assert time.monotonic() - start < 1.5
