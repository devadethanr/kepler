# Kepler collaborative research revamp

Research Desk is now active in the normal app at **http://localhost:8502**, backed by the regular database and running local research services. Read [LOCAL_ACTIVATION.md](LOCAL_ACTIVATION.md) for the tested activation and start/stop commands.

The first usable local research-room slice is implemented from `beaa5df`. Read [RESEARCH_ROOM_IMPLEMENTATION.md](RESEARCH_ROOM_IMPLEMENTATION.md) for verified behavior and remaining grounding limitations, then [RESEARCH_ROOM_RUNBOOK.md](RESEARCH_ROOM_RUNBOOK.md) for the native host/API/dashboard path. Existing trading services and manual live-entry approval were preserved.

Personal Kepler implementation handoff, revision 5 — Codex selected, 1 November 2026.

**Decision:** use **Codex App Server with the tested local Responses-to-Chat adapter** for Kepler’s research agents. The user selected this implementation path for their own workspace after the completed browser/tool/adapter follow-ups. It is not parked as an experiment or awaiting another framework-selection gate. Read [CODEX_IMPLEMENTATION.md](CODEX_IMPLEMENTATION.md) for the concrete architecture and work order. Grounding improvements remain implementation work; live entries still require manual approval.

**Inspected application baseline:** main commit `8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0`. Recheck current code before implementing; line references in the audits refer to that revision.

## Read this first

**Do not run destructive graph tests yet.** The test Memgraph environment override is shadowed by committed YAML, and the fixture deletes all nodes on the graph it reaches. Fix and prove fail-closed test isolation before broad test commands. No deletion was performed during research.

Read in this order:

1. [Codex implementation](CODEX_IMPLEMENTATION.md): chosen runtime, reuse of the working adapter, external-thread collaboration and implementation order.
2. [Post-spike review](SPIKE_REVIEW.md): current decisions, evidence limits and corrections after reviewing `8d7ddfc`.
3. [Initial findings](SPIKE_FINDINGS.md), [follow-up findings](FOLLOW_UP_FINDINGS.md), and [completed request queue](FOLLOW_UP_REQUESTS.md): preserve successes, failed gates and exact experimental scope. The tested runtime commit was `5ebdd17`; `8d7ddfc` records the reports and runtime snapshots.
4. [Pre-implementation audit](PRE_IMPLEMENTATION_AUDIT.md): stale/shadowed keys and the still-unfixed graph-test blocker.
5. [Next validation plan](NEXT_VALIDATION_PLAN.md): focused grounding and adapter checks during implementation; reuse existing evidence and do not repeat the full spike unchanged.
6. [Implementation plan](IMPLEMENTATION_PLAN.md): the selected design and implementation sequence.
7. [Collaborative harness](COLLABORATIVE_HARNESS_RESEARCH.md): adaptive discussion on Codex, budgets and Harness².
8. [Skills and context tools](SKILLS_AND_CONTEXT_TOOLS.md): graph, files, search, browser and extraction capabilities.
9. [Models and fast brain](MODELS_AND_FAST_BRAIN.md), with [artifact pins](MODEL_CANDIDATES.json).
10. [TimesFM audit and reuse](TIMESFM_AUDIT_AND_REUSE.md).
11. [Live discussion UI](LIVE_DISCUSSION_UI_RESEARCH.md) and [research sources](RESEARCH_SOURCES.md).

The [initial spike procedure](INITIAL_SPIKE_PLAN.md) and [Codex conformance matrix](CODEX_CONFORMANCE_SPIKE.md) are retained for reproducibility; they are not instructions to restart completed work. CODEX_IMPLEMENTATION.md and the current implementation plan take precedence over historical framework-selection language; SPIKE_REVIEW.md records the measured evidence. Local R/F raw evidence remains on the user's PC; this cloud review inspected the pushed reports, not those private runners/logs or a rerun of the GPU tests.

## Hardware and runtime update

