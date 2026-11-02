# Required visual agent workspace — delivery order

Clarified with the user on 2 November 2026. The existing Research Desk is a working form, discussion and evidence interface. The requested Pixel Agents/Gather-like visual workspace is **not implemented** and is a **required revamp deliverable**, not optional decoration.

## Order from here

1. **Finish the current integrity and market-context phase.** Follow MARKET_CONTEXT_HANDOFF.md: stream terminal handling, source cutoff/omission fixes, read-only GIFT/Singapore context and existing desk integration. Do not interrupt that work or expand its model-call budget for office development. If a provider entitlement is blocked, finish the available service/UI and explicit unavailable state, document the gap and hand back that phase; do not postpone the visual workspace indefinitely for an external data entitlement.
2. **Build the visual agent workspace next.** The existing room/thread/tool/message/history events provide its backend foundation. There is no need to wait for TimesFM, Harness² or every autonomous-research feature before making the agents visible.
3. **Add TimesFM reuse and advisory fast-brain integration.** Preserve explicit uncertainty and deterministic broker/risk authority; forecast quality remains unqualified.
4. **Add broader scheduled/event-driven research rooms.** Reuse the same workspace, source context, deduplication, limits and durable events.
5. **Add Harness² improvement experiments and remaining research-quality refinements.** User-selected harness promotion and manual live-entry approval remain in force.

Model/source evaluation and concrete regressions continue within the relevant implementation. Do not reopen framework selection or repeat the old prompt study.

## What the visual milestone must deliver

- A Pixel Agents-style office/war-room scene is the main Research Desk view, visible before a room is selected. Show configured agents honestly as idle, active or unknown within the displayed scope; an empty selection must not become a blank form-only page.
- Visible analyst/skeptic avatars, desks and a discussion area. Multiple logical roles share the existing two model services; an avatar does not imply another loaded model or GPU.
- Observed queued/researching/tool-use/waiting/speaking/finished/failed/cancelled states. Public-message bubbles and handoffs are driven by actual published messages and addressed interactions. Decorative motion must not imply nonexistent research, meetings or consensus.
- Clicking an avatar or message opens the actual discussion, tool outcomes and cited source/market snapshots in a side panel. Keep disagreements, missing data and unassessed interpretations visible.
- Compact room selection/activity controls and a collapsible question/source-coverage panel. The office takes the central space; long technical metadata belongs in the evidence inspector rather than dominating the initial page.
- Saved-room replay and live mode use the same event adapter. Deduplicate by durable IDs, restore state on reload/reconnect and mark stale/disconnected observations explicitly. Do not display cached motion as current work.
- Preserve usable transcript/list controls, keyboard access, reduced motion and a small-screen fallback. The office and evidence views describe the same real run, not separate fabricated conversations.

## Reuse and implementation boundary

Use [Pixel Agents](https://github.com/pixel-agents-hq/pixel-agents) as the concrete visual reference and selectively reuse its renderer/layout/components/assets where suitable. Pin the inspected revision and check code and individual art licences before copying, retaining required notices. Its existing provider integration is not a drop-in Kepler adapter; implement the Kepler event provider rather than changing the chosen Codex backend to match another application's hooks.

Keep the existing React dashboard and Python/Postgres/SSE room contract. Start with a lightweight Canvas/React scene and an explicit event-to-visual-state mapping. Avoid an extra agent runtime, standalone office service or heavy game engine solely for this view. Pause/throttle rendering when hidden and measure browser/resource impact on the PC hosting both model services.

Use separate ownership for renderer/layout, event-state adapter, and evidence/interaction panels. One integrator owns the screen wiring and actual-browser verification. Prepare the concrete UI implementation handoff when the current market-context phase is reviewed; this plan does not claim office implementation has started.

## Completion evidence

Verify the office is visible with no selected room, real agent/tool/message events update it, clicking an agent opens matching evidence, and saved history/reload/reconnect/cancellation do not invent activity. Test state projection with explicit offline fixtures first, then reuse saved real rooms and one bounded live run if needed. Test actual localhost and LAN browser views, not just TypeScript or server rendering. Capture the visible workspace and report performance, accessibility and remaining limits. Replay alone needs no new model inference; any live checks use an explicitly declared budget for that later phase.

The current market-context task remains first. This clarification makes the next UI deliverable explicit and removes the earlier assumption that the requested visual workspace was optional.
