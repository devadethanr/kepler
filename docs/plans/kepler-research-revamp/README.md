Current installed follow-up: [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md) records the LAN loading fix, R1–R8 changes, bounded evaluation and remaining quality failures.

Latest local follow-up: [PROMPT_TUNING_FINDINGS.md](PROMPT_TUNING_FINDINGS.md),
[all prompt results](PROMPT_TUNING_RESULTS.md) and
[post-reboot browser checks](REBOOT_BROWSER_CHECKS.md) record the resumed experiment.
The seven-round prompt study improved some matched results but missed its quality
objective; experimental prompts are not active. The older loading-failure and
next-phase instructions below are preserved as the original handoff history.

# Kepler collaborative research revamp

Implementation handoff, revision 6 — review of `aebd42d`, 1 November 2026.

**Current state:** the first local Codex research room is implemented and activated in the user's normal app at **http://localhost:8502 → Research Desk**, as recorded in [LOCAL_ACTIVATION.md](LOCAL_ACTIVATION.md). **Codex App Server + the tested local adapter remains the chosen runtime.** No framework-selection gate is reopened.

**Reported current issue:** the user says Research Desk is not loading. It is intended to work now; local Codex must diagnose and restore it first, using the actual browser origin and API/service responses. See task 0 in NEXT_PHASE_IMPLEMENTATION.md.

**Next:** fix the concrete conversation/lifecycle/tool gaps and improve grounded claims on that installed room. Read [ROOM_REVIEW.md](ROOM_REVIEW.md), then [NEXT_PHASE_IMPLEMENTATION.md](NEXT_PHASE_IMPLEMENTATION.md). Use [NEXT_PHASE_HANDOFF.md](NEXT_PHASE_HANDOFF.md) for local Codex.

The cloud review repeated 22 backend tests, 16 frontend tests, typecheck/build and Ruff; eight backend checks needing disposable Postgres/graph infrastructure were skipped. It checked committed evidence hashes and reproduced specific defects using temporary SQLite/dummy files. The local report's 89 backend/graph tests and UI/GPU observations were not rerun on the user's PC. Review evidence and exact limits are linked in ROOM_REVIEW.md.

## Read this first

The graph environment-precedence defect and independently verified disposable-target guard are **implemented at aebd42d**. Retain those guards and use the documented disposable launcher for destructive tests; never point it at the user's graph. The old static audit's “unfixed blocker” language is historical, not current status.

Read in this order:

1. [Activated-room review](ROOM_REVIEW.md): verified behavior, reproductions, grounding limits and concrete findings.
2. [Next implementation phase](NEXT_PHASE_IMPLEMENTATION.md) and [local Codex handoff](NEXT_PHASE_HANDOFF.md).
3. [Local activation](LOCAL_ACTIVATION.md) and [runbook](RESEARCH_ROOM_RUNBOOK.md): normal :8502 entry point, host services and supported launch context.
4. [First implementation report](RESEARCH_ROOM_IMPLEMENTATION.md) and its committed evidence.
5. [Codex architecture](CODEX_IMPLEMENTATION.md) and [overall implementation plan](IMPLEMENTATION_PLAN.md): installed foundation plus later capabilities.
6. [Configuration audit](PRE_IMPLEMENTATION_AUDIT.md): baseline inventory with remediation notes; other configuration/TimesFM items remain relevant.
7. [Harness](COLLABORATIVE_HARNESS_RESEARCH.md), [skills/tools](SKILLS_AND_CONTEXT_TOOLS.md), [models](MODELS_AND_FAST_BRAIN.md) and [artifact/status manifest](MODEL_CANDIDATES.json).
8. [TimesFM audit](TIMESFM_AUDIT_AND_REUSE.md), [discussion UI](LIVE_DISCUSSION_UI_RESEARCH.md) and [research sources](RESEARCH_SOURCES.md).

[SPIKE_FINDINGS.md](SPIKE_FINDINGS.md), [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md), the [closed request queue](FOLLOW_UP_REQUESTS.md), [SPIKE_REVIEW.md](SPIKE_REVIEW.md) and [NEXT_VALIDATION_PLAN.md](NEXT_VALIDATION_PLAN.md) preserve earlier scopes/results. The G0/G1 export and fresh 120-call G2 comparison are now recorded in evidence/review-v1; do not replay their expired budgets. Historical initial-spike/conformance documents are not current start instructions. This read order and NEXT_PHASE_IMPLEMENTATION.md take precedence over stale pre-implementation task wording.

