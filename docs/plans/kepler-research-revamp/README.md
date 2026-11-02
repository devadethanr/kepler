# Kepler collaborative research revamp

Implementation handoff, revision 8 — reviewed `34a3f40`, 2 November 2026.

**Current:** the fresh-source service and Research Desk provenance views are delivered at source `0ba305a`, with findings at `34a3f40`. The installed Codex/local adapter, active participant policy and Gemma/Qwen serving pair remain selected; tuning candidates remain inactive. The LAN UI loading bug is fixed.

**Next:** fix three reproduced integrity issues and implement read-only GIFT Nifty / Singapore market context. Start with [FRESH_SOURCE_REVIEW.md](FRESH_SOURCE_REVIEW.md), then [MARKET_CONTEXT_IMPLEMENTATION.md](MARKET_CONTEXT_IMPLEMENTATION.md) and [MARKET_CONTEXT_HANDOFF.md](MARKET_CONTEXT_HANDOFF.md). Provider discovery can proceed in parallel with offline integrity fixes. Do not replay the completed source run or another prompt-only experiment.

## Read this first

1. [Current source-phase review](FRESH_SOURCE_REVIEW.md): independent tests/reproductions, source delivery, actual room results and limits.
2. [Market-context implementation](MARKET_CONTEXT_IMPLEMENTATION.md) and [local handoff](MARKET_CONTEXT_HANDOFF.md): active next scope.
3. [Fresh-source findings](FRESH_SOURCE_FINDINGS.md) and [results](FRESH_SOURCE_RESULTS.md): completed ingestion, tests, frozen rooms and accounting.
4. [Runbook](RESEARCH_ROOM_RUNBOOK.md), [reboot checks](REBOOT_BROWSER_CHECKS.md) and [work history](WORK_HISTORY.md): normal :8502 entry point, supported host services and implementation history.
5. [Overall plan](IMPLEMENTATION_PLAN.md), [Codex design](CODEX_IMPLEMENTATION.md), [model/status manifest](MODEL_CANDIDATES.json), [skills](SKILLS_AND_CONTEXT_TOOLS.md) and [TimesFM](TIMESFM_AUDIT_AND_REUSE.md): existing design and later capabilities.

Older fresh-source/room-fix handoffs, prompt-iteration plans and spike documents retain historical scopes. The fresh-source allocation is closed at 93 model / 88 tool admissions; unspent limits do not renew it. The graph isolation/precedence fixes remain implemented; destructive tests still require the verified disposable launcher.

## Current evidence and limits

- Independent cloud checks: **87 backend/source tests passed / 11 infrastructure skips; 22 frontend tests, TypeScript, build and Ruff passed**. The local 157-test/UI/graph/reboot observations were not rerun on the user's PC.
- All 30 fresh-source export files matched manifest sizes/hashes. Actual application helpers reproduced missing stream-terminal completion, widened predecessor read cutoff and incorrect undated omission reporting using scratch SQLite/loopback HTTP; no real model or broker calls.
- Three paired real questions: relevant titles retrieved 3/3 saved-source versus 0/3 ordinary; unsupported messages 1/23 versus 5/11 in the saved audit. Repeated messages are not independent facts. All six ended in three abstentions/three failures; they do not establish reliable research conclusions.
- Source snapshots preserve first-seen/revisions and explicit date/identity limits. Company filings, broad archive coverage and RBI/PIB timezone gaps remain open. Metadata/real quote validity does not prove interpretation.
- GIFT/Singapore provider support is not yet implemented. The existing GIFT scheduler method only logs; macro float/cache helpers do not qualify live index data. The next scope addresses that directly.
- Manual live-entry approval and existing broker/protection controls remain; TimesFM receives no new score/risk authority. Preserve local changing runtime files and original evidence.

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

Use [MARKET_CONTEXT_HANDOFF.md](MARKET_CONTEXT_HANDOFF.md). Fix the three precise integrity findings, qualify read-only GIFT/STI sources and add truthful session/delay/quality snapshots to the existing desk and tool gateway. Keep current runtime/model/prompt choices, preserve source history and local state, and verify with a fresh bounded run. Record actual outcomes in MARKET_CONTEXT_FINDINGS.md.
