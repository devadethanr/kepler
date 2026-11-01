from uuid import uuid4

from memory.models import CognitionRunRow


def create(store):
    return store.create(
        "What evidence supports ACME?",
        "ACME",
        str(uuid4()),
        {"model": 2, "tool": 2, "seconds": 60},
    )


def test_queued_cancel_is_terminal_once_and_persisted(store):
    room = create(store)
    assert store.cancel(room["id"])["status"] == "cancelled"
    store.cancel(room["id"])
    store.finish(room["id"], "old", "conclusion", "late")
    events = store.events(room["id"])
    assert [e["kind"] for e in events] == ["room.created", "room.cancel_requested", "room.finished"]
    assert events[-1]["data"]["status"] == "cancelled"
    with store.scope() as session:
        assert session.get(CognitionRunRow, room["id"]).completed_at is not None


def test_expired_lease_reconciles_unresolved_work_without_inventing_usage(store):
    room = create(store)
    store.claim("owner", 60)
    store.admit(room["id"], "owner", "model")
    store.admit(room["id"], "owner", "tool")
    with store.scope() as session:
        row = session.get(CognitionRunRow, room["id"])
        row.payload = {**row.payload, "lease_until": 0}
    stale = store.get(room["id"])
    assert stale["worker_state"] == "stale" and stale["active"] is None
    store.finish(room["id"], "owner", "conclusion", "late")
    store.release(room["id"], "owner", "model", {"input_tokens": 100})
    assert store.claim("replacement", 60) is None
    recovered = store.get(room["id"])
    assert recovered["status"] == "interrupted"
    assert recovered["active"] == {"model": 0, "tool": 0}
    assert recovered["unresolved_activity"] == {"model": 1, "tool": 1}
    assert recovered["counts"]["unknown_usage_calls"] == 1
    assert recovered["counts"]["input_tokens"] == 0
    store.release(room["id"], "owner", "model")
    assert store.get(room["id"])["counts"]["unknown_usage_calls"] == 1
    assert sum(e["kind"] == "room.finished" for e in store.events(room["id"])) == 1