The current implementation review targets `aebd42d`; old source-line references at `8fb5088` remain explicitly historical. The five changing runtime-state files reported by the user remain local and must be preserved.

## Hardware and runtime update

The local report refreshed Ubuntu 24.04.4, about 16 GiB host RAM, the 16,303 MiB RTX 5070 Ti and 12,288 MiB RTX 3060, driver 610.43.02 and CUDA toolkit 13.3. Only llama.cpp completed preferred-pair measurements; default placement retained CPU embeddings and was fast, while strict full-GPU Gemma timed out. vLLM/SGLang did not produce a passing preferred-pair replacement in the measured configurations. No universal engine winner or full-GPU requirement follows from this.

Use the measured llama.cpp profile as the initial implementation baseline; do not infer answer quality from speed or reinstall optimized engines unchanged. The original final profiles had 30/30 valid JSON and only 2/30 exact record/citation answers. The fresh scoped G2 test later scored Gemma 4/30 and Qwen 9/30; all remained schema-valid, and accuracy failed. Diagnose evidence scope, evaluator and prompts before changing models. Native scripts remain valid; Docker is optional. Preserve the working driver/services.

## Agreed product behavior

- Keep Zerodha and its existing deterministic execution, reconciliation, protection and risk controls.
- Research agents collaborate and address one another dynamically; they can retrieve evidence, challenge, revise and return to unresolved questions. This is not a fixed speaking pipeline.
- Research can run unattended; **live entries still require the user's approval**.
- A room may conclude no action or preserve disagreement. It must not force consensus or invent evidence.
- Provide approved graph, research-artifact, web, agent-browser and forecast skills with real enforcing tools.
- Show actual published messages, tool outcomes and evidence live, with durable history and recovery.

## Response to the ten requested revisions

| Request | Decision carried into the plan |
|---|---|
| Gemma 4 E4B | Gemma E4B on the 3060 and Qwen3.5-9B on the 5070 Ti were measured together. Keep the installed measured profiles and improve their task representation/grounding in the next phase. |
| Implement GIFT and Singapore | Required context service. Verify the existing Kite GIFT quote entitlement; optional delayed provider fallback. Singapore context is a hypothesis to evaluate, not proof that STI causes Nifty moves. |
| Put Harness² into agents' work | Agents can propose and review research-harness experiments through tools. Candidate testing is isolated and promotion remains manual; ordinary research uses an approved immutable version. |
| Add Scrapling | Required bounded extraction adapter behind the existing provider boundary, with source profiles and quality tests. |
| Gather-like live discussion UI | Real discussion transcript and evidence inspector first; optional Pixel Agents-style office view driven by the same events. Check code and art licenses separately. |
| Agent-browser skill available while researching | Pin and load official guidance plus matching executable functionality through a constrained tool bridge. Merely adding skill text is insufficient. |
| Evaluate/reuse Codex | Selected: Codex App Server plus the tested local adapter, with externally coordinated threads. The first room is installed; extend it using the same external-thread design. |
| Multiple small model families | Use Gemma and Qwen for complementary roles. Multiple roles share two resident services; agreement is not independent corroboration. |
| Intelligent fast brain | Deterministic authority plus a versioned feature/state policy and asynchronous SLM advice. Optional calibrated decision model is an evaluated challenger, not live trade authority. |
| UI backed by actual work | Durable run, step, message, evidence and tool events; no invented conversation, success, progress or activity. |

## TimesFM decision

TimesFM is an informational CPU tool. A Forecast Analyst may explain its outputs and limitations, but no score, sizing, stop/target or risk influence is approved. The wrapper passed 36 checks; the unchanged product has six reproduced defects. Historical SP500 results showed no demonstrated baseline advantage and nominal 80% coverage of 64.5% in the limited sample.

The pinned API returns channel 5 as the point forecast, not the full-array channel 0 mean; the earlier audit has been corrected. Crossing fixes enforce ordering, not calibration. About 2.28 GiB CPU RSS must be budgeted with the two model services, browser and existing running services.

## Start instructions for local Codex

Use [NEXT_PHASE_HANDOFF.md](NEXT_PHASE_HANDOFF.md). Preserve the installed setup and local runtime files, fix the concrete review findings, improve the claim/evidence contract and run focused verification. Keep the existing model/runtime pair and manual live-entry approval. Report measured results in NEXT_PHASE_FINDINGS.md and push source/sanitized docs on this branch. No new framework selection or unchanged spike rerun is required.
