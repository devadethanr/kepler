from types import SimpleNamespace
from uuid import uuid4

from research_room.grounding import packet
from research_room.iteration_scoring import score_v2
from research_room.store import Budget
from research_room.tools import Gateway


def setup_room(store, tmp_path):
    room = store.create(
        "What does the report say?",
        "Example",
        str(uuid4()),
        {"model": 1, "tool": 10, "seconds": 60},
    )
    store.claim("owner", 60)
    gateway = Gateway(
        SimpleNamespace(artifact_root=tmp_path, workspace_target="Example", max_messages=12),
        store,
        room,
        "owner",
        Budget(store, room["id"], "owner"),
    )
    return room, gateway


def proposal(text, quote_id, assessment="supported"):
    return {
        "recipient": "room",
        "text": text,
        "position": "question",
        "quote_id": quote_id,
        "claim_kind": "observation",
        "support_assessment": assessment,
        "event_id": "",
    }


def case(assessment, quotes):
    return {
        "target_entity": "Example",
        "event_id": None,
        "claim_text": "Example increased output.",
        "expected": {
            "support_assessment": assessment,
            "claim_kind": "observation",
            "relevant_sources": list(quotes),
            "allowed_quotes": quotes,
            "wrong_entity_sources": [],
            "wrong_event_sources": [],
            "uncertainty_required": assessment != "supported",
        },
    }


def publish(store, room, gateway, args):
    output = gateway.execute(
        "analyst", {"tool": "room_message", "arguments": args, "callId": str(uuid4())}
    )
    return output, store.events(room["id"])


def test_gold_span_not_just_source_and_actual_scope_labels(store, tmp_path):
    room, gateway = setup_room(store, tmp_path)
    evidence = packet("Example", "file:report", "Example increased output. Example opened a shop.")
    gateway.evidence[evidence["id"]] = evidence
    gold = case("supported", {"file:report": ["Example increased output."]})
    args = proposal(gold["claim_text"], evidence["quote_spans"][0]["id"])
    output, events = publish(store, room, gateway, args)
    good = score_v2(gold, args, output, events, gateway.evidence)
    assert good["fully_correct"] and good["supported_case_correct"]
    assert not good["publication_truth_verified_flag"]
    args["quote_id"] = evidence["quote_spans"][1]["id"]
    wrong_span = score_v2(gold, args, output, events, gateway.evidence)
    assert not wrong_span["fields"]["relevant_citation"]
    assert wrong_span["irrelevant_citation"] and not wrong_span["fully_correct"]
    gold["expected"]["wrong_entity_sources"] = ["file:report"]
    gold["expected"]["wrong_event_sources"] = ["file:report"]
    wrong_scope = score_v2(gold, args, output, events, gateway.evidence)
    assert wrong_scope["wrong_entity_citation"] and wrong_scope["wrong_event_citation"]


def test_raw_rejected_and_accepted_unsupported_proposals_distinct(store, tmp_path):
    room, gateway = setup_room(store, tmp_path)
    evidence = packet("Example", "file:report", "Example opened a shop.")
    gateway.evidence[evidence["id"]] = evidence
    gold = case("insufficient", {})
    args = proposal(gold["claim_text"], "q:missing")
    output, events = publish(store, room, gateway, args)
    rejected = score_v2(gold, args, output, events, gateway.evidence)
    assert rejected["raw_unsupported_support_proposed"]
    assert not rejected["unsupported_supported_proposal_accepted"]
    assert rejected["nonexistent_citation"]
    args["quote_id"] = evidence["quote_spans"][0]["id"]
    output, events = publish(store, room, gateway, args)
    accepted = score_v2(gold, args, output, events, gateway.evidence)
    assert accepted["unsupported_supported_proposal_accepted"]
    assert accepted["valid_quote"] and accepted["irrelevant_citation"]


def test_false_abstention_and_altered_publication_are_labeled(store, tmp_path):
    room, gateway = setup_room(store, tmp_path)
    evidence = packet("Example", "file:report", "Example increased output.")
    gateway.evidence[evidence["id"]] = evidence
    gold = case("supported", {"file:report": ["Example increased output."]})
    args = proposal("Example opened a shop.", evidence["quote_spans"][0]["id"], "insufficient")
    output, events = publish(store, room, gateway, args)
    result = score_v2(gold, args, output, events, gateway.evidence)
    assert result["accepted"] and result["false_abstention"]
    assert not result["gate_rejection"] and not result["supported_case_correct"]
    assert result["published_text_mismatch_needs_review"]
    assert result["proposed_text_mismatch_needs_review"]


def test_empty_gold_citation_and_supported_gate_rejection(store, tmp_path):
    room, gateway = setup_room(store, tmp_path)
    gold = case("insufficient", {})
    args = proposal(gold["claim_text"], "", "insufficient")
    output, events = publish(store, room, gateway, args)
    empty = score_v2(gold, args, output, events, gateway.evidence)
    assert empty["fully_correct"] and empty["fields"]["relevant_citation"]

    room2, gateway2 = setup_room(store, tmp_path)
    supported = case("supported", {"file:missing": ["Example increased output."]})
    args = proposal(supported["claim_text"], "q:nonexistent")
    output, events = publish(store, room2, gateway2, args)
    rejected = score_v2(supported, args, output, events, gateway2.evidence)
    assert rejected["gate_rejection"] and rejected["incorrect_rejection"]
    assert not rejected["false_abstention"] and not rejected["supported_case_correct"]
