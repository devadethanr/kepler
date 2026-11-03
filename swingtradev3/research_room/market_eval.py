"""One immutable market-context run allocation: 12 development / 48 integration.

Each model continuation and tool call uses the existing durable room admissions.
This driver cannot reopen the closed source experiment or refund cancellations.
"""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from memory.models import CognitionRunRow
from memory.news_snapshot import _utc

from .store import PHASE, Store


def validate_plan(plan):
    rooms = plan["rooms"]
    if not plan.get("run_id") or not 1 <= len(rooms) <= 4:
        raise ValueError("Declare one run and at most four room identities")
    if any(len({r[key] for r in rooms}) != len(rooms) for key in ("key", "request_id")):
        raise ValueError("Room keys/identities must be unique")
    totals = {p: {k: 0 for k in ("model", "tool")} for p in ("development", "integration")}
    for room in rooms:
        if str(UUID(room["request_id"])) != room["request_id"]:
            raise ValueError("Use canonical UUID spelling")
        if room["phase"] not in totals:
            raise ValueError("Unknown phase")
        _utc(room["cutoff"])
        if not 30 <= room["limits"]["seconds"] <= 1200:
            raise ValueError("Invalid deadline")
        for kind in ("model", "tool"):
            count = room["limits"][kind]
            if type(count) is not int or not 1 <= count <= 24:
                raise ValueError("Invalid per-room allocation")
            totals[room["phase"]][kind] += count
    for kind in ("model", "tool"):
        if totals["development"][kind] > 12 or totals["integration"][kind] > 48:
            raise ValueError("Market phase ceiling exceeded (12/48; total60)")
    return totals


def register_plan(plan, store):
    validate_plan(plan)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    key = "market-eval:" + plan["run_id"]
    if len(key) > 128:
        raise ValueError("Run identity too long")
    with store.scope() as session:
        row = session.get(CognitionRunRow, key)
        if row is None:
            try:
                with session.begin_nested():
                    row = CognitionRunRow(
                        run_id=key,
                        phase="research_market_eval_v1",
                        status="frozen",
                        started_at=datetime.now(timezone.utc),
                        payload={"plan": plan, "plan_sha256": digest},
                    )
                    session.add(row)
                    session.flush()
            except IntegrityError:
                row = session.get(CognitionRunRow, key)
                if row is None:
                    raise
        if row.phase != "research_market_eval_v1" or row.payload.get("plan_sha256") != digest:
            raise ValueError("Run already registered; cannot renew/change allocation")
    return digest


def admit_room(plan, key, store):
    digest = register_plan(plan, store)
    item = next(r for r in plan["rooms"] if r["key"] == key)
    evidence_scope = {
        "run_id": plan["run_id"],
        "phase": item["phase"],
        "mode": "saved",
        "cutoff": item["cutoff"],
        "version_ids": item["version_ids"],
        "market_scopes": ["gift_nifty", "singapore_sti", "nifty_cash"],
        "market_snapshot_ids": item["market_snapshot_ids"],
        "plan_sha256": digest,
    }
    return store.create(
        item["question"],
        item["target"],
        item["request_id"],
        item["limits"],
        evidence_scope=evidence_scope,
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
    if actual - {"room:" + r["request_id"] for r in plan["rooms"]}:
        raise RuntimeError("Unallocated room found; stop and reconcile")
    totals = {
        k: 0
        for k in (
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
        admit_room(plan, item["key"], store)  # Validate existing identity; no retry.
        for kind in totals:
            totals[kind] += room["counts"][kind]
        if any(room["counts"][k] > item["limits"][k] for k in ("model", "tool")):
            raise RuntimeError("Room exceeded its immutable allocation")
        rooms.append({"key": item["key"], **room})
    return {
        "run_id": plan["run_id"],
        "allocation": validate_plan(plan),
        "totals": totals,
        "rooms": rooms,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--admit")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    result = admit_room(plan, args.admit, Store()) if args.admit else accounting(plan, Store())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
