"""Classification is pure and does not perform model calls or mock a provider."""

from research_room.admission_errors import classify_model_admission_error
from research_room.store import RoomStopped


def denial(**changes):
    return {
        "kind": "model",
        "code": "call_limit",
        "role": "skeptic",
        "turn": 3,
        "reason": "Shared room model budget exhausted",
        **changes,
    }


def classify(error, *, role="skeptic", turn=3, recorded=None):
    return classify_model_admission_error(
        error, role=role, turn=turn, denial=denial() if recorded is None else recorded
    )


def test_explicit_marker_and_same_turn_produce_typed_limit():
    error = {"message": "Provider error: kepler_budget_exhausted", "httpStatusCode": 429}
    result = classify(error)
    assert isinstance(result, RoomStopped)
    assert result.code == "call_limit"
    assert str(result) == "Shared room model budget exhausted"


def test_captured_native_429_lacks_marker_and_stays_unclassified():
    # Exact turn.error shape observed in completed paired rooms.
    error = {
        "message": "exceeded retry limit, last status: 429 Too Many Requests",
        "codexErrorInfo": {"responseTooManyFailedAttempts": {"httpStatusCode": 429}},
        "additionalDetails": None,
        "misalignment": None,
    }
    assert classify(error) is None


def test_captured_real_codex_response_failure_preserves_marker():
    # Actual installed Codex 0.164.0 + Bridge, zero admission room, no model request.
    error = {
        "message": "stream disconnected before completion: kepler_budget_exhausted: Shared room model budget exhausted",
        "codexErrorInfo": "other",
        "additionalDetails": None,
        "misalignment": None,
    }
    assert classify(error).code == "call_limit"


def test_real_bridge_denied_stream_never_admits_or_connects_to_provider(store):
    import json
    from urllib.request import Request, ProxyHandler, build_opener
    from uuid import uuid4

    from research_room.adapter import Bridge
    from research_room.store import Budget

    room = store.create(
        "Protocol test only; no inference.",
        "Kepler",
        str(uuid4()),
        {"model": 0, "tool": 0, "seconds": 60},
    )
    store.claim("owner", 60)
    budget = Budget(store, room["id"], "owner")
    budget.model_roles = {"pinned": "analyst"}
    budget.begin_turn("analyst")
    bridge = Bridge({}, budget)
    bridge.allowed = {}
    try:
        port = bridge.start(0, "pinned", 1)  # Unreachable provider; admission must prevent access.
        payload = {
            "model": "pinned",
            "input": [{"role": "user", "content": "No inference."}],
            "tools": [],
        }
        request = Request(
            f"http://127.0.0.1:{port}/v1/responses",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with build_opener(ProxyHandler({})).open(request, timeout=3) as response:
            body = response.read().decode()
        assert '"code": "server_error"' in body
        assert '"type": "response.failed"' in body
        assert "kepler_budget_exhausted" in body
        assert store.get(room["id"])["counts"]["model"] == 0
        assert budget.limiting_denial["role"] == "analyst"
    finally:
        bridge.close()


def test_unrelated_or_stale_error_cannot_inherit_a_denial():
    marker = {"error": {"code": "kepler_budget_exhausted"}}
    assert classify(marker, role="analyst") is None
    assert classify(marker, turn=4) is None
    assert classify(marker, recorded=denial(kind="tool", code="tool_limit")) is None
    assert classify({"message": "network failure"}) is None
    assert classify({"message": "not_kepler_budget_exhausted_extra"}) is None
    assert classify_model_admission_error(marker, role="skeptic", turn=3, denial=None) is None


def test_peer_denial_does_not_overwrite_another_roles_causal_denial(store):
    from uuid import uuid4
    from research_room.store import Budget

    room = store.create(
        "Protocol-only exhausted room.",
        "Kepler",
        str(uuid4()),
        {"model": 0, "tool": 0, "seconds": 60},
    )
    store.claim("owner", 60)
    budget = Budget(store, room["id"], "owner")
    for role in ("analyst", "skeptic"):
        budget.begin_turn(role)
        assert not budget.admit("model", role=role)
    for role in ("analyst", "skeptic"):
        failure = classify_model_admission_error(
            {"message": "kepler_budget_exhausted"},
            role=role,
            turn=1,
            denial=budget.denial_for(role),
        )
        assert failure.code == "call_limit"
    budget.begin_turn("analyst")
    assert budget.denial_for("analyst") is None
    assert budget.denial_for("skeptic")["turn"] == 1
