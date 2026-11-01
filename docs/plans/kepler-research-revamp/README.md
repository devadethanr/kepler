# Kepler collaborative research revamp

Implementation handoff, revision 7 — reviewed `ae7d45f`, 2 November 2026.

**Current:** the local room/Research Desk is installed and restored after reboot. The LAN UUID loading bug and most earlier room findings are fixed. Codex App Server + the local adapter and measured Gemma/Qwen serving pair remain selected. Installed participants still use `research_room/codex.py:INSTRUCTIONS`; retained tuning candidates are inactive.

**Next:** implement a narrow, fresh primary-source evidence service and close the small remaining terminal-reason edge. Read [POST_TUNING_REVIEW.md](POST_TUNING_REVIEW.md), [FRESH_SOURCE_IMPLEMENTATION.md](FRESH_SOURCE_IMPLEMENTATION.md) and [FRESH_SOURCE_HANDOFF.md](FRESH_SOURCE_HANDOFF.md). Do not restart the completed room-fix handoff or tune an eighth round on now-seen cases.

## Read this first

1. [Current review](POST_TUNING_REVIEW.md): independently repeated tests, confirmation replay, repaired findings, remaining limits and official-source diagnostics.
2. [Fresh-source implementation](FRESH_SOURCE_IMPLEMENTATION.md) and [local Codex handoff](FRESH_SOURCE_HANDOFF.md): active next task and findings template.
3. [Runbook](RESEARCH_ROOM_RUNBOOK.md), [reboot/browser checks](REBOOT_BROWSER_CHECKS.md) and [local activation](LOCAL_ACTIVATION.md): normal :8502 entry point, model/API/worker services and supported IDE launch context.
4. [Work history](WORK_HISTORY.md), [phase findings](NEXT_PHASE_FINDINGS.md), [prompt results](PROMPT_TUNING_RESULTS.md) and [prompt findings](PROMPT_TUNING_FINDINGS.md): completed source, tests, frozen scores, call accounting and filenames.
5. [Overall implementation plan](IMPLEMENTATION_PLAN.md), [Codex architecture](CODEX_IMPLEMENTATION.md), [models/status](MODEL_CANDIDATES.json), [skills/tools](SKILLS_AND_CONTEXT_TOOLS.md), [harness](COLLABORATIVE_HARNESS_RESEARCH.md) and [TimesFM](TIMESFM_AUDIT_AND_REUSE.md): design and later capabilities.

[ROOM_REVIEW.md](ROOM_REVIEW.md), [NEXT_PHASE_IMPLEMENTATION.md](NEXT_PHASE_IMPLEMENTATION.md), [NEXT_PHASE_HANDOFF.md](NEXT_PHASE_HANDOFF.md), the initial spike reports and [NEXT_VALIDATION_PLAN.md](NEXT_VALIDATION_PLAN.md) retain historical scope. Their early “UI not loading”, graph blocker and first-room build instructions are not current tasks. Retain the now-implemented graph/Toolbox precedence and verified disposable-target guard; destructive tests still require that launcher, never the user's graph.

## Current evidence and limitations

- Independent cloud checks: **55 backend tests passed / 11 infrastructure-specific skips; 21 frontend tests, TypeScript, build and changed-file Ruff passed**. Local guarded 125-test and browser/GPU/reboot results remain local reports, not tests rerun on the user's PC.
- All 25 phase-2 and 235 prompt-evidence files matched supplied manifests. Replaying all 120 final confirmation proposals through the actual gateway/scorer and temporary SQLite reproduced every score.
- Final matched confirmation: Gemma **25/30**, Qwen **24/30**, below the frozen 27/30 objective; candidates remain inactive. This is a supplied-claim contract task, not financial accuracy or live-room quality. Earlier failed scores remain separate history.
- SEBI/RBI RSS were populated in a bounded cloud check; NSE RSS was reachable but empty. The current helper returned unknown for the observed SEBI date-only strings. Freshness, identity, completeness and as-of history need source-specific implementation.
- Manual live-entry approval, existing broker controls and TimesFM's lack of new score/risk authority remain unchanged. Preserve the changing local runtime files.

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

Use [FRESH_SOURCE_HANDOFF.md](FRESH_SOURCE_HANDOFF.md). Reuse the installed room and existing news infrastructure, fix the small terminal-reason edge, preserve timestamp/identity/version provenance and connect bounded source tools to actual discussions. Keep the old runtime policy active, preserve local state and run one predeclared source-backed check after offline fixes. Report actual outcomes in FRESH_SOURCE_FINDINGS.md and push source/sanitized docs on this branch.
