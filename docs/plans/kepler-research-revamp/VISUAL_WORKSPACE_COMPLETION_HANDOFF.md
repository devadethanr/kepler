# Local Codex: finish the research workspace before extending it

4 November 2026. This corrects the completion claim in `31583db` after the user's
two screenshots and source inspection. Track C has an implemented office/event
foundation, but the requested usable Pixel Agents/Gather-like workspace remains
**partial**. This handoff takes priority over starting new TimesFM work.
Preserve any forecast work already in progress; do not revert or overwrite it.

Read AGENTS.md, README.md, VISUAL_WORKSPACE_REVIEW.md, UI_MILESTONE_PLAN.md and
this handoff. Continue on `feat-generic-broker`, preserving runtime changes,
stash/backups, model configuration, original source/market evidence, broker
services, controls and manual live-entry approval. Keep the existing React,
Codex, Python/Postgres/SSE implementation and licensed assets.

## What the screenshots establish

- The selected room is a **queued cancellation**: three events, zero messages,
  zero model/tool calls. No discussion bubbles is correct for that room; it does
  not demonstrate a working discussion. Do not populate it with fake activity.
- Both model-health labels say unavailable. That observation does not establish
  current worker health or the root cause. Saved history is accessible, but a
  live research session has not been demonstrated by these screenshots.
- The office occupies almost the entire view; replay/status/actions are below
  it and the transcript is collapsed. Users have to search for the actual work.
- Source inspection confirms uncapped width-based canvas sizing and an inspector
  that opens only after a click. The renderer has fixed desk/discussion poses
  and work frames, with no interpolated movement. Existing tests and hashes
  establish engineering properties, not acceptance of this interaction design.

## Required implementation

1. **Fit the workspace to the viewport.** Retain the pixel office as the main
   visual, with a bounded responsive stage that preserves its aspect ratio and
   coordinate/hit-target mapping. Increasing window width must not keep making
   the office taller. Start with a stage around 35–45% of usable viewport height
   on desktop and adjust from actual screenshots; do not crop or distort sprites.
   Make labels and controls readable at 100% browser zoom. Measure layout in
   pixels; shrinking the entire page is not a solution.
2. **Show the research alongside the scene.** A discussion/activity pane is open
   by default for a selected room. Show real recent addressed messages and current
   tool/status events with timestamps. Evidence can open in that pane without
   losing the conversation. Keep the question/selection, latest/replay status,
   readiness and applicable start/cancel actions visible without scrolling past
   the whole office. On narrow screens, stack office and readable discussion;
   keep the primary controls above the scene. Preserve keyboard/reduced motion.
3. **Make saved, live and empty states understandable.** Show room status,
   message count and whether any research actually ran near the selector. A
   queued-cancelled room says cancelled before research, with no messages, when
   durable events establish that fact. Offer navigation to a real saved room
   with messages and an explicit new-research action. Preserve explicit room
   selection across reload; never silently replace it with a prettier room.
   Put model readiness near the action and disclose worker readiness only when
   an actual health signal supports it. Unknown stays unknown; page/API reachability
   does not mean models or the worker are ready. Surface the existing supported
   local startup/recovery steps rather than repeatedly queueing doomed work.
4. **Finish the event-driven office interactions.** Use short, bounded movement
   between desk and discussion positions when recorded public activity changes.
   Explain current research/tool activity and who is addressing whom; retain
   exact message/evidence click-through. Mark bubbles as the latest recorded
   message when the agent is no longer speaking. Cancelled, saved, stale and
   disconnected views must not invent present work. Replay uses recorded events
   and says recorded replay; reduced motion uses immediate state changes.
   No wandering or repetitive meetings that imply unscheduled research.
5. **Repair correctness already reproduced.** Fix silent OPEN-SSE gaps masked
   by healthy polling, verified contiguous cursor/catch-up and all relevant
   races described in VISUAL_WORKSPACE_REVIEW.md. Preserve broadcast recipient
   `room` in bubbles and accessible controls. Cover both in focused regressions.

## Demonstrate completion

Validate normal **100% zoom** at desktop 1440×900 and 1920×1080, a 1366×768 laptop,
and 390-pixel mobile width. Record viewport, zoom and bounding boxes. On desktop,
the first viewport must contain the complete office stage, primary controls and
readable actual discussion/activity. Long transcripts may scroll within their
pane. Avoid tiny text and page-wide overflow. Verify native click targets after
resize; keyboard, reduced motion, selection/reload, replay and evidence navigation
must remain usable.

Use an existing real saved room with messages to demonstrate discussion/evidence;
also show this zero-message cancellation, no selection, unavailable models and
outage/reconnect. Use explicitly labeled offline traces for concurrent work,
movement and silent-SSE gaps. Preserve original saved payloads/event hashes.
Synthetic traces do not establish that real models/worker are running.

Inspect local service state. Use the supported research-only startup workflow
if a live check is needed and host resources permit; never restart broker
services or reinstall working models for this UI task. Any real UI room uses a
separately recorded run within the original A/B/C aggregate 60/60 ceiling:
market closed at41/39, at most19 additional model/21 tool admissions before
subtracting any later UI usage. Do not reopen that run or borrow the forecast
allocation. Prefer saved-data/fixture verification for design iterations.
Report a live end-to-end check unrun/blocked if it cannot be performed; do not
turn a saved replay into proof of live research.

Run focused frontend/transport tests, TypeScript/build and required protected
regressions for any backend change. No broad graph/DB tests without the verified
disposable launcher. No predictive-quality claim follows from successful UI work.

Write `VISUAL_WORKSPACE_COMPLETION_FINDINGS.md` after execution. Include source
and findings commits, before/after viewport screenshots, real/synthetic evidence
labels, service state, exact tests and remaining defects, preservation hashes,
run usage if any, and private/sanitized artifact locations. Push source and
sanitized evidence to the same branch; leave runtime files uncommitted. Return
the findings for review. Describe delivered parts and remaining limitations
separately; a rendered office and passing tests alone do not complete this task.

TimesFM remains the next capability in FORECAST_ADVISORY_IMPLEMENTATION.md after
this UI completion work. Broader autonomous scheduling and Harness² retain their
existing later scope.
