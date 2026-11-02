from copy import deepcopy
from uuid import uuid4

import pytest

from research_room.source_eval import accounting, admit_room, validate_plan


def plan():
    return {
        "run_id": "synthetic-offline-run",
        "rooms": [
            {
                "key": "one",
                "phase": "development",
                "arm": "saved",
                "request_id": str(uuid4()),
                "target": "ACME",
                "question": "Which evidence is available?",
                "cutoff": "2026-01-02T00:00:00Z",
                "version_ids": ["synthetic-only"],
                "limits": {"model": 12, "tool": 12, "seconds": 60},
            }
        ],
    }


def test_frozen_native_attempt_is_idempotent_and_cancel_does_not_renew_budget(store):
    frozen = plan()
    room = admit_room(frozen, "one", store)
    store.claim("owner", 60)
    store.admit(room["id"], "owner", "model")
    store.release(room["id"], "owner", "model")
    store.cancel(room["id"])
    store.finish(room["id"], "owner", "abstention", "cancelled")
    assert admit_room(frozen, "one", store)["status"] == "cancelled"
    result = accounting(frozen, store)
    assert result["totals"]["model"] == 1
    assert result["totals"]["unknown_usage_calls"] == 1
    changed = deepcopy(frozen)
    changed["rooms"][0]["arm"] = "ordinary"
    with pytest.raises(ValueError):
        admit_room(changed, "one", store)


def test_every_phase_allocation_and_duplicate_identity_is_checked():
    frozen = plan()
    duplicate = deepcopy(frozen["rooms"][0])
    frozen["rooms"].append(duplicate)
    with pytest.raises(ValueError):
        validate_plan(frozen)
    duplicate["request_id"] = str(uuid4())
    duplicate["limits"]["model"] = 13
    with pytest.raises(ValueError):
        validate_plan(frozen)
