from types import SimpleNamespace
from uuid import uuid4

import pytest

from research_room.grounding import metadata_policy, packet, validate_claims
from research_room.store import Budget
from research_room.tools import Gateway, _browser_excerpt


def gateway(root, store):
    room = store.create(
        "What does ACME report?", "ACME", str(uuid4()), {"model": 2, "tool": 10, "seconds": 60}
    )
    store.claim("owner", 30)
    return Gateway(
        SimpleNamespace(artifact_root=root, workspace_target="Kepler", max_messages=12),
        store,
        room,
        "owner",
        Budget(store, room["id"], "owner"),
    )


def test_original_path_rejects_hidden_and_directory_symlinks(tmp_path, store):
    hidden = tmp_path / ".secret"
    hidden.mkdir()
    (hidden / "dummy.md").write_text("ACME dummy private content")
    (tmp_path / "visible.md").symlink_to(hidden / "dummy.md")
    (tmp_path / "linked").symlink_to(hidden, target_is_directory=True)
    g = gateway(tmp_path, store)
    for path in ("visible.md", "linked/dummy.md", ".secret/dummy.md"):
        with pytest.raises((OSError, ValueError)):
            g._read(path)


def test_paged_retrieval_and_model_proposal_never_verifies_narrative(tmp_path, store):
    (tmp_path / "dummy.md").write_text("ACME reports earnings. " + "x" * 9000)
    g = gateway(tmp_path, store)
    page = g.dispatch("analyst", "r1", "artifact_read", {"path": "dummy.md"})
    assert page["retrieval"]["truncated"]
    assert page["retrieval"]["next_offset"] == 6000
    second = g.dispatch(
        "analyst", "r2", "artifact_read_more", {"path": "dummy.md", "offset": "6000"}
    )
    assert second["retrieval"]["offset"] == 6000
    search = g.dispatch("analyst", "s1", "artifact_search", {"query": "earnings"})
    assert search["retrieval"]["scan_limit"] == 2000
    assert "unknown" in search["retrieval"]["completeness"]
    item = page["evidence"][0]
    args = {
        "recipient": "skeptic",
        "text": "ACME caused a disruption.",
        "position": "conclude",
        "quote_id": item["quote_spans"][0]["id"],
        "claim_kind": "inference",
        "support_assessment": "supported",
        "event_id": "",
    }
    g._message("analyst", "m1", args)
    claim = g.store.events(g.room["id"])[-1]["data"]["claims"][0]
    assert claim["support_assessment"] == "supported"
    assert claim["assessment_origin"] == "model proposal"
    assert claim["narrative_verification"] == "unassessed"
    with pytest.raises(ValueError, match="Event identity"):
        g._message("skeptic", "m2", {**args, "recipient": "analyst", "event_id": "invented"})


def test_known_cutoff_and_record_identity():
    evidence = packet(
        "ACME",
        "dummy",
        "ACME reports earnings.",
        record_id="r1",
        event_id="e1",
        published_at="2025-02-01T00:00:00Z",
        decision_cutoff="2025-01-01T00:00:00Z",
    )
    assert evidence["record_id"] == "r1" and evidence["event_id"] == "e1"
    assert evidence["freshness"] == "future"
    other = packet("ACME", "dummy", "ACME reports earnings.", record_id="r2")
    assert evidence["quote_spans"][0]["id"] != other["quote_spans"][0]["id"]
    with pytest.raises(ValueError, match="publication"):
        validate_claims(
            "ACME",
            [{"evidence_id": evidence["id"], "quote": evidence["quote_spans"][0]["id"]}],
            {evidence["id"]: evidence},
        )


def test_deterministic_freshness_and_future_scheduled_event():
    cutoff = "2025-03-01T00:00:00Z"
    assert metadata_policy(decision_cutoff=cutoff)["freshness"] == "unknown"
    assert (
        metadata_policy(published_at="2025-02-15T00:00:00Z", decision_cutoff=cutoff)["freshness"]
        == "current"
    )
    assert (
        metadata_policy(published_at="2024-12-01T00:00:00Z", decision_cutoff=cutoff)["freshness"]
        == "stale"
    )
    item = packet(
        "ACME",
        "https://example.test",
        "ACME schedules a future meeting.",
        published_at="2025-02-15T00:00:00Z",
        event_at="2025-04-01T00:00:00Z",
        decision_cutoff=cutoff,
    )
    assert item["source_type"] == "public_html"
    assert item["metadata_policy"]["event"] == "after_cutoff"
    assert item["metadata_policy"]["event_occurred_by_cutoff"] is False
    assert validate_claims(
        "ACME",
        [{"evidence_id": item["id"], "quote": item["quote_spans"][0]["id"]}],
        {item["id"]: item},
    )


def test_browser_paging_exposes_capture_limit():
    text = "ACME " + "x" * 5995 + "ACME " + "y" * 5995
    retrieval = {"truncated": True, "completeness": "unknown"}
    _, first = _browser_excerpt(text, retrieval, 0)
    assert first["next_offset"] == 6000
    _, second = _browser_excerpt(text, retrieval, 6000)
    assert second["next_offset"] is None
    assert second["truncated"] is True
