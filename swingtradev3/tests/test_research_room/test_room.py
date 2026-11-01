from uuid import uuid4

import pytest

from research_room.adapter import Bridge
from research_room.grounding import packet, scoped_records, validate_claims
from research_room.store import Budget, RoomStopped
from research_room.worker import outcome


def create(store):
    return store.create(
        "What evidence supports ACME?", "ACME", str(uuid4()), {"model": 2, "tool": 2, "seconds": 60}
    )


def test_durable_replay_idempotency_budget_and_cancel(store):
    room = create(store)
    assert store.claim("worker", 30)["id"] == room["id"]
    assert store.claim("other", 30) is None
    budget = Budget(store, room["id"], "worker")
    assert budget.admit("model")
    budget.release("model", {"input_tokens": 21, "output_tokens": 4})
    assert budget.admit("model")
    budget.release("model")
    assert not budget.admit("model")
    state = store.get(room["id"])
    assert state["counts"]["reserved_tokens"] == 65536
    assert state["counts"]["input_tokens"] == 21
    assert state["counts"]["unknown_usage_calls"] == 1
    first = store.event(room["id"], "worker", "unique", "message", {"text": "once"})
    assert store.event(room["id"], "worker", "unique", "message", {"text": "once"}) == first
    assert store.events(room["id"], first["seq"]) == []
    store.cancel(room["id"])
    with pytest.raises(RoomStopped):
        store.event(room["id"], "worker", "late", "message", {})
    store.finish(room["id"], "worker", "conclusion", "must not win cancel race")
    assert store.get(room["id"])["status"] == "cancelled"
    assert store.events(room["id"])[-1]["kind"] == "room.finished"


def test_expired_lease_is_interrupted_without_tool_replay(store):
    room = create(store)
    store.claim("dead", -1)
    assert store.claim("replacement", 30) is None
    assert store.get(room["id"])["status"] == "interrupted"
    with pytest.raises(RoomStopped):
        store.event(room["id"], "dead", "late", "tool.started", {})


def test_scope_preserves_contradictions_and_rejects_wrong_spans():
    records = [
        {"id": "a", "sources": ["ACME reports disruption", "ACME denies disruption"]},
        {"id": "b", "sources": ["BETA reports earnings"]},
    ]
    assert scoped_records(records, "a") == [records[0]]
    evidence = packet("ACME", "file:brief", "ACME reports disruption. ACME denies disruption.")
    cited = [{"evidence_id": evidence["id"], "quote": "ACME denies disruption."}]
    assert validate_claims("ACME", cited, {evidence["id"]: evidence})
    for claims in [
        [{"evidence_id": "fabricated", "quote": "ACME denies disruption."}],
        [{"evidence_id": evidence["id"], "quote": "ACME reports earnings."}],
    ]:
        with pytest.raises(ValueError):
            validate_claims("ACME", claims, {evidence["id"]: evidence})
    with pytest.raises(ValueError):
        validate_claims("BETA", cited, {evidence["id"]: evidence})


def test_adapter_preserves_roles_and_denies_unmatched_changed_cross_model_calls():
    bridge = Bridge({}, None)
    bridge.allowed = {"lookup": ("read", {"entity": {"type": "string"}})}
    payload = {
        "model": "pinned",
        "instructions": "trusted",
        "input": [
            {"role": "developer", "content": "prefix"},
            {"role": "user", "content": "untrusted"},
        ],
        "tools": [{"type": "function", "name": "lookup", "parameters": {}}],
    }
    chat = bridge.translate(payload, "pinned")
    assert chat["messages"][0] == {"role": "system", "content": "trusted\n\nprefix"}
    assert chat["messages"][1]["role"] == "user"
    assert chat["max_tokens"] == 512
    call = {
        "type": "function_call",
        "call_id": "c1",
        "name": "lookup",
        "arguments": '{"entity":"ACME"}',
    }
    result = {"type": "function_call_output", "call_id": "c1", "output": "real output"}
    with pytest.raises(ValueError):
        bridge.translate({**payload, "input": [result]}, "pinned")
    bridge.issued["c1"] = {**call, "model": "pinned"}
    assert (
        bridge.translate({**payload, "input": [call, result]}, "pinned")["messages"][-1]["role"]
        == "tool"
    )
    with pytest.raises(ValueError):
        bridge.translate({**payload, "input": [call, {**result, "output": "tampered"}]}, "pinned")
    with pytest.raises(ValueError):
        bridge.translate({**payload, "model": "other", "input": [call, result]}, "other")
    with pytest.raises(ValueError):
        bridge.translate({**payload, "tools": [{"type": "namespace", "name": "shell"}]}, "pinned")


