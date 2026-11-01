"""Export only synthetic fixture inputs, public JSON outputs and original scoring code."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections import Counter
from pathlib import Path


def export(run: Path, output: Path):
    evidence = run / "evidence"
    runner = run / "scripts/bench.py"
    source = runner.read_text()
    tree = ast.parse(source)
    names = {"SCHEMA", "SYSTEM"}
    code = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id in names for t in node.targets
        ):
            code.append(ast.get_source_segment(source, node))
        if isinstance(node, ast.FunctionDef) and node.name in {
            "corpus",
            "valid_schema",
            "chat_payload",
            "measure",
        }:
            code.append(ast.get_source_segment(source, node))
    output.mkdir(parents=True, exist_ok=True)
    (output / "original_scorer.py.txt").write_text("\n\n".join(code) + "\n")
    corpus = json.loads((evidence / "corpus-v1.json").read_text())
    (output / "corpus.json").write_text(json.dumps(corpus, indent=2) + "\n")
    arms = {"llama-gemma-e4b-dual", "llama-qwen35-9b"}
    fields = ["entity", "date", "event_type", "status", "citations"]
    rows, groups = [], {}
    for line in (evidence / "scored.ndjson").read_text().splitlines():
        row = json.loads(line)
        if row.get("arm") not in arms or row.get("mode") != "both-busy":
            continue
        actual, expected = row.get("actual", {}), row.get("expected", {})
        errors = [k for k in fields if actual.get(k) != expected.get(k)]
        supplied, cited = set(expected.get("citations", [])), set(actual.get("citations", []))
        rows.append(
            {
                k: row.get(k)
                for k in [
                    "number",
                    "arm",
                    "case_id",
                    "prefix_category",
                    "schema_valid",
                    "exact_correct",
                    "actual",
                    "expected",
                ]
            }
            | {
                "field_errors": errors,
                "cross_record_citations": sorted(cited - supplied),
                "prompt": row["request"]["messages"],
                "request_settings": {
                    k: row["request"].get(k)
                    for k in ["max_tokens", "seed", "response_format", "tool_choice"]
                },
                "citation_order_normalized_correct": all(
                    actual.get(k) == expected.get(k) for k in fields[:-1]
                )
                and cited == supplied,
            }
        )
    for arm in sorted(arms):
        values = [x for x in rows if x["arm"] == arm]
        groups[arm] = {
            "n_requests": len(values),
            "unique_case_ids": len({x["case_id"] for x in values}),
            "schema_valid": sum(x["schema_valid"] for x in values),
            "original_exact": sum(x["exact_correct"] for x in values),
            "citation_order_normalized_exact": sum(
                x["citation_order_normalized_correct"] for x in values
            ),
            "field_errors": dict(Counter(k for x in values for k in x["field_errors"])),
            "cross_record_citation_requests": sum(
                bool(x["cross_record_citations"]) for x in values
            ),
        }
    (output / "final-profiles.json").write_text(json.dumps(rows, indent=2) + "\n")
    (output / "audit.json").write_text(json.dumps(groups, indent=2) + "\n")
    manifest = {
        "run": run.name,
        "tested_git": "5ebdd171cf3dc3862e1b7a1dd17427ad626471a3",
        "original_runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
        "original_scored_sha256": hashlib.sha256(
            (evidence / "scored.ndjson").read_bytes()
        ).hexdigest(),
        "redactions": "Only synthetic corpus, explicit task prompts, structured JSON answers and scoring code. No private reasoning, credentials, raw broker/FRED observations, or full traces.",
        "files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in output.iterdir()
            if p.is_file()
        },
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(groups, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.run, args.output)
