# Required visual agent workspace — delivery order

**Delivery update, 4 November 2026:** Track C source **`3bd12d0`** implements the
workspace described below in this same phase. See
[VISUAL_WORKSPACE_FINDINGS.md](VISUAL_WORKSPACE_FINDINGS.md) for measured results
and actual screenshots. The preimplementation scope/history below is retained;
the 41/39 market run remains closed and UI checks added no inference.

**Review update:** [VISUAL_WORKSPACE_REVIEW.md](VISUAL_WORKSPACE_REVIEW.md) confirms the office milestone and records two scoped UI fixes for [the next handoff](FORECAST_ADVISORY_HANDOFF.md). Everything below records the original required scope, not a request to rebuild the office.

Historical clarification, 2 November 2026: the form/discussion interface alone did not deliver the required Pixel Agents/Gather-like workspace. Track C has now delivered it.

## Current phase: preserve A/B, deliver required Track C now

Publication note, 4 November: A/B are now reported delivered in source `30b5c39` with findings `e70a3b0`. Preserve those changes and provider limitations; implement C as required remaining work of this same phase. The office is not yet delivered.

The user's latest instruction includes this workspace **now, in the existing phase**. This supersedes the earlier wording that deferred it until after market context. Keep all work already assigned through MARKET_CONTEXT_HANDOFF.md:

- **A:** the three reproduced stream/cutoff/undated-omission fixes.
- **B:** verified read-only GIFT Nifty and Singapore/STI context, with truthful missing/delayed/unavailable states.
- **C:** implement the Pixel Agents-style visual workspace and integrate the market/source context into that same Research Desk.

Implement Track C using existing saved rooms/events and offline fixtures, independently of any remaining provider follow-up. Preserve the reported A/B integrity fixes and data qualifications. Do not restart the completed market study or drop its limitations. A provider entitlement blocker does not block the office renderer; finish independent work and show the actual unavailable state.

The existing **combined 60 model / 60 tool phase ceilings remain unchanged**. UI development and saved-history replay require no new inference. The completed market run stays closed at 41/39. If a live UI/model check is necessary, record a separate UI run with at most 19 additional model / 21 tool admissions and reconcile cumulative totals; do not reset the original run or grant a new 60/60 allocation.

After this combined phase: TimesFM/advisory integration → broader scheduled/event-driven research → Harness² improvement experiments. Source/model evaluation continues within the relevant work, without reopening framework selection or repeating seen prompt rounds.

## What the visual milestone must deliver

- A real pixel-art office/war-room scene, with character sprites, desks and discussion space, is the main Research Desk view, visible before a room is selected. A form, status cards or avatar icons alone do not satisfy this deliverable. With no selection show configured avatars/health and explicit no-selection state; do not infer global idle from missing room data. Show selected agents honestly as idle, active or unknown within the displayed scope; an empty selection must not become a blank form-only page.
- Visible analyst/skeptic avatars, desks and a discussion area. Multiple logical roles share the existing two model services; an avatar does not imply another loaded model or GPU.
- Observed queued/researching/tool-use/waiting/speaking/finished/failed/cancelled states. Public-message bubbles and handoffs are driven by actual published messages and addressed interactions. Decorative motion must not imply nonexistent research, meetings or consensus.
- Clicking an avatar or message opens the actual discussion, tool outcomes and cited source/market snapshots in a side panel. Keep disagreements, missing data and unassessed interpretations visible.
- Compact room selection/activity controls and a collapsible question/source-coverage panel. The office takes the central space; long technical metadata belongs in the evidence inspector rather than dominating the initial page.
- Saved-room replay and live mode use the same event adapter. Deduplicate by durable IDs, restore state on reload/reconnect and mark stale/disconnected observations explicitly. Do not display cached motion as current work.
- Preserve usable transcript/list controls, keyboard access, reduced motion and a small-screen fallback. The office and evidence views describe the same real run, not separate fabricated conversations.

## Reuse and implementation boundary

Use [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents) as the concrete visual reference and selectively reuse its renderer/layout/components/assets where suitable. Pin the inspected revision and check code and individual art licences before copying, retaining required notices. Its existing provider integration is not a drop-in Kepler adapter; implement the Kepler event provider rather than changing the chosen Codex backend to match another application's hooks.

Keep the existing React dashboard and Python/Postgres/SSE room contract. Start with a lightweight Canvas/React scene and an explicit event-to-visual-state mapping. Avoid an extra agent runtime, standalone office service or heavy game engine solely for this view. Pause/throttle rendering when hidden and measure browser/resource impact on the PC hosting both model services.

Use separate ownership for renderer/layout, event-state adapter, and evidence/interaction panels. One integrator owns the screen wiring and actual-browser verification. MARKET_CONTEXT_HANDOFF.md Track C is the current implementation instruction. One UI owner integrates both the renderer and market/source cards so concurrent agents do not overwrite ResearchDeskScreen.tsx. This documentation change does not claim the office is already implemented.

## Completion evidence

Verify the office is visible with no selected room, real agent/tool/message events update it, clicking an agent opens matching evidence, and saved history/reload/reconnect/cancellation do not invent activity. Test state projection with explicit offline fixtures first, then reuse saved real rooms and one bounded live run if needed. Test actual localhost and LAN browser views, not just TypeScript or server rendering. Capture the visible workspace and report performance, accessibility and remaining limits. Replay alone needs no new model inference; any live checks share the already declared current-phase budget. Record actual localhost/LAN screenshots and evidence in MARKET_CONTEXT_FINDINGS.md, including no-selection, live/saved discussion, error and reconnect states. Do not mark this phase complete with only the existing form/transcript.

The active phase keeps its integrity/market scope and includes this required visual workspace now. Completion must report Tracks A, B and C separately, including concrete blockers, rather than quietly deferring C.