def test_two_independent_conclusions_do_not_manufacture_consensus():
    a = {
        "id": "a",
        "agent": "analyst",
        "data": {"stance": "conclusion", "reply_to": "", "assessment": "none"},
    }
    b = {
        "id": "b",
        "agent": "skeptic",
        "data": {"stance": "conclusion", "reply_to": "", "assessment": "none"},
    }
    assert outcome([a, b]) is None
    b["data"].update(reply_to="a", assessment="supports")
    assert outcome([a, b]) == "conclusion"
    b["data"].update(stance="disagreement", assessment="objects")
    assert outcome([a, b]) == "disagreement"


def test_gateway_paths_replay_and_peer_citations(store, tmp_path):
    from types import SimpleNamespace
    from research_room.tools import Gateway

    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "brief.md").write_text(
        "ACME source reports a disruption.\n\nACME denies the disruption."
    )
    outside = tmp_path / "outside.md"
    outside.write_text("SECRET_SENTINEL")
    (root / "escape.md").symlink_to(outside)
    room = create(store)
    store.claim("worker", 30)
    gateway = Gateway(
        SimpleNamespace(artifact_root=root, workspace_target="Kepler", max_messages=12),
        store,
        room,
        "worker",
        Budget(store, room["id"], "worker"),
    )
    assert "denies" in gateway._read("brief.md")
    for path in ["../outside.md", "escape.md", ".env", str(outside)]:
        with pytest.raises(ValueError):
            gateway._read(path)
    params = {"tool": "artifact_read", "arguments": {"path": "brief.md"}, "callId": "original"}
    first = gateway.execute("analyst", params)
    assert first["status"] == "ok"
    assert gateway.execute("analyst", params) == first
    assert gateway.execute("skeptic", params)["status"] == "denied"
    assert (
        gateway.execute("analyst", {**params, "arguments": {"path": "escape.md"}})["status"]
        == "denied"
    )
    assert store.get(room["id"])["counts"]["tool"] == 1
    gateway.turn_reads["analyst"] = 4
    assert gateway.granted_tools("analyst") == {"room_message"}
    item = first["evidence"][0]
    copied = {
        "evidence_id": item["id"],
        "quote": "ACME denies the disruption.",
        "source": item["source"],
        "freshness": item["freshness"],
    }
    assert validate_claims("ACME", [copied], {item["id"]: item})
    with pytest.raises(ValueError):
        validate_claims("ACME", [{**copied, "source": "invented"}], {item["id"]: item})


def test_browser_refuses_private_hosts_credentials_ports_and_non_allowlisted_redirects():
    from research_room.browser import validate_url

    assert validate_url("https://www.sebi.gov.in/", ["www.sebi.gov.in"]) == ("www.sebi.gov.in", 443)
    for url in [
        "http://www.sebi.gov.in/",
        "https://127.0.0.1/",
        "https://169.254.169.254/",
        "https://user:pass@www.sebi.gov.in/",
        "https://www.sebi.gov.in:444/",
        "https://evil.example/",
    ]:
        with pytest.raises(ValueError):
            validate_url(url, ["www.sebi.gov.in"])


def test_adapter_validates_zero_argument_and_enum_tools():
    bridge = Bridge({}, None)
    bridge.allowed = {
        "discover": ("list", {}),
        "publish": ("say", {"stance": {"type": "string", "enum": ["abstention"]}}),
    }
    bridge.validate_arguments("discover", {})
    bridge.validate_arguments("publish", {"stance": "abstention"})
    for name, args in [
        ("discover", {"extra": "x"}),
        ("publish", {"stance": "continue"}),
        ("publish", {"stance": 1}),
        ("shell", {}),
    ]:
        with pytest.raises(ValueError):
            bridge.validate_arguments(name, args)


