# Kepler collaborative research revamp

Implementation handoff, revision 12 — reviewed through `5b3db54`, 4 November 2026.

**Current:** source `30b5c39` fixes terminal streams, predecessor cutoffs and undated omissions, and adds immutable read-only market context with Research Desk provenance cards. [Market-context findings](MARKET_CONTEXT_FINDINGS.md) record the delivered service and its limits: GIFT/STI quotes are honestly unavailable, and the actual rooms still show query/citation/repetition failures. The installed Codex/local adapter, active participant policy and Gemma/Qwen serving pair remain selected; tuning candidates remain inactive.

**Track C delivered in this phase:** source `3bd12d0` adds the central pixel-art office, licensed character sprites, real state/message projection, agent/tool/evidence inspectors and saved replay. [Visual findings and actual screenshots](VISUAL_WORKSPACE_FINDINGS.md) record localhost/LAN, no-selection, replay, mobile and outage/reconnect verification. The existing A/B implementation and its qualification/model failures are preserved.

UI verification used saved real rooms and clearly labeled offline traces, with **zero new model/tool/provider admissions**. Combined phase remains **41/39** within 60/60; the market run stays closed. Local findings report the research API running for history and models/worker stopped as found. Refresh service state locally rather than assuming it remains current.

**Next:** [independent UI review](VISUAL_WORKSPACE_REVIEW.md) confirms the office delivery and identifies a reproduced silent-SSE synchronization defect plus a lost broadcast audience label. Fix those, then implement the shared informational CPU forecast tool through [FORECAST_ADVISORY_HANDOFF.md](FORECAST_ADVISORY_HANDOFF.md) and its [implementation plan](FORECAST_ADVISORY_IMPLEMENTATION.md). No forecast implementation or new inference was performed by this review.

## Read this first

1. [Independent review](VISUAL_WORKSPACE_REVIEW.md), [next implementation](FORECAST_ADVISORY_IMPLEMENTATION.md) and [local handoff](FORECAST_ADVISORY_HANDOFF.md): two UI fixes, then shared CPU advisory forecasting. [Visual workspace findings](VISUAL_WORKSPACE_FINDINGS.md) retain the delivered Track C evidence.
2. [Market-context findings](MARKET_CONTEXT_FINDINGS.md): retained A/B fixes, provider/model gaps and counters. [Track C scope](UI_MILESTONE_PLAN.md), [handoff](MARKET_CONTEXT_HANDOFF.md) and [market-context plan](MARKET_CONTEXT_IMPLEMENTATION.md) retain the implementation requirements.
3. [Fresh-source findings](FRESH_SOURCE_FINDINGS.md) and [results](FRESH_SOURCE_RESULTS.md): completed ingestion, tests, frozen rooms and accounting.
4. [Runbook](RESEARCH_ROOM_RUNBOOK.md), [reboot checks](REBOOT_BROWSER_CHECKS.md) and [work history](WORK_HISTORY.md): normal :8502 entry point, supported host services and implementation history.
5. [Overall plan](IMPLEMENTATION_PLAN.md), [Codex design](CODEX_IMPLEMENTATION.md), [model/status manifest](MODEL_CANDIDATES.json), [skills](SKILLS_AND_CONTEXT_TOOLS.md) and [TimesFM](TIMESFM_AUDIT_AND_REUSE.md): existing design and later capabilities.

Older fresh-source/room-fix handoffs, prompt-iteration plans and spike documents retain historical scopes. The fresh-source allocation is closed at 93 model / 88 tool admissions; unspent limits do not renew it. The graph isolation/precedence fixes remain implemented; destructive tests still require the verified disposable launcher.

## Current evidence and limits

