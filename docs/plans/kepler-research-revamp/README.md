# Kepler collaborative research revamp

Research and planning handoff, revision 4 — post-spike review, 1 November 2026.

**Status:** the local spike and all three user-authorized isolated follow-ups are executed and recorded at `8d7ddfc`. Browser/skill and adapter-backed Codex fixture checks passed. Grounding, optimized runtime/placement, production integration and forecast market-quality gates remain unresolved or failed. No production promotion or live-trading permission is added.

**Inspected application baseline:** main commit `8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0`. Recheck current code before implementing; line references in the audits refer to that revision.

## Read this first

**Do not run destructive graph tests yet.** The test Memgraph environment override is shadowed by committed YAML, and the fixture deletes all nodes on the graph it reaches. Fix and prove fail-closed test isolation before broad test commands. No deletion was performed during research.

Read in this order:

1. [Post-spike review](SPIKE_REVIEW.md): current decisions, evidence limits and corrections after reviewing `8d7ddfc`.
2. [Initial findings](SPIKE_FINDINGS.md), [follow-up findings](FOLLOW_UP_FINDINGS.md), and [completed request queue](FOLLOW_UP_REQUESTS.md): preserve successes, failed gates and exact experimental scope. The tested runtime commit was `5ebdd17`; `8d7ddfc` records the reports and runtime snapshots.
3. [Pre-implementation audit](PRE_IMPLEMENTATION_AUDIT.md): stale/shadowed keys and the still-unfixed graph-test blocker.
4. [Next validation plan](NEXT_VALIDATION_PLAN.md): export existing sanitized evidence and audit grounding/evaluator failures first; do not repeat the full spike unchanged. New inference is a separately declared run.
5. [Implementation plan](IMPLEMENTATION_PLAN.md): target product design, not deployment approval.
6. [Collaborative harness](COLLABORATIVE_HARNESS_RESEARCH.md): adaptive discussion, Codex feasibility, budgets and Harness².
7. [Skills and context tools](SKILLS_AND_CONTEXT_TOOLS.md): graph, files, search, browser and extraction capabilities.
8. [Models and fast brain](MODELS_AND_FAST_BRAIN.md), with [artifact pins](MODEL_CANDIDATES.json).
9. [TimesFM audit and reuse](TIMESFM_AUDIT_AND_REUSE.md).
10. [Live discussion UI](LIVE_DISCUSSION_UI_RESEARCH.md) and [research sources](RESEARCH_SOURCES.md).

The [initial spike procedure](INITIAL_SPIKE_PLAN.md) and [Codex conformance matrix](CODEX_CONFORMANCE_SPIKE.md) are retained for reproducibility; they are not instructions to restart completed work. SPIKE_REVIEW.md takes precedence over pre-spike assumptions. Local R/F raw evidence remains on the user's PC; this cloud review inspected the pushed reports, not those private runners/logs or a rerun of the GPU tests.

## Hardware and runtime update

The local report refreshed Ubuntu 24.04.4, about 16 GiB host RAM, the 16,303 MiB RTX 5070 Ti and 12,288 MiB RTX 3060, driver 610.43.02 and CUDA toolkit 13.3. Only llama.cpp completed preferred-pair measurements; default placement retained CPU embeddings and was fast, while strict full-GPU Gemma timed out. vLLM/SGLang did not produce a passing preferred-pair replacement in the measured configurations. No universal engine winner or full-GPU requirement follows from this.

Keep the measured llama.cpp profile as a comparison baseline; do not promote it solely for speed or reinstall optimized engines unchanged. JSON validity was 30/30, but all-field/citation-set correctness only 2/30 per preferred lane. Diagnose evidence scope, evaluator and prompts before changing models. Native scripts remain valid; Docker is optional. Preserve the working driver/services.

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
| Gemma 4 E4B | Gemma E4B on the 3060 and Qwen3.5-9B on the 5070 Ti were measured together. Keep that experimental baseline; fix grounding before production selection. |
| Implement GIFT and Singapore | Required context service. Verify the existing Kite GIFT quote entitlement; optional delayed provider fallback. Singapore context is a hypothesis to evaluate, not proof that STI causes Nifty moves. |
| Put Harness² into agents' work | Agents can propose and review research-harness experiments through tools. Candidate testing is isolated and promotion remains manual; ordinary research uses an approved immutable version. |
| Add Scrapling | Required bounded extraction adapter behind the existing provider boundary, with source profiles and quality tests. |
| Gather-like live discussion UI | Real discussion transcript and evidence inspector first; optional Pixel Agents-style office view driven by the same events. Check code and art licenses separately. |
| Agent-browser skill available while researching | Pin and load official guidance plus matching executable functionality through a constrained tool bridge. Merely adding skill text is insufficient. |
| Evaluate/reuse Codex | Authorized adapter-backed worker fixtures passed; native heterogeneous child routing is unproven. Inspect the adapter and representative research quality before selecting one room runtime. |
| Multiple small model families | Use Gemma and Qwen for complementary roles. Multiple roles share two resident services; agreement is not independent corroboration. |
| Intelligent fast brain | Deterministic authority plus a versioned feature/state policy and asynchronous SLM advice. Optional calibrated decision model is an evaluated challenger, not live trade authority. |
| UI backed by actual work | Durable run, step, message, evidence and tool events; no invented conversation, success, progress or activity. |

## TimesFM decision

TimesFM remains an experimental informational CPU tool. A Forecast Analyst may explain its outputs and limitations, but no score, sizing, stop/target or risk influence is approved. The wrapper passed 36 checks; the unchanged product has six reproduced defects. Historical SP500 results showed no demonstrated baseline advantage and nominal 80% coverage of 64.5% in the limited sample.

The pinned API returns channel 5 as the point forecast, not the full-array channel 0 mean; the earlier audit has been corrected. Crossing fixes enforce ordering, not calibration. About 2.28 GiB CPU RSS must be budgeted with the two model services, browser and existing production workload.

## Start instructions for local Codex

Read SPIKE_REVIEW.md, both findings reports and PRE_IMPLEMENTATION_AUDIT.md first. The initial spike and three follow-ups are complete. Preserve their results and the user's local work; do not replay expired budgets, restart the old queue or run destructive graph fixtures.

The next bounded task is G0/G1 of NEXT_VALIDATION_PLAN.md: export a small sanitized, versioned review bundle from existing R/F evidence and audit the shared-register evaluator/errors. No new inference is needed for that export/audit. Any new grounding experiment uses a new declared scope/budget after review. Product implementation/deployment remains stopped; keep manual live-entry approval and do not promote TimesFM or a coordinator from fixture passes.
