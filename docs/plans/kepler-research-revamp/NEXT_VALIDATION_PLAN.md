# Grounding and adapter checks during Codex implementation

Updated 1 November 2026 after the user selected Codex for personal Kepler. Read CODEX_IMPLEMENTATION.md first; SPIKE_REVIEW.md records the evidence.

These are focused implementation checks, not another framework-selection or generic production-readiness stage. Do not rerun the completed spike unchanged. Existing R/F run budgets are expired; any fresh inference gets a new run ID and declared limits.

## What these checks improve

Diagnose why correct-schema outputs failed record grounding and preserve the working adapter behavior while integrating it into Kepler. Codex is already the selected implementation runtime.

Use the measured model/runtime pair. Room/tool/UI implementation can proceed alongside this audit; avoid changing serving engines while isolating a grounding error. Keep TimesFM informational.

## G0 — export existing evidence, no inference needed

Produce a small sanitized grounding bundle under docs/plans/kepler-research-revamp/evidence/review-v1/. Preserve originals outside Git. Required for G1:

- Manifest: tested Git revision, model/template/runtime pins, runner and file hashes, run IDs and the originating R record for each item.
- Final shared-register fixture corpus, selected target IDs, prompt/schema, expected answers and exact evaluator/scorer code. Include all relevant contradicting records, not just successful cases.
- Per-case actual outputs/scores for the final 30-request profiles, with field errors and citation sets. Distinguish repeated transport/cache profiles from unique semantic cases.

Other evidence is on demand for the later component reviews, not a prerequisite for the grounding audit:

- For G3: scoped adapter source/config/schema, approved functions, role/ownership/replay checks and representative success/error/cancellation/admission traces. Include the matched Codex/ADK rubric only when assessing that comparison.
- For a separate forecast-contract review: wrapper source, checkpoint/source/package mapping, channel settings and aggregate evaluation policy/results; private-storage negative fixtures only if needed to inspect a defect.
- Existing cleanup/preservation summaries can be referenced from the submitted reports. Request a specific underlying artifact only to resolve a concrete uncertainty.

Missing unrelated F artifacts must not block G1. Do not turn the first export into a reconstruction of the entire spike.

Do NOT commit credentials, cookies, personal Codex home/config, production account data, full private reasoning, model weights, environment dumps or raw licensed FRED/broker observations. Synthetic fixture data and aggregate results are enough. Redactions must retain causal IDs and expected-versus-actual semantics, with a redaction manifest.

Exported code is for inspection, not permission to execute it automatically. Hashes prove identity, not correctness. A missing artifact is explicitly MISSING rather than reconstructed and presented as original.

Deliverable: reviewable code/fixture/results and a manifest, or a specific missing-evidence list. This does not require GPU or production access.

## G1 — audit the existing grounding failures before new calls

Review all unique final fixture cases and representative model outputs, independently of model self-evaluation.

Verify:
- The prompt selects one target and defines its evidence scope unambiguously.
- Gold answers follow the stated timestamp, contradiction and source-authority policy.
- The rubric does not accidentally require information outside the model's allowed scope.
- Raw versus normalized citation order/IDs are handled as declared.
- Inputs were not truncated or scoped differently across profiles.
- A valid alternate answer/abstention is not scored wrong solely by prescribed wording.
- Legitimate cross-record relationships remain available; unrelated facts do not become target facts.
- Budget/truncation/parser differences are not silently counted as reasoning failures.

Classify errors: evaluator/golden defect; wrong target; wrong field; unsupported inference; stale/future evidence; cross-record citation; fabrication; false abstention; syntax/parser/truncation; other/unclear.

Report raw JSON validity, each field's accuracy, target selection, exact record-level correctness, citation precision/recall and valid abstention separately. Do not change the old 2/30 result retroactively: if the evaluator is corrected, version it and show original and revised scores side by side.

A deterministic extraction/retrieval baseline should establish what can be solved without an LLM. No new inference is needed for G1. If a required grounding artifact is unavailable, report the specific gap and the portion of the audit it blocks. Continue independent checks; do not request unrelated experiment logs.

## G2 — targeted grounding comparison after auditing the labels

