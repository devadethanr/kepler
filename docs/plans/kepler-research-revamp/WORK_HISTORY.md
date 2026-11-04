# Research revamp work history and references

This is a navigation/history record. Measurements and failures stay in their original
reports and frozen artifacts. The current branch is `feat-generic-broker`.

| Work | Reference / commit | Result and boundary |
|---|---|---|
| Initial isolated runtime/model spike | [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md) | Compared the requested runtimes and measured the local model pair. It did not authorize trading or imply every engine passed. |
| Queued tool/network and forecast-validity follow-ups | [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md), [closed queue](FOLLOW_UP_REQUESTS.md) | Preserves the completed follow-up evidence, including remaining model and forecast limitations. These were not rerun during the later prompt study. |
| First usable room and normal local activation | [RESEARCH_ROOM_IMPLEMENTATION.md](RESEARCH_ROOM_IMPLEMENTATION.md), [LOCAL_ACTIVATION.md](LOCAL_ACTIVATION.md) | Codex analyst/skeptic threads, real tools, durable events and Research Desk at :8502. |
| Room correctness/grounding phase | `921088c`; findings `5adeaea`; [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md) | LAN UUID render fix, R1–R8 lifecycle/tool/evidence changes and guarded graph tests. Old 20/30 and 14/30 assessment results remain unchanged. |
| Recoverable local prompt evaluation | `7f6dc9f`; [prompt findings](PROMPT_TUNING_FINDINGS.md) | Seven development rounds, generic policy/contract variants, full/compact inputs and unchanged span-aware scoring. No values or per-case answers embedded in prompts. |
| Prompt results, restart recovery and native checks | `eda07cb`; [all results](PROMPT_TUNING_RESULTS.md), [browser checks](REBOOT_BROWSER_CHECKS.md), [evidence manifest](evidence/prompt-iteration-v1/manifest.json) | Final confirmation 25/30 Gemma and 24/30 Qwen; 27/30 still failed. 1,232 isolated + 55 native requests. SQLite recovered admissions lost from the reboot-truncated JSONL. |
| Final prompt filenames and this reference history | 2 November 2026, follow-up to `eda07cb` | Renamed retained prompt files without changing their text; preserved selectors, old hashes and frozen snapshots. No extra inference or runtime-policy promotion. |
| Fresh primary-source evidence | Source `0ba305a`, starting `7037018`; [findings](FRESH_SOURCE_FINDINGS.md), [results](FRESH_SOURCE_RESULTS.md), [manifest](evidence/fresh-source-v1/manifest.json) | Controlled SEBI/RBI/PIB acquisition, immutable source history, read-only room tools, current-only graph references and Desk provenance. 93 model/88 tool admissions; useful titles recovered, narrative and terminal limitations retained. Actual LAN/localhost/reboot/API-restart checks; no prompt promotion or trading-authority change. |

## Retained prompt files

Files live in [research_room/prompts](../../../swingtradev3/research_room/prompts/README.md).

| Retained candidate | Evidence policy | Assessment contract | Final confirmation |
|---|---|---|---|
| Qwen / skeptic `combined-v7`, full | [evidence-agent.md](../../../swingtradev3/research_room/prompts/evidence-agent.md) | [contract-agent.md](../../../swingtradev3/research_room/prompts/contract-agent.md) | 24/30 strict, 28/30 support labels, 9/10 strict positive recall. |
| Gemma / analyst `combined-v2`, full | [evidence-analyst.md](../../../swingtradev3/research_room/prompts/evidence-analyst.md) | [contract-analyst.md](../../../swingtradev3/research_room/prompts/contract-analyst.md) | 25/30 strict, 29/30 support labels, 10/10 strict positive recall. |

These documents do not start agents. Evidence files contain participant policy;
contract files contain evaluation-only single-claim instructions. The installed
room still uses the original `codex.py` instructions. All failed earlier candidates,
earlier accepted unsupported support and identifier sensitivity remain documented.
The renames change neither scores nor the promotion decision.

## Why the five runtime files remain local

