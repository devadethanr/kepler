import json

from research_room.paired_experiment import arms_for, completed_results, prepare_evidence


def test_prior_complete_records_ignore_nul_and_torn_tail(tmp_path):
    path = tmp_path / "prior.jsonl"
    row = {"role": "analyst", "prompt_variant": "selected", "case_id": "one"}
    path.write_bytes(json.dumps(row).encode() + b'\n{"partial":\x00' + b"\x00" * 32)
    assert completed_results(path) == {("analyst", "selected", "one")}


def test_matrix_preserves_selected_role_styles():
    assert arms_for("opaque", "analyst") == [("selected", "combined-v2", "full")]
    assert arms_for("heldout", "skeptic") == [
        ("control-full", "generic-baseline", "full"),
        ("control-compact", "generic-baseline", "compact"),
        ("selected", "combined-v4", "compact"),
    ]
    assert len(arms_for("challenge", "analyst")) == 2


def test_prepared_evidence_preserves_policy_and_metadata():
    case = {
        "decision_cutoff": "2025-01-10T00:00:00Z",
        "stale_after_days": 5,
        "sources": [
            {
                "target_entity": "Example",
                "source": "file:example",
                "text": "Example announced a result.",
                "record_id": "r1",
                "published_at": "2025-01-01T00:00:00Z",
            }
        ],
    }
    evidence = prepare_evidence(case)
    item = next(iter(evidence.values()))
    assert item["record_id"] == "r1"
    assert item["freshness"] == "stale"
    assert item["fetched_at"]


def test_recovery_checks_freeze_evidence_and_unknown_outcomes(tmp_path):
    import pytest

    from research_room.codex import INSTRUCTIONS
    from research_room.contract_eval import TASK
    from research_room.paired_experiment import SELECTION, digest, validate_recovery
    from research_room.prompt_candidates import evaluation_prompts

    case = {
        "id": "one",
        "decision_cutoff": "2025-01-10T00:00:00Z",
        "stale_after_days": 9,
        "sources": [
            {
                "target_entity": "Example",
                "source": "file:example",
                "text": "Example announced a result.",
                "record_id": "r1",
                "published_at": "2025-01-06T00:00:00Z",
            }
        ],
    }
    cases = [case]
    case_bytes = json.dumps(cases).encode()
    evidence = {"one": prepare_evidence(case)}
    prepared = json.dumps(evidence).encode()
    evidence_file = tmp_path / "prepared-evidence.json"
    evidence_file.write_bytes(prepared)
    prompts = {}
    for role, spec in SELECTION.items():
        instructions, task = evaluation_prompts(spec["variant"], INSTRUCTIONS, TASK)
        prompts[role + "/selected"] = {**spec, "instructions": instructions, "task": task}
    freeze = {
        "mode": "opaque",
        "case_sha256": digest(case_bytes),
        "prepared_evidence_sha256": digest(prepared),
        "prompts": prompts,
        "model_ids": {"analyst": "a", "skeptic": "s"},
    }
    freeze_file = tmp_path / "freeze.json"
    freeze_file.write_text(json.dumps(freeze))
    results = tmp_path / "results.jsonl"
    row = {
        "role": "analyst",
        "prompt_variant": "selected",
        "case_id": "one",
        "model_prompt_variant": "combined-v2",
        "packet_style": "full",
    }
    results.write_text(json.dumps(row) + "\n")
    ledger = [
        {"intent": ["analyst", "selected", "one"]},
        {"result": ["analyst", "selected", "one"]},
        {"intent": ["skeptic", "selected", "one"]},
    ]
    (tmp_path / "ledger.jsonl").write_bytes(
        b"".join((json.dumps(x) + "\n").encode() for x in ledger) + b"\0" * 12
    )

    def validate(ack=None, payload=case_bytes):
        return validate_recovery(
            results,
            evidence_file,
            payload,
            cases,
            SELECTION,
            "opaque",
            {"analyst": "a", "skeptic": "s"},
            ack,
        )

    with pytest.raises(ValueError, match="Acknowledge 1"):
        validate()
    assert validate(1)[0] == {("analyst", "selected", "one")}
    with pytest.raises(ValueError, match="case hash"):
        validate(1, case_bytes + b" ")
    freeze["prompts"]["analyst/selected"]["task"] += " changed"
    freeze_file.write_text(json.dumps(freeze))
    with pytest.raises(ValueError, match="frozen prompt"):
        validate(1)
    freeze["prompts"]["analyst/selected"]["task"] = prompts["analyst/selected"]["task"][:-8]
    freeze_file.write_text(json.dumps(freeze))
    evidence["one"][next(iter(evidence["one"]))]["text"] = "Tampered source text."
    modified = json.dumps(evidence).encode()
    evidence_file.write_bytes(modified)
    freeze["prepared_evidence_sha256"] = digest(modified)
    freeze_file.write_text(json.dumps(freeze))
    with pytest.raises(ValueError, match="case sources"):
        validate(1)
