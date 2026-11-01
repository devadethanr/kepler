"""Frozen paired assessments with durable, non-retried request accounting."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
from pathlib import Path

from .codex import INSTRUCTIONS
from .contract_eval import TASK, evaluate_case
from .grounding import packet
from .prompt_candidates import VARIANTS, evaluation_prompts
from .prompt_experiment import summarize
from .settings import load_settings

SELECTION = {
    "analyst": {"variant": "combined-v2", "packet_style": "full"},
    "skeptic": {"variant": "combined-v4", "packet_style": "compact"},
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def completed_results(path):
    """Read complete JSONL records before any torn or NUL-padded tail."""
    if path is None:
        return set()
    data = path.read_bytes().split(b"\0", 1)[0]
    lines = data.split(b"\n")[:-1]
    completed = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            completed.add((row["role"], row["prompt_variant"], row["case_id"]))
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Invalid completed result in prior JSONL") from exc
    return completed


def prepare_evidence(case):
    evidence = {}
    for source in case["sources"]:
        item = packet(
            source["target_entity"], source["source"], source["text"],
            record_id=source["record_id"], event_id=source.get("event_id"),
            published_at=source.get("published_at"), event_at=source.get("event_at"),
            decision_cutoff=case["decision_cutoff"], status=source.get("status", "ok"),
            stale_after_days=case.get("stale_after_days", 30),
            adjustment=source.get("adjustment"), delay=source.get("delay"),
            source_type=source.get("source_type"),
            retrieval=source.get("retrieval", {"completeness": "complete for this supplied excerpt only"}),
        )
        evidence[item["id"]] = item
    return evidence


def arms_for(mode, role, selection=None):
    selection = SELECTION if selection is None else selection
    selected = ("selected", selection[role]["variant"], selection[role]["packet_style"])
    if mode == "opaque":
        return [selected]
    arms = [("control-full", "generic-baseline", "full")]
    if mode == "heldout":
        arms.append(("control-compact", "generic-baseline", "compact"))
    return [*arms, selected]


def durable_write(path, data):
    with path.open("ab") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("label")
    parser.add_argument("--mode", required=True, choices=("opaque", "heldout", "challenge"))
    parser.add_argument("--skip-results", type=Path)
    parser.add_argument("--prepared-evidence", type=Path)
    parser.add_argument("--selection-file", type=Path)
    parser.add_argument("--batch-limit", type=int, default=200)
    args = parser.parse_args()
    if Path(args.label).name != args.label or args.label in (".", ".."):
        raise ValueError("Label must be a single directory name")
    selection_path = args.selection_file or args.run / "candidate-selection-before-unseen.json"
    selection_bytes = selection_path.read_bytes()
    selection = json.loads(selection_bytes)
    selected_profiles = selection.get("selection", {})
    if set(selected_profiles) != set(SELECTION) or any(
        value.get("variant") not in VARIANTS
        or value.get("packet_style") not in ("full", "compact")
        for value in selected_profiles.values()
    ):
        raise ValueError("Invalid presealed candidate selection")
    if args.selection_file is None and selected_profiles != SELECTION:
        raise ValueError("Original presealed candidate selection changed")
    source_root = Path(__file__).parent
    repo_root = source_root.parent.parent
    for name, expected in selection.get("files", {}).items():
        if digest((repo_root / name).read_bytes()) != expected:
            raise ValueError("A presealed source hash changed: " + name)
    cases_bytes = args.cases.read_bytes()
    cases = json.loads(cases_bytes)
    if len({case["id"] for case in cases}) != len(cases):
        raise ValueError("Case identifiers must be unique")
    for case in cases:
        if (not isinstance(case["id"], str) or not case["id"]
                or Path(case["id"]).name != case["id"] or case["id"] in (".", "..")):
            raise ValueError("Case identifiers must be single directory names")
        for field in ("allowed_quotes", "wrong_entity_sources", "wrong_event_sources"):
            if field not in case["expected"]:
                raise ValueError("Span-aware gold required before generation")
    skipped = completed_results(args.skip_results)
    settings = load_settings()
    if set(settings.profiles) != set(SELECTION):
        raise ValueError("Expected analyst and skeptic profiles")
    jobs = [(role, arm, case["id"]) for role in settings.profiles
            for arm, _, _ in arms_for(args.mode, role, selected_profiles) for case in cases]
    planned = sum(job not in skipped for job in jobs)
    if args.batch_limit < 0 or planned > args.batch_limit:
        raise ValueError("Batch allocation exceeded")
    if args.prepared_evidence:
        prepared_bytes = args.prepared_evidence.read_bytes()
        evidence = json.loads(prepared_bytes)
        if set(evidence) != {case["id"] for case in cases}:
            raise ValueError("Prepared evidence must contain exactly the case IDs")
    else:
        evidence = {case["id"]: prepare_evidence(case) for case in cases}
        prepared_bytes = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode()
    batch = args.run / args.label
    batch.mkdir(mode=0o700)
    snapshot = batch / "source"
    snapshot.mkdir(mode=0o700)
    sources = sorted(p for p in source_root.rglob("*") if p.is_file() and p.suffix in {".py", ".md"})
    source_hashes = {}
    for path in sources:
        relative = path.relative_to(source_root)
        data = path.read_bytes()
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        durable_write(destination, data)
        source_hashes[str(relative)] = digest(data)
    prompts = {}
    for role in settings.profiles:
        for arm, variant, style in arms_for(args.mode, role, selected_profiles):
            instructions, task = evaluation_prompts(variant, INSTRUCTIONS, TASK)
            prompts[role + "/" + arm] = {"variant": variant, "packet_style": style,
                                         "instructions": instructions, "task": task}
    durable_write(batch / "prepared-evidence.json", prepared_bytes)
    freeze = {
        "mode": args.mode, "rubric": "span-v2", "planned_requests": planned,
        "total_matrix_requests": len(jobs), "skipped_completed": len(jobs) - planned,
        "case_sha256": digest(cases_bytes), "prepared_evidence_sha256": digest(prepared_bytes),
        "selection_sha256": digest(selection_bytes), "source_hashes": source_hashes,
        "skip_results_sha256": digest(args.skip_results.read_bytes()) if args.skip_results else None,
        "prompts": prompts, "model_ids": {r: p.model for r, p in settings.profiles.items()},
        "order": "analyst forward, skeptic reverse; arm rotation by case and role; no retries",
        "transport": "Responses bridge and publication gateway with supplied evidence",
    }
    durable_write(batch / "freeze.json", json.dumps(freeze, indent=2).encode())
    # Ensure the new batch directory entries are durable before admitting requests.
    directory_fd = os.open(batch, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    lock = threading.Lock()
    rows = []

    def append(path, row):
        durable_write(batch / path, (json.dumps(row, ensure_ascii=False) + "\n").encode())

    def lane(pair):
        role, profile = pair
        ordered = cases if role == "analyst" else list(reversed(cases))
        arms = arms_for(args.mode, role, selected_profiles)
        for index, case in enumerate(ordered):
            offset = (index + (role == "skeptic")) % len(arms)
            for arm, variant, style in arms[offset:] + arms[:offset]:
                ident = (role, arm, case["id"])
                if ident in skipped:
                    continue
                with lock:
                    append("ledger.jsonl", {"intent": list(ident), "max_requests": 1})
                try:
                    row = evaluate_case(
                        case, role, profile, settings, batch / role / arm / case["id"],
                        prompt_variant=variant, rubric="span-v2", packet_style=style,
                        prepared_evidence=evidence[case["id"]],
                    )
                except Exception as exc:
                    row = {"case_id": case["id"], "role": role,
                           "error": type(exc).__name__ + ": " + str(exc)[:240]}
                row["model_prompt_variant"] = variant
                row["prompt_variant"] = arm
                row["packet_style"] = style
                with lock:
                    append("results.jsonl", row)
                    append("ledger.jsonl", {"result": list(ident), "counts": row.get("counts"),
                                            "error": row.get("error")})
                    rows.append(row)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lane, settings.profiles.items()))
    summary = summarize(rows)
    durable_write(batch / "summary.json", json.dumps(summary, indent=2).encode())
    print(json.dumps({"planned": planned, "completed": len(rows), "summary": summary}))


if __name__ == "__main__":
    main()