The [handoff](NEXT_PHASE_HANDOFF.md) explicitly requests source/sanitized-doc commits
and leaves changing runtime state uncommitted. Repository guidance also requires
careful review of `context/` changes. These files were already modified; running
services can continue updating them. Their local contents were preserved.

| File under `swingtradev3/context/` | Runtime purpose |
|---|---|
| `agent_activity.json` | Current agent activity/status. |
| `event_log.jsonl` | Append-only runtime event log. |
| `macro_cache.json` | Cached macro context and fetch state. |
| `regime_cache.json` | Cached market-regime context. |
| `scan_status.json` | Current scan progress/status. |

Committing these would mix a moving operational snapshot with reproducible source
and research evidence. The current request asks about their status and does not
request publishing them. They stay uncommitted alongside retained backup
`stash@{0}` (`b69b0eb`, `safe-next-phase-before-pull-20261101`). Source, prompts and
sanitized research evidence are committed separately.

## Checks and next use

The completed verification is 125 backend/guarded graph/Postgres tests, 21 frontend
tests, TypeScript, build, actual UI/tools/cancellation, API restart and worker-crash
recovery. See [checks.json](evidence/prompt-iteration-v1/checks.json) and
[native evidence](evidence/prompt-iteration-v1/native/rooms-summary.json).

The filename follow-up passed **15 focused backend regressions**, **21 frontend
tests**, TypeScript, Ruff and whitespace checks. It also verified all four renamed
files byte-for-byte against `eda07cb`, 38 frozen prompt selections, historical
selection hashes, and all 235 existing evidence hashes. No new model call was made.

Backend command from `swingtradev3/`:

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_research_room/test_paired_experiment.py \
  tests/test_research_room/test_prompt_iteration.py \
  tests/test_research_room/test_iteration_inputs.py \
  tests/test_research_room/test_iteration_scoring.py \
  tests/test_research_room/test_contract_eval_phase2.py
