Execution follow-up: [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md) records source `921088c`, completed correctness/UI changes and the still-failed grounding objective. The original handoff/plan/review below is preserved.

Latest continuation: [PROMPT_TUNING_FINDINGS.md](PROMPT_TUNING_FINDINGS.md) contains
the completed seven-round prompt study, source `7f6dc9f`, corrected request accounting,
post-reboot restoration and a new copyable handback. Do not rerun the historical
phase or replace its scores. Experimental candidates remain inactive; the final
confirmation still missed 27/30. [REBOOT_BROWSER_CHECKS.md](REBOOT_BROWSER_CHECKS.md)
records actual live tools, cancellation, API restart and worker interruption checks.

[WORK_HISTORY.md](WORK_HISTORY.md) indexes the completed phases and the renamed
retained prompt files (`contract-agent.md`, `evidence-agent.md` and analyst pair).

# Local Codex handoff — next research-room phase

Start from `feat-generic-broker` containing `aebd42d` and the subsequent review-doc commit. Preserve the five changing runtime-state files and any newer local changes. This is the user's personal, already activated Kepler at :8502; keep Codex selected.

Paste this into local Codex:

```text
Continue on feat-generic-broker. Fetch/pull safely while preserving local changes.
Read docs/plans/kepler-research-revamp/ROOM_REVIEW.md,
NEXT_PHASE_IMPLEMENTATION.md, LOCAL_ACTIVATION.md and RESEARCH_ROOM_RUNBOOK.md.

Implement the next phase on the existing Codex App Server/local-adapter room.
Do not rebuild the framework or repeat the completed model/engine spike.

FIRST restore the existing Research Desk UI. It is intended to load now at
http://localhost:8502 -> Research Desk; the user reports it is not loading.
Reproduce on the actual URL they use, with an isolated test browser/profile.
Capture the first console error, failed network request and status without secrets.
Distinguish a blank/render failure from unavailable API, saved history or models.
Check:
- App.tsx lazy import/tab wiring, browser console and failed/stale JS chunks.
- window.isSecureContext and crypto.randomUUID availability: the current screen
  calls it unguarded during mount, and research.ts calls it for retry. This can
  throw on some non-localhost HTTP origins; it is a hypothesis, not a diagnosis.
- /api/research/health and /api/research/rooms through the dashboard proxy;
  FASTAPI_URL/optional RESEARCH_API_URL, server-side auth, the normal API's Unix
  socket path, host research API and make research-status from swingtradev3/.
- Actual response bodies versus Zod schemas and terminal SSE lifecycle.

Fix the demonstrated cause, preserve valid UUID/idempotency behavior, and add a
focused render/interaction regression. The view must render a useful loading,
empty or unavailable/error state even when services/models are down. Add a local
error boundary/retry surface if appropriate; do not hide the exception or expose
API keys in JavaScript. Verify the user's actual origin as well as localhost,
saved-room selection/reload and error recovery. Do not just rerun the build and
claim the screen loads. The optional Gather-like office view can wait.

Then fix the concrete review findings:
- Deliver and give a bounded response opportunity to the latest objection before
  terminating a room; persist the causal state needed for this decision.
- Make queued cancellation atomically terminal, with completion time and one
  room.finished event; stop terminal SSE reconnects, including after reload.
- Open original relative artifact paths without following symlinks, including
  links into hidden paths. Use dummy files for regressions.
- Fix create/retry idempotency, parent identity and concurrent UUID insert races.
- Handle a final-slot outcome correctly; stop peer work promptly on participant
  failure; keep lease/recovery/activity and usage states honest.
- Apply one deadline/cancellation context across browser fetch and DOM work.
- Expose retrieval omission/truncation/scan limits and older saved rooms.

Then implement the compact claim/evidence contract described in the phase plan:
separate entity/event/record IDs, authoritative timestamps/cutoff and exact source
spans from model interpretation. Compute known metadata policy deterministically;
unknown remains unknown. A real quote must not imply its narrative is verified.
Preserve questions, inference, disagreement and abstention. Do not force consensus
or add an unvalidated third-model judge.

Keep the measured Gemma/Qwen llama.cpp profiles. Reuse saved grounding failures,
clarify prompts/field meanings, freeze independently authored development/held-out
cases and evaluate the new contract plus actual tool-driven rooms. Report raw
unsupported assertions accepted separately from valid quotes and model agreement.
Preserve old scores and distinguish hypotheses from demonstrated causes.

For parallel coding, use Terra with high reasoning for lifecycle/storage and
claim/evidence changes; give the UI work its own bounded task. Assign separate
file ownership and have one integrator handle shared worker/prompt/test changes.
Use an independent reviewer for causal cancellation/idempotency behavior. These
are development-agent choices; the runtime stays on the installed local pair.

Implement offline fixes/tests first. For fresh inference use a declared run ID,
frozen cases/rubric and at most 120 total requests INCLUDING development, tools,
continuations, retries, cancellation and UI tests, as allocated in the phase plan.
No downloads or driver/serving-stack changes. Report incomplete coverage at the
ceiling; do not silently spend more. Model quality can remain weak; keep that
visible instead of claiming it solved because the room works.

Use verified disposable infrastructure for Postgres/graph tests. Add focused
regressions for changed behavior; run backend checks, frontend tests/typecheck/build.
Verify :8502 with actual discussions, cancellation, saved history and API restart.
Test worker interruption separately if changed; recovery is currently a linked
fresh attempt, not automatic continuation of the old Codex threads.

Keep broker services, controls, manual live-entry approval and TimesFM's lack of
score/risk authority intact. Activate only needed research/API changes through
the existing runbook; preserve unrelated services and local runtime files.

Update NEXT_PHASE_FINDINGS.md with the committed source, changes, evidence and
remaining issues. Commit/push source and sanitized docs on feat-generic-broker;
leave changing runtime state uncommitted. Return the copyable handback below.
Continue reversible work within scope; do not stop merely to select Codex again.
```

## Copyable findings handback

```text
KEPLER NEXT-PHASE FINDINGS
Branch / starting and final source commit:
Research Desk load failure root cause, actual URL/origin and browser verification:
Review finding IDs fixed / remaining:
Conversation: latest objection and final-message-limit behavior:
Queued/active/browser cancellation and terminal events:
Concurrent create/retry identity and linked attempts:
File boundary / retrieval completeness / older-room access:
Claim/evidence contract and UI meaning of verification:
Offline tests passed/skipped/failed:
Model/prompt/tool/config versions:
New run ID, case freeze/split and total model requests including continuations:
Held-out unique cases per model and all metric denominators:
Unsupported claims accepted / wrong citations / correct abstention / failures:
Integrated discussion + :8502 reload/API restart/worker-interruption result:
Actual versus reserved/unknown usage and resource observations:
Services activated and broker/control preservation:
Runtime files left uncommitted:
Evidence locations / sanitized artifacts pushed:
Remaining limitations and smallest useful next capability:
```

Create `NEXT_PHASE_FINDINGS.md` with measured outcomes during execution; this review has not run or implemented that next phase. There is no empty “passed” findings page to mistake for completed work.
