# Kepler collaborative research revamp

Research and planning handoff, revision 3 — 1 November 2026.

**Status:** research and static code audits complete. A mandatory local spike now precedes product implementation; GPU/runtime/model/Codex compatibility and authenticated feed results are still unmeasured. No live-trading permission is added.

**Inspected application baseline:** main commit `8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0`. Recheck current code before implementing; line references in the audits refer to that revision.

## Read this first

**Do not run destructive graph tests yet.** The test Memgraph environment override is shadowed by committed YAML, and the fixture deletes all nodes on the graph it reaches. Fix and prove fail-closed test isolation before broad test commands. No deletion was performed during research.

Read in this order:

1. [Pre-implementation audit](PRE_IMPLEMENTATION_AUDIT.md): stale/shadowed keys, effective behavior, replacements and the graph-test blocker.
2. [Mandatory initial spike](INITIAL_SPIKE_PLAN.md), [Codex conformance matrix](CODEX_CONFORMANCE_SPIKE.md), then [findings page](SPIKE_FINDINGS.md): test the real local models and serving engines, write measured findings and **stop for user review before product implementation**. The findings page starts NOT_RUN; do not mistake a template for evidence.
3. [Implementation plan](IMPLEMENTATION_PLAN.md): authoritative product scope, decisions, sequencing and gates, to revisit after the spike.
4. [Collaborative harness](COLLABORATIVE_HARNESS_RESEARCH.md): adaptive discussion, Codex feasibility, budgets and Harness².
5. [Skills and context tools](SKILLS_AND_CONTEXT_TOOLS.md): graph, files, search, browser and extraction capabilities.
6. [Models and fast brain](MODELS_AND_FAST_BRAIN.md), with [artifact pins](MODEL_CANDIDATES.json).
7. [TimesFM audit and reuse](TIMESFM_AUDIT_AND_REUSE.md).
8. [Live discussion UI](LIVE_DISCUSSION_UI_RESEARCH.md).
9. [Research sources](RESEARCH_SOURCES.md).

The initial spike and findings stop rule take precedence until the user reviews local results. The implementation plan is authoritative for subsequent product work if a supporting note describes an earlier proposal.

## Hardware and runtime update

The user supplied a 16,303 MiB RTX 5070 Ti and 12,288 MiB RTX 3060, driver 610.43.02 and CUDA toolkit 13.3/V13.3.73. Refresh UUIDs/current memory/OS/RAM locally. Evaluate vLLM first, compare SGLang, and retain llama.cpp as the known-format baseline. Do not declare a winner before measuring concurrent latency, quality, cache/context behavior and tool/Responses compatibility.

Existing GGUF pins are not automatically optimized vLLM/SGLang artifacts. Record any separately reviewed checkpoint/format change. Native isolated environments and start scripts are accepted; Docker is optional. Preserve the working driver and existing services.

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
| Gemma 4 E4B | Preferred fast model is official Gemma 4 E4B QAT on the 3060; Qwen3.5-9B remains the deeper model on the 5070 Ti. Measure actual memory and latency first. |
| Implement GIFT and Singapore | Required context service. Verify the existing Kite GIFT quote entitlement; optional delayed provider fallback. Singapore context is a hypothesis to evaluate, not proof that STI causes Nifty moves. |
| Put Harness² into agents' work | Agents can propose and review research-harness experiments through tools. Candidate testing is isolated and promotion remains manual; ordinary research uses an approved immutable version. |
| Add Scrapling | Required bounded extraction adapter behind the existing provider boundary, with source profiles and quality tests. |
| Gather-like live discussion UI | Real discussion transcript and evidence inspector first; optional Pixel Agents-style office view driven by the same events. Check code and art licenses separately. |
| Agent-browser skill available while researching | Pin and load official guidance plus matching executable functionality through a constrained tool bridge. Merely adding skill text is insufficient. |
| Evaluate/reuse Codex | Run the documented local-model, collaboration, budget, sandbox and event conformance gate. Select Codex App Server only if all gates pass; otherwise ship the same dynamic room contract on ADK. |
| Multiple small model families | Use Gemma and Qwen for complementary roles. Multiple roles share two resident services; agreement is not independent corroboration. |
| Intelligent fast brain | Deterministic authority plus a versioned feature/state policy and asynchronous SLM advice. Optional calibrated decision model is an evaluated challenger, not live trade authority. |
| UI backed by actual work | Durable run, step, message, evidence and tool events; no invented conversation, success, progress or activity. |

## TimesFM decision

TimesFM remains one shared, typed forecasting tool. A Forecast Analyst can participate in discussions, call the tool and explain uncertainty. The model itself is not a chat agent. Repair input cutoffs, cache identity, quantile validation and false-success/derived stop-target behavior before score influence.

CPU-first and explicit resource allocation preserve the two LLM GPU budgets. No claim that TimesFM beats a random-walk baseline is made.

## Start instructions for local Codex

Read the audit and INITIAL_SPIKE_PLAN.md before changing anything. Preserve local work and the pushed operator-control fixes. Execute the spike only: isolated pinned environments, minimal experimental runners and fixtures, real local model/runtime measurements and Codex/tool checks. Use dummy data and safe fixtures; do not expose or rotate actual secrets or run the destructive graph fixtures.

Populate SPIKE_FINDINGS.md, return its copyable handback to the user with evidence and blockers, and STOP before product P0–P6 implementation. The user will bring the findings back for planning review. Report PASS, FAIL, BLOCKED, NOT_RUN and unavailable metrics distinctly. Do not migrate brokers, enable autonomous live entries, install every optional model/framework or rewrite the application during the spike.