```

Frontend command from `swingtradev3-dashboard/`: `npm test && npm run lint`.
Backend used the retained research Python 3.12 environment. The earlier full
125-test disposable-infrastructure run and browser/build evidence remain unchanged;
no graph fixture was needed for a filename change. Research health reports both
models ready, and models/API/worker remain running. Broker services, installed
serving configuration and manual entry approval retain their existing authority.

## Independent review after ae7d45f — 2 November 2026

[POST_TUNING_REVIEW.md](POST_TUNING_REVIEW.md) records independent cloud checks and replay of all 120 final confirmation proposals, without model calls. Existing raw reports/scores stay unchanged. The active next implementation is [FRESH_SOURCE_IMPLEMENTATION.md](FRESH_SOURCE_IMPLEMENTATION.md), with [local handoff](FRESH_SOURCE_HANDOFF.md): primary-source evidence and the remaining minor terminal-reason edge. No new prompt was activated by the review.

## Fresh-source delivery and independent review — 2 November 2026

Source `0ba305a`, findings `34a3f40`: immutable source revisions/observations, source-aware dates and identity gaps, bounded news tools, controlled graph references and Desk provenance. [FRESH_SOURCE_REVIEW.md](FRESH_SOURCE_REVIEW.md) records independent tests, arithmetic and three actual-class reproductions. The next active task is [MARKET_CONTEXT_IMPLEMENTATION.md](MARKET_CONTEXT_IMPLEMENTATION.md) / [handoff](MARKET_CONTEXT_HANDOFF.md): integrity fixes plus read-only GIFT/Singapore context. The 93/88 source run and old prompt scores stay closed/unchanged.

## Visual UI scope clarification — 2 November 2026

The user confirmed that the intended agent UI is the Pixel Agents/Gather-like workspace, beyond the delivered form/transcript. [UI_MILESTONE_PLAN.md](UI_MILESTONE_PLAN.md) makes it a required next milestone after the current integrity/market-context phase. The active phase remains unchanged. This clarification updates planning only; no office renderer or avatars have been implemented.

## Integrity and market context delivered — 3 November 2026

Source **`30b5c39`**, starting at `6b2b84b` with safe documentation fast-forward
`410ccef`. I1 terminal completion/dispatch, I2 earlier predecessor cutoff and I3
undated omission regressions are corrected. Immutable market observations,
read-only tools/API, conservative identity/calendar/quality handling and Research
Desk cards are delivered. The availability collector records explicit missing
quotes; it is not a live GIFT/STI feed. Normal Kite login, actual futures mapping,
STI data rights and current GIFT overnight calendar remain qualification gaps.

[MARKET_CONTEXT_FINDINGS.md](MARKET_CONTEXT_FINDINGS.md) records **164 guarded
backend passes / 3 skips, 82 host passes, 25 frontend passes**, actual localhost
and LAN `.41` checks, active-inference cancellation and unchanged event hashes
across API restart. Fixed run `market-context-20261102T175740Z` closed at **41 model /
39 tool** admissions, with two unknown-usage calls. Source-summary retrieval failed;
market discussion retained wrong-instrument citations and repetition. Those
failures were not relabeled or rerun. Active instructions/models/configuration and
inactive candidates were preserved.

All 2,065 original news IDs/payloads and 71/71/6 source-history IDs survived; normal
producers added nine records. Four protected controls/manual approval are unchanged;
heartbeat records and runtime files changed normally. Five tracked runtime files,
original stash and new private backup remain local. The only schema addition is
market observations; an existing config/auth read invoked the additive upgrade
after backup but before the intended disposable-validation step, transparently
recorded in findings. The required visual workspace remains next, unimplemented.

## Required current-phase visual workspace — scope published 4 November 2026

The user requested the Pixel Agents-style office **now in the existing integrity/market-context phase**. This supersedes earlier next-milestone wording. Local A/B source `30b5c39` and findings `e70a3b0` arrived while the scope commit was unpublished and are preserved unchanged. The updated MARKET_CONTEXT_HANDOFF.md makes C required remaining work; the form/cards alone do not complete it. UI development/replay needs no new inference. The closed market run stays at 41 model / 39 tool admissions; any separately recorded UI live check must preserve the original combined 60/60 phase ceiling, leaving at most 19/21 additional. This publication changes planning only, not application source or delivered UI.

## Track C implemented and verified — 4 November 2026

Source **`3bd12d0`** replaces the initial form/cards emphasis with a central
pixel-art office, two pinned licensed character sheets and original furniture.
Real durable events drive scoped agent states, addressed bubbles, inspectors,
tools/market/source evidence and saved sequence replay. No-selection activity stays
unknown; stale/current health and recorded state remain distinct. Selection,
reconnect and terminal history are preserved; controls/context are collapsible.

[Visual findings](VISUAL_WORKSPACE_FINDINGS.md) include actual localhost/LAN
screenshots, mobile/keyboard/reduced-motion checks, a real API outage/recovery,
and labeled intercepted live/cancellation fixtures. **35 frontend and 82 protected
backend checks passed**, with types/build. Active fixture animation measured
29 callbacks/5s and zero/3s offscreen/reduced-motion/cancelled. UI work used
**0 new model/tool/provider admissions**; phase remains41/39, source/market history
and event hashes intact. Models/worker remained stopped as found; only the API
was started for history. Four controls, five runtime files and stash were preserved.
No A/B backend, provider study, failed discussion, prompt or serving profile was
changed. TimesFM/advisory work and broader scheduling remain subsequent scope.

## Independent visual review and next handoff — 4 November 2026

Reviewed source `3bd12d0` / findings `5b3db54`. The required office milestone is
implemented. Independent checks: **35 frontend passes**, types/build, **78 focused
backend passes / 4 infrastructure skips**, all18 visual evidence hashes and15
source hashes. The review did not reproduce the local browser/GPU/service history.
An actual-effect offline probe reproduced silent OPEN-SSE gaps masked by polling;
broadcast `room` recipient labels are also lost by the office projection.

[Review](VISUAL_WORKSPACE_REVIEW.md) records both issues and preserves original
findings. [Next handoff](FORECAST_ADVISORY_HANDOFF.md) fixes them, then repairs and
exposes TimesFM as one bounded CPU advisory tool with trusted input/as-of cache,
evidence/UI and explicit legacy scoring/risk containment. No source code, model,
broker control, runtime state or original evidence was changed by this review;
new model/tool/provider admissions were zero. Old market41/39 remains closed.