def test_quote_span_ids_resolve_to_exact_text_and_cannot_cross_sources():
    first = packet("ACME", "file:first", "ACME reports a disruption. ACME denies that claim.")
    second = packet("ACME", "file:second", "ACME reports earnings.")
    span = first["quote_spans"][0]
    resolved = validate_claims(
        "ACME", [{"evidence_id": first["id"], "quote": span["id"]}], {first["id"]: first}
    )
    assert resolved[0]["quote"] == span["text"]
    with pytest.raises(ValueError):
        validate_claims(
            "ACME", [{"evidence_id": second["id"], "quote": span["id"]}], {second["id"]: second}
        )


def test_addressed_publications_resolve_quotes_and_require_delivered_peer_agreement(
    store, tmp_path
):
    from types import SimpleNamespace
    from research_room.tools import Gateway

    room = create(store)
    store.claim("worker", 30)
    gateway = Gateway(
        SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler", max_messages=12),
        store,
        room,
        "worker",
        Budget(store, room["id"], "worker"),
    )
    item = gateway._evidence("file:brief", "ACME requires manual approval for all entries.")
    quote_id = item["quote_spans"][0]["id"]
    args = {
        "recipient": "skeptic",
        "text": "The source requires manual approval.",
        "quote_id": quote_id,
        "position": "conclude",
    }
    published = gateway.dispatch("analyst", "m1", "room_message", args)
    event = store.events(room["id"])[-1]
    assert event["data"]["claims"][0]["quote"] == "ACME requires manual approval for all entries."
    with pytest.raises(ValueError):
        gateway.dispatch(
            "skeptic", "m2", "room_message", {**args, "recipient": "analyst", "position": "agree"}
        )
    gateway.delivered["skeptic"] = published["message_id"]
    gateway.dispatch(
        "skeptic", "m3", "room_message", {**args, "recipient": "analyst", "position": "agree"}
    )
    assert store.events(room["id"])[-1]["data"]["reply_to"] == published["message_id"]
    assert outcome([event, store.events(room["id"])[-1]]) == "conclusion"


def test_gateway_missing_graph_and_unsupported_asof_fail_honestly(store, tmp_path, monkeypatch):
    from types import SimpleNamespace
    from config import cfg
    from research_room.tools import Gateway

    monkeypatch.setattr(cfg.context_graph, "enabled", False)
    room = create(store)
    store.claim("worker", 30)
    gateway = Gateway(
        SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler", max_messages=12),
        store,
        room,
        "worker",
        Budget(store, room["id"], "worker"),
    )
    historical = gateway.execute(
        "analyst",
        {
            "tool": "graph_lookup",
            "arguments": {"entity": "ACME", "as_of": "2020-01-01"},
            "callId": "historical",
        },
    )
    assert historical["status"] == "denied"
    missing = gateway.execute(
        "analyst", {"tool": "graph_lookup", "arguments": {"entity": "ACME"}, "callId": "missing"}
    )
    assert missing["status"] == "unavailable" and "evidence" not in missing
    gateway.close()


def test_future_and_unknown_inline_citations_are_refused(store, tmp_path):
    from types import SimpleNamespace
    from research_room.tools import Gateway

    future = packet("ACME", "future", "ACME reports earnings.", published_at="2099-01-01T00:00:00Z")
    with pytest.raises(ValueError):
        validate_claims(
            "ACME",
            [{"evidence_id": future["id"], "quote": "ACME reports earnings."}],
            {future["id"]: future},
        )
    room = create(store)
    store.claim("worker", 30)
    gateway = Gateway(
        SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler", max_messages=12),
        store,
        room,
        "worker",
        Budget(store, room["id"], "worker"),
    )
    with pytest.raises(ValueError):
        gateway.dispatch(
            "analyst",
            "fabricated",
            "room_message",
            {
                "recipient": "skeptic",
                "text": "Evidence ev:invented supports this claim.",
                "quote_id": "",
                "position": "question",
            },
        )
