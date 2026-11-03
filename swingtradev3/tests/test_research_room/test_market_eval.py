from copy import deepcopy
from uuid import uuid4

import pytest

from research_room.market_eval import accounting, admit_room, register_plan, validate_plan


def plan():
    return {
        "run_id": "isolated-market-eval",
        "rooms": [
            {
                "key": phase,
                "request_id": str(uuid4()),
                "phase": phase,
                "target": "Kepler",
                "question": "What recorded market context is available?",
                "cutoff": "2026-01-02T00:00:00Z",
                "version_ids": [],
                "market_snapshot_ids": [],
                "limits": {"model": count, "tool": count, "seconds": 60},
            }
            for phase, count in (("development", 12), ("integration", 24))
        ],
    }


def test_market_run_is_fixed_and_cancellation_never_renews_it(store):
    frozen = plan()
    digest = register_plan(frozen, store)
    room = admit_room(frozen, "development", store)
    store.cancel(room["id"])
    assert admit_room(frozen, "development", store)["status"] == "cancelled"
    assert register_plan(frozen, store) == digest
    assert accounting(frozen, store)["totals"]["model"] == 0
    changed = deepcopy(frozen)
    changed["rooms"][1]["request_id"] = str(uuid4())
    with pytest.raises(ValueError, match="cannot renew"):
        register_plan(changed, store)


def test_market_ceiling_cannot_reuse_source_or_prompt_budget():
    frozen = plan()
    frozen["rooms"][0]["limits"]["model"] = 13
    with pytest.raises(ValueError, match="ceiling"):
        validate_plan(frozen)
    frozen = plan()
    extra = deepcopy(frozen["rooms"][1])
    extra.update(key="integration2", request_id=str(uuid4()))
    frozen["rooms"].append(extra)
    assert validate_plan(frozen)["integration"]["model"] == 48
    extra = deepcopy(extra)
    extra.update(key="integration3", request_id=str(uuid4()))
    frozen["rooms"].append(extra)
    with pytest.raises(ValueError, match="ceiling"):
        validate_plan(frozen)
