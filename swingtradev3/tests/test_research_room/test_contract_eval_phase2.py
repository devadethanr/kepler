"""Evaluator observes real publication acceptance, not a gold-match acceptance rule."""

from types import SimpleNamespace
from uuid import uuid4

from research_room.contract_eval import score
from research_room.grounding import packet
from research_room.store import Budget
from research_room.tools import Gateway


def test_real_irrelevant_quote_does_not_become_truth_and_is_counted(store, tmp_path):
    room = store.create("Did ACME approve the merger?", "ACME", str(uuid4()),
                        {"model": 1, "tool": 2, "seconds": 60})
    store.claim("owner", 60)
    gateway = Gateway(SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler",
                                      max_messages=12), store, room, "owner",
                      Budget(store, room["id"], "owner"))
    evidence = packet("ACME", "file:unrelated", "ACME opened a warehouse.")
    gateway.evidence[evidence["id"]] = evidence
    args = {"recipient": "room", "text": "ACME approved the merger.",
            "quote_id": evidence["quote_spans"][0]["id"], "position": "question",
            "claim_kind": "observation", "support_assessment": "supported", "event_id": ""}
    output = gateway.execute("analyst", {"tool": "room_message", "arguments": args,
                                         "callId": "actual-irrelevant-proposal"})
    case = {"target_entity": "ACME", "event_id": None, "claim_text": args["text"],
            "expected": {"support_assessment": "insufficient", "claim_kind": "observation",
                         "relevant_sources": [], "uncertainty_required": True}}
    result = score(case, args, output, store.events(room["id"]), gateway.evidence)
    assert result["accepted"] and result["valid_quote"]
    assert result["unsupported_supported_proposal_accepted"]
    assert not result["fully_correct"] and not result["ui_truth_verified"]


def test_nonexistent_quote_is_counted_even_when_publication_is_rejected(store, tmp_path):
    room = store.create("What supports ACME?", "ACME", str(uuid4()),
                        {"model": 1, "tool": 1, "seconds": 60})
    store.claim("owner", 60)
    gateway = Gateway(SimpleNamespace(artifact_root=tmp_path, workspace_target="Kepler",
                                      max_messages=12), store, room, "owner",
                      Budget(store, room["id"], "owner"))
    args = {"recipient": "room", "text": "ACME approved the merger.", "position": "question",
            "quote_id": "q:doesnotexist", "claim_kind": "observation",
            "support_assessment": "supported", "event_id": ""}
    output = gateway.execute("analyst", {"tool": "room_message", "arguments": args,
                                         "callId": "bad-quote"})
    case = {"target_entity": "ACME", "event_id": None, "claim_text": args["text"],
            "expected": {"support_assessment": "insufficient", "claim_kind": "observation",
                         "relevant_sources": [], "uncertainty_required": True}}
    result = score(case, args, output, store.events(room["id"]), gateway.evidence)
    assert not result["accepted"] and result["nonexistent_citation"]