The local report refreshed Ubuntu 24.04.4, about 16 GiB host RAM, the 16,303 MiB RTX 5070 Ti and 12,288 MiB RTX 3060, driver 610.43.02 and CUDA toolkit 13.3. Only llama.cpp completed preferred-pair measurements; default placement retained CPU embeddings and was fast, while strict full-GPU Gemma timed out. vLLM/SGLang did not produce a passing preferred-pair replacement in the measured configurations. No universal engine winner or full-GPU requirement follows from this.

Use the measured llama.cpp profile as the initial implementation baseline; do not infer answer quality from speed or reinstall optimized engines unchanged. JSON validity was 30/30, but all-field/citation-set correctness only 2/30 per preferred lane. Diagnose evidence scope, evaluator and prompts before changing models. Native scripts remain valid; Docker is optional. Preserve the working driver/services.

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
| Gemma 4 E4B | Gemma E4B on the 3060 and Qwen3.5-9B on the 5070 Ti were measured together. Use that measured baseline for implementation and improve grounding alongside integration. |
| Implement GIFT and Singapore | Required context service. Verify the existing Kite GIFT quote entitlement; optional delayed provider fallback. Singapore context is a hypothesis to evaluate, not proof that STI causes Nifty moves. |
| Put Harness² into agents' work | Agents can propose and review research-harness experiments through tools. Candidate testing is isolated and promotion remains manual; ordinary research uses an approved immutable version. |
| Add Scrapling | Required bounded extraction adapter behind the existing provider boundary, with source profiles and quality tests. |
| Gather-like live discussion UI | Real discussion transcript and evidence inspector first; optional Pixel Agents-style office view driven by the same events. Check code and art licenses separately. |
| Agent-browser skill available while researching | Pin and load official guidance plus matching executable functionality through a constrained tool bridge. Merely adding skill text is insufficient. |
| Evaluate/reuse Codex | Selected: Codex App Server plus the tested local adapter, with externally coordinated threads. Implement it now in the plan; native heterogeneous child routing is unnecessary for this design. |
| Multiple small model families | Use Gemma and Qwen for complementary roles. Multiple roles share two resident services; agreement is not independent corroboration. |
| Intelligent fast brain | Deterministic authority plus a versioned feature/state policy and asynchronous SLM advice. Optional calibrated decision model is an evaluated challenger, not live trade authority. |
| UI backed by actual work | Durable run, step, message, evidence and tool events; no invented conversation, success, progress or activity. |

## TimesFM decision

TimesFM is an informational CPU tool. A Forecast Analyst may explain its outputs and limitations, but no score, sizing, stop/target or risk influence is approved. The wrapper passed 36 checks; the unchanged product has six reproduced defects. Historical SP500 results showed no demonstrated baseline advantage and nominal 80% coverage of 64.5% in the limited sample.

The pinned API returns channel 5 as the point forecast, not the full-array channel 0 mean; the earlier audit has been corrected. Crossing fixes enforce ordering, not calibration. About 2.28 GiB CPU RSS must be budgeted with the two model services, browser and existing running services.

## Start instructions for local Codex

Read CODEX_IMPLEMENTATION.md and IMPLEMENTATION_PLAN.md, then SPIKE_REVIEW.md and PRE_IMPLEMENTATION_AUDIT.md. Codex App Server plus the tested local adapter is the chosen research runtime. The initial spike and three follow-ups are complete; do not restart the queue, rerun the framework comparison or reopen selection.

Implement the chosen path for this personal workspace: reuse the local working adapter/source and pinned config, connect real tools/skills, persist addressed messages and expose the discussion in the dashboard. Fix the graph-test target guard before destructive graph tests. Audit grounding and improve evidence packets as part of this work, using NEXT_VALIDATION_PLAN.md; those checks do not hold all implementation behind another approval stage. Keep the existing broker execution and manual live-entry approval. Report changes, actual checks and concrete remaining issues.
