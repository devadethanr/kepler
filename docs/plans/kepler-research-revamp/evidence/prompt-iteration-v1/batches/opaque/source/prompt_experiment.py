"""One frozen, counterbalanced local experiment batch with a durable request ledger.

No prompt promotion or service configuration changes occur here. Each case/arm makes
one request through the installed bridge and real publication gate, without retries.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import threading
import time
from pathlib import Path

from .codex import INSTRUCTIONS
from .contract_eval import TASK, evaluate_case
from .prompt_candidates import VARIANTS, evaluation_prompts
from .settings import load_settings


def summarize(rows):
    result = {}
    keys = ("fully_correct", "accepted", "valid_quote", "raw_unsupported_support_proposed",
            "unsupported_supported_proposal_accepted", "raw_ungrounded_support_proposed",
            "ungrounded_support_accepted", "supported_gold", "supported_case_correct",
            "false_abstention", "gate_rejection", "wrong_entity_citation",
            "wrong_event_citation", "nonexistent_citation", "irrelevant_citation",
            "correct_uncertainty", "uncertainty_case", "published_text_mismatch_needs_review")
    for role, variant in sorted({(r["role"], r["prompt_variant"]) for r in rows}):
        selected = [r for r in rows if r["role"] == role and r["prompt_variant"] == variant]
        result[role + "/" + variant] = {
            "n": len(selected),
            **{key: sum(bool(r.get("score", {}).get(key)) for r in selected) for key in keys},
            "fields": {key: sum(bool(r.get("score", {}).get("fields", {}).get(key)) for r in selected)
                       for key in ("claim_text", "claim_kind", "support_assessment",
                                   "relevant_citation", "event_identity")},
            "model_calls": sum(r.get("counts", {}).get("model", 0) for r in selected),
            "unknown_setup_attempts": sum("counts" not in r for r in selected),
        }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("label")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, required=True)
    parser.add_argument("--batch-limit", type=int, default=200)
    parser.add_argument("--packet-style", choices=["full", "compact"], default="full")
    args = parser.parse_args()
    settings = load_settings()
    cases = json.loads(args.cases.read_text())
    planned = len(cases) * len(args.variants) * len(settings.profiles)
    if planned > args.batch_limit or len(set(args.variants)) != len(args.variants):
        raise ValueError("Invalid batch allocation or duplicate variants")
    for case in cases:
        for field in ("allowed_quotes", "wrong_entity_sources", "wrong_event_sources"):
            if field not in case["expected"]:
                raise ValueError("Span-aware gold required before generation")
    batch = args.run / args.label
    batch.mkdir(mode=0o700)
    frozen_prompts = {variant: dict(zip(("instructions", "task"), evaluation_prompts(
        variant, INSTRUCTIONS, TASK))) for variant in args.variants}
    freeze = {
        "phase": args.label, "rubric": "span-v2", "planned_requests": planned,
        "packet_style": args.packet_style,
        "case_sha256": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        "unique_cases_per_model_arm": len(cases), "variants": args.variants,
        "prompts": frozen_prompts,
        "files": {str(path.relative_to(Path(__file__).parent)): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in [Path(__file__), *Path(__file__).parent.glob("*.py"),
                               *Path(__file__).parent.glob("prompts/*.md")]},
        "model_ids": {role: profile.model for role, profile in settings.profiles.items()},
        "source_retrieval": "supplied fixture packets; real Responses bridge/Gateway/SQLite",
        "order": "roles reverse case order; arm rotation per case and role; no retries",
    }
    (batch / "freeze.json").write_text(json.dumps(freeze, indent=2))
    lock = threading.Lock()
    results = []

    def append(filename, data):
        with (batch / filename).open("a") as stream:
            stream.write(json.dumps(data) + "\n")
            stream.flush()

    def lane(pair):
        role, profile = pair
        ordered = cases if role == "analyst" else list(reversed(cases))
        for index, case in enumerate(ordered):
            start_arm = (index + (role == "skeptic")) % len(args.variants)
            arms = args.variants[start_arm:] + args.variants[:start_arm]
            for variant in arms:
                ident = f"{role}/{variant}/{case['id']}"
                with lock:
                    append("ledger.jsonl", {"intent": ident, "max_requests": 1})
                try:
                    row = evaluate_case(case, role, profile, settings, batch / ident,
                                        prompt_variant=variant, rubric="span-v2",
                                        packet_style=args.packet_style)
                except Exception as exc:
                    row = {"case_id": case["id"], "role": role, "prompt_variant": variant,
                           "error": type(exc).__name__ + ": " + str(exc)[:240]}
                with lock:
                    results.append(row)
                    append("results.jsonl", row)
                    append("ledger.jsonl", {"result": ident, "counts": row.get("counts"),
                                            "error": row.get("error")})
                    if len(results) % 20 == 0:
                        print(json.dumps({"finished": len(results), "planned": planned}), flush=True)

    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(settings.profiles)) as pool:
        list(pool.map(lane, settings.profiles.items()))
    summary = summarize(results)
    (batch / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({"label": args.label, "wall_seconds": time.monotonic() - start,
                      "summary": summary}), flush=True)


if __name__ == "__main__":
    main()
