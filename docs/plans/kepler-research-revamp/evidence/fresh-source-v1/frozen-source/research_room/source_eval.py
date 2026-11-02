"""Small frozen-plan admission driver for native source-room evaluation.

The plan allocates fixed room IDs and nonrefundable maxima, including failed/cancelled
attempts. Resuming the same plan reuses those IDs. It never renews the run or retries
inference. All continuations consume the room's durable admission budget.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from memory.models import CognitionRunRow

from .store import PHASE, Store


def validate_plan(plan):
    rooms = plan["rooms"]
    if not plan.get("run_id") or not rooms or len(rooms) > 8:
        raise ValueError("Declare one run with at most eight frozen room identities")
    if len({room["request_id"] for room in rooms}) != len(rooms):
        raise ValueError("Every attempted room must have a unique frozen identity")
    if len({room["key"] for room in rooms}) != len(rooms):
        raise ValueError("Room keys must be unique")
    totals = {phase: {kind: 0 for kind in ("model", "tool")} for phase in ("development", "frozen")}
    for room in rooms:
        if str(UUID(room["request_id"])) != room["request_id"]:
            raise ValueError("Room UUID must use canonical spelling")
        if room["phase"] not in totals or room["arm"] not in {"ordinary", "saved"}:
            raise ValueError("Unknown phase/arm")
        for kind in ("model", "tool"):
            maximum = room["limits"][kind]
            if type(maximum) is not int or not 1 <= maximum <= 24:
                raise ValueError("Invalid per-room admission ceiling")
            totals[room["phase"]][kind] += maximum
        if not 30 <= room["limits"]["seconds"] <= 1200:
            raise ValueError("Invalid room deadline")
        if not room.get("cutoff") or not room.get("version_ids"):
            raise ValueError("Freeze availability cutoff and saved version identities")
    for kind in ("model", "tool"):
        if totals["development"][kind] > 24 or totals["frozen"][kind] > 96:
            raise ValueError("Frozen phase allocation exceeds 24/96 admissions")
    return totals


def register_plan(plan, store):
    """One canonical allocation per run, anchored in the existing durable store."""
    validate_plan(plan)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    identity = "source-eval:" + plan["run_id"]
    if len(identity) > 128:
        raise ValueError("Run ID exceeds durable identity bound")
    with store.scope() as session:
        row = session.get(CognitionRunRow, identity)
        if row is None:
            try:
                with session.begin_nested():
                    row = CognitionRunRow(
                        run_id=identity,
                        phase="research_source_eval_v1",
                        status="frozen",
                        started_at=datetime.now(timezone.utc),
                        payload={"plan_sha256": digest, "plan": plan},
                    )
                    session.add(row)
                    session.flush()
            except IntegrityError:
                row = session.get(CognitionRunRow, identity)
                if row is None:
                    raise
        if row.phase != "research_source_eval_v1" or row.payload.get("plan_sha256") != digest:
            raise ValueError(
                "Run already frozen with a different plan; allocation cannot be renewed"
            )
    return digest


def admit_room(plan, key, store):
    digest = register_plan(plan, store)
    item = next(room for room in plan["rooms"] if room["key"] == key)
    scope = {
        "run_id": plan["run_id"],
        "phase": item["phase"],
        "mode": item["arm"],
        "cutoff": item["cutoff"],
        "version_ids": item["version_ids"],
        "plan_sha256": digest,
    }
    return store.create(
        item["question"], item["target"], item["request_id"], item["limits"], evidence_scope=scope
    )


def accounting(plan, store):
    register_plan(plan, store)
    with store.scope() as session:
        actual = set(
            session.scalars(
                select(CognitionRunRow.run_id).where(
                    CognitionRunRow.phase == PHASE,
                    CognitionRunRow.payload["evidence_scope"]["run_id"].as_string()
                    == plan["run_id"],
                )
            ).all()
        )
    if actual - {"room:" + item["request_id"] for item in plan["rooms"]}:
        raise RuntimeError("Unallocated room found in durable run; stop and reconcile")
    totals = {
        kind: 0
        for kind in (
            "model",
            "tool",
            "reserved_tokens",
            "input_tokens",
            "output_tokens",
            "unknown_usage_calls",
        )
    }
    rooms = []
    for item in plan["rooms"]:
        try:
            room = store.get("room:" + item["request_id"])
        except KeyError:
            continue
        expected = admit_room(plan, item["key"], store)  # Idempotent identity check only.
        assert expected["id"] == room["id"]
        for kind in totals:
            totals[kind] += room["counts"][kind]
        if any(room["counts"][kind] > item["limits"][kind] for kind in ("model", "tool")):
            raise RuntimeError("Durable room accounting exceeds frozen allocation")
        rooms.append({"key": item["key"], **room})
    return {
        "run_id": plan["run_id"],
        "totals": totals,
        "rooms": rooms,
        "allocation": validate_plan(plan),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--admit", help="One frozen room key; omission only reports accounting")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if args.admit:
        print(json.dumps(admit_room(plan, args.admit, Store()), indent=2))
    else:
        print(json.dumps(accounting(plan, Store()), indent=2))


if __name__ == "__main__":
    main()