When implementation needs a new local comparison, declare a fresh run ID and limits. Suggested ceiling: 60 active minutes, 120 model calls including retries, no additional model downloads, preserve existing running services and avoid graph deletion fixtures. This is normal scoped verification, not a new request to approve the Codex choice.

Use existing runtime/model/checkpoint/placement pins. Do not add vLLM/SGLang changes while diagnosing semantics.

Predeclare two arms at identical context/output/deadline settings:

A. Original shared-register prompt with independently audited labels.

B. Source-scoped retrieval/evidence packet for the same target, with explicit record/evidence IDs and quoted facts.

Keep valid target contradictions in B; do not remove hard facts to make the test easier. A historical as_of query must reject unsupported time travel. Test missing, stale, unavailable, ambiguous and cross-target distractor cases.

Use 30 held-out unique cases per lane, not 30 repeated transport requests. Two lanes x two arms x 30 cases uses 120 calls; no hidden retry budget. If an unavoidable retry consumes the ceiling, reduce completed count and report INCOMPLETE. Freeze development versus held-out separation and evaluator before calls.

Minimum functional gate for this small synthetic scope:
- 30/30 parseable schema outputs per lane/arm, or explicitly fail that gate.
- At least 27/30 fully correct records on source-scoped held-out tasks, with field/citation/abstention breakdown.
- Zero cross-target facts or fabricated citations ACCEPTED by deterministic validation. Model proposals rejected by the validator remain visible as errors, not successes.
- No authority violation, silent paid fallback, dropped tool error or invented source.
- Deadlines and resource floors unchanged.

These gates qualify only the tested retrieval/extraction behavior, not financial reasoning or deployment. They must not be weakened after seeing results. Confidence intervals and sample size remain visible. If both models remain weak, investigate task representation or a deterministic solution before adding another large model.

Only after grounding passes should an UNSCRIPTED adaptive-room task be evaluated: no prescribed sentence or predetermined speaker outcome, real targeted evidence lookup, an objection, and a supported revision or explicit disagreement. The existing controlled room remains a completed integration test.

## G3 — inspect the working Codex adapter

Review the existing follow-up source before rewriting it:
- Response/tool IDs, replay/ownership validation, stream terminal/error handling.
- System/developer role translation and untrusted user/tool evidence boundaries.
- Flat tool allowlist and denied native built-ins.
- Atomic admission/cancellation across externally coordinated threads.
- Actual usage versus conservative reservation, reclaim/unknown-usage policy and lease/crash behavior.
- Context/output settings and model-specific templates.
- Sandbox and browser egress/namespace assumptions.

Native heterogeneous child spawn is optional if the selected architecture explicitly uses externally coordinated top-level threads. Do not relabel external routing as native spawn, and do not pursue unsupported namespaces merely to claim a feature.

The fixture's 393216 conservative-token budget differs from the planned local room budget. Reconcile actual usage versus reserved admission when setting local limits; do not present reservations as measured consumption.

Deliverable: reusable adapter code/config with any concrete integration fixes and focused regression checks. Preserve limitations without reopening runtime selection.

## Safety and later product work

The known graph-test configuration/target guard and unchanged TimesFM cache/contracts remain product safety prerequisites. A dedicated safety patch can be planned separately, with dummy-value/unit checks and an exclusively disposable graph before destructive tests.

No TimesFM score/risk/stop/target influence. No broker migration or new live-entry authority. GIFT needs a valid existing local session and read-only entitlement checks; no token values in chat.

Do not repeat the browser namespace fix, 84-stream validation, controlled Codex/ADK exchange or full runtime matrix unchanged. Reuse their artifacts, continue the selected implementation and report concrete changes and verification. A missing unrelated old artifact does not block independent implementation work.

## Handback

~~~text
KEPLER GROUNDING / ADAPTER REVIEW
Source report commit:
Export manifest and missing files:
Evaluator/golden audit:
Original versus revised metrics (if any):
Per-field/target/citation/abstention failures:
New run ID/limits/results or NOT_RUN:
Grounding arm A/B results, unique n and budgets:
Adapter review and remaining limits:
No score/risk influence from TimesFM:
Graph test safety status:
Recommended smallest next step:
Implementation changes completed and remaining:
~~~