- Track C: **35 frontend tests, types/build and 82 protected backend regressions passed**. Actual localhost/LAN office, inspectors, replay/reload, mobile, cached outage/recovery and labeled fixture cancellation verified. No fresh inference; both original research failures and quote gaps remain visible.
- Independent review at `5b3db54`: **35 frontend tests, types/build, 78 backend passes / 4 infrastructure skips**; all 18 visual evidence files and 15 source hashes matched. Actual-effect offline probe reproduced missing live history masked by successful polling. The local browser/service observations above were not rerun in cloud.
- Local market-context verification: **164 guarded backend tests / 3 expected skips, 82 host tests, 25 frontend tests, types/build/Ruff and actual localhost/LAN recovery passed**. The 41-model/39-tool run retained two imperfect 12-message abstentions and active cancellation; exact citations do not establish narrative truth.
- Historical independent cloud checks at `34a3f40`: **87 backend/source tests passed / 11 infrastructure skips; 22 frontend tests, TypeScript, build and Ruff passed**. That cloud review did not reproduce the earlier local 157-test/UI/graph/reboot observations; the newer local market-context results are listed above.
- All 30 fresh-source export files matched manifest sizes/hashes. Actual application helpers reproduced missing stream-terminal completion, widened predecessor read cutoff and incorrect undated omission reporting using scratch SQLite/loopback HTTP; no real model or broker calls.
- Three paired real questions: relevant titles retrieved 3/3 saved-source versus 0/3 ordinary; unsupported messages 1/23 versus 5/11 in the saved audit. Repeated messages are not independent facts. All six ended in three abstentions/three failures; they do not establish reliable research conclusions.
- Source snapshots preserve first-seen/revisions and explicit date/identity limits. Company filings, broad archive coverage and RBI/PIB timezone gaps remain open. Metadata/real quote validity does not prove interpretation.
- GIFT/Singapore snapshots, tool/UI and bounded availability refresh are implemented. Live quote feeds are unqualified: Kite login expired, the GIFT master row is not a resolved futures contract, STI rights/provider are unverified, and current GIFT overnight hours remain unknown. No quote is fabricated. The new data hook awaits a normal later broker-worker restart; that service was preserved.
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
| Add Scrapling | Bounded extraction adapter delivered for the reviewed PIB HTML source; this is not general crawler/source coverage. |
| Gather-like live discussion UI | Required Pixel Agents-style office delivered at `3bd12d0`, with sprites, events, bubbles, inspectors and replay. Fix the documented live-event synchronization issue; preserve license notices. |
| Agent-browser skill available while researching | Pin and load official guidance plus matching executable functionality through a constrained tool bridge. Merely adding skill text is insufficient. |
| Evaluate/reuse Codex | Selected: Codex App Server plus the tested local adapter, with externally coordinated threads. The first room is installed; extend it using the same external-thread design. |
| Multiple small model families | Use Gemma and Qwen for complementary roles. Multiple roles share two resident services; agreement is not independent corroboration. |
| Intelligent fast brain | Deterministic authority plus a versioned feature/state policy and asynchronous SLM advice. Optional calibrated decision model is an evaluated challenger, not live trade authority. |
| UI backed by actual work | Durable run, step, message, evidence and tool events; no invented conversation, success, progress or activity. |

## TimesFM decision

TimesFM is an informational CPU tool. A Forecast Analyst may explain its outputs and limitations, but no score, sizing, stop/target or risk influence is approved. The wrapper passed 36 checks; the unchanged product has six reproduced defects. Historical SP500 results showed no demonstrated baseline advantage and nominal 80% coverage of 64.5% in the limited sample.

The pinned API returns channel 5 as the point forecast, not the full-array channel 0 mean; the earlier audit has been corrected. Crossing fixes enforce ordering, not calibration. About 2.28 GiB CPU RSS must be budgeted with the two model services, browser and existing running services.

## Start instructions for local Codex

Use [FORECAST_ADVISORY_HANDOFF.md](FORECAST_ADVISORY_HANDOFF.md) for the current task. Repair the two reviewed UI issues, then implement the advisory tool. The market handoff and UI scope are retained history, not instructions to rebuild Track C. Preserve old rooms, source/provider gaps and closed accounting. The new plan specifies a separate bounded optional forecast smoke exercise; no older allocation renews.
