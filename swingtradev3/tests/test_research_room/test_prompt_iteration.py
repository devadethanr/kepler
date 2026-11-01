"""Prompt variants share one allocation; changing labels never renews a budget."""

import json

import pytest

from research_room.contract_eval import check_allocation


def record(run, directory, calls):
    root = run / directory
    root.mkdir()
    (root / "results.jsonl").write_text(
        json.dumps({"case_id": "arbitrary-name", "counts": {"model": calls}}) + "\n"
    )


def test_new_candidate_and_renamed_cases_do_not_renew_development_budget(tmp_path):
    record(tmp_path, "development", 8)
    record(tmp_path, "development-evidence-v2", 8)
    check_allocation(tmp_path, "development-confirm", 2)
    with pytest.raises(ValueError, match="Development allocation exhausted"):
        check_allocation(tmp_path, "development-confirm", 3)


def test_heldout_variants_share_assessment_allocation(tmp_path):
    record(tmp_path, "heldout", 60)
    with pytest.raises(ValueError, match="Heldout allocation exhausted"):
        check_allocation(tmp_path, "heldout", 1)


def test_total_run_limit_includes_all_result_directories(tmp_path):
    record(tmp_path, "development", 20)
    record(tmp_path, "heldout", 60)
    record(tmp_path, "integrated", 40)
    with pytest.raises(ValueError, match="total inference ceiling"):
        check_allocation(tmp_path, "heldout", 1)
