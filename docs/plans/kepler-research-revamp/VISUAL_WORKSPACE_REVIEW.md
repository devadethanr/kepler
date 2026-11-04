# Track C independent review — 4 November 2026

Reviewed `3bd12d0` / findings `5b3db54` on `feat-generic-broker`. **The required
Pixel Agents-style office is implemented.** It is the main Research Desk view
before selection, with licensed sprites, addressed public messages, agent and
evidence inspectors, and saved-event replay. This is a delivered UI milestone,
with one current-event synchronization defect to fix before extending it.

The review changes documentation only. It does not claim to have accessed the
operator's localhost/LAN, private database, GPUs or browser profiles. Original
[findings](VISUAL_WORKSPACE_FINDINGS.md), raw evidence and failed conversations
remain unchanged.

## Independently checked

| Check | Result / boundary |
|---|---|
| Frontend | **35 passed**, TypeScript passed, Vite build passed. Existing KnowledgeScreen chunk-size warning. |
| Focused backend | **78 passed / 4 skipped**, disposable SQLite and loopback HTTP only. The four Postgres/proxy checks require local disposable infrastructure. This is separate from the reported local 82/82 run. |
| Integrity regressions | Retained stream terminal/dispatch, predecessor cutoff and undated-omission checks passed in the focused suite. No real model or provider request. |
| Visual evidence | Inspected published no-selection and inspector screenshots: office is central; original abstention and unavailable models remain visible. All **18 evidence files** and **15 implementation-source hashes** match their manifests. |
| Reused assets | Both sprites match documented SHA-256 and Git blob IDs; pinned Pixel Agents MIT notice and MetroCity creator/CC0 provenance are present. External creator terms were not re-fetched. |
| Source scope | No backend change between `c4cedec` and `5b3db54`; no new npm dependencies or competing orchestrator. |

Commands/results and an executable reproduction are in
[cloud review evidence](evidence/cloud-review-5b3db54/checks.json).
The source probe runs the actual selected-room effect under controlled offline
dependencies; it is not a browser observation or a live inference run.

## Fix first: a healthy poll can hide missing streamed events

`ResearchDeskScreen.tsx:249–253` refreshes `lastSync` and reports `Live` when
the room GET succeeds and EventSource remains OPEN. It never compares the room's
sequence with delivered history. If SSE silently stops delivering, a successful
GET every two seconds can keep the old researching/tool state animated forever,
even while the room snapshot's sequence advances. Terminal resync repairs a
finished room eventually, but does not repair gaps during an ongoing room.

The [actual-effect probe](evidence/cloud-review-5b3db54/probe.mts) delivered events
through sequence **2**, polled a running snapshot through **12**, and advanced
the clock **20 seconds** without subsequent events. There was only **one history
read**, the connection remained **Live**, sync age was **0**, and the analyst
remained in **tool** state. Existing projection/server-render tests all pass
despite this transport defect.

Required repair: track event delivery separately from snapshot fetch health.
When a current snapshot is ahead of delivered history, fetch bounded missing
history, merge by durable IDs and advance a verified contiguous cursor. Until caught up,
show cached/unknown current activity and suppress working animation. Reconcile
poll/SSE races and pages without starting another room or inference. Do not mark
a long but genuinely active turn stale merely because it has no new messages:
an up-to-date snapshot, worker lease and complete event cursor can establish
synchronization. Test the effect/controller, not only `projectOffice`.

Also preserve the valid broadcast recipient **`room`** in office messages.
`research-office.ts:94` currently converts it to null because the recipient type
only admits analyst/skeptic. The full discussion retains it; the bubble/mobile
audience label is lost. Keep broadcasts distinct from agent-to-agent handoffs.

## Evidence limits and retained work

Actual localhost/LAN interaction and the API outage/recovery are recorded by the
local operator. Public connected/tool/speaking/cancelled traces are explicitly
synthetic intercepted fixtures. They validate UI behavior, not new live research
or active-inference cancellation. Only the LAN no-selection screenshot is
published; other LAN screenshot hashes in `lan.json` refer to private captures.
Past service/control/runtime preservation is supported by the local audit records,
not independently observed in cloud.

Track C used **zero new model/tool/provider admissions**. The old market run
remains closed at **41/39**, including two unknown-usage calls. Models and worker
were stopped as found; starting the API for history does not activate research.
GIFT/STI quote access, session/identity qualifications, source-summary failure,
wrong citations and repeated abstaining discussion remain unresolved. The UI
does not improve their financial accuracy.

Next: repair the two scoped UI issues, then implement the shared informational
CPU forecast tool in [FORECAST_ADVISORY_IMPLEMENTATION.md](FORECAST_ADVISORY_IMPLEMENTATION.md).
Use [FORECAST_ADVISORY_HANDOFF.md](FORECAST_ADVISORY_HANDOFF.md) locally. Broader
scheduled rooms and Harness² follow; no new framework/model selection is needed.
