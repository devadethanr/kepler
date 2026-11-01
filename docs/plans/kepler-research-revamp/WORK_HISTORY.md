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
