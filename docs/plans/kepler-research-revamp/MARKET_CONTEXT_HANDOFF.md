# Local Codex handoff — integrity, market context and visual workspace

Continue from the branch containing market source `30b5c39`, findings `e70a3b0` and this scope update. Preserve the reported A/B delivery and its provider/quality limits. Track C below is required remaining work of the same phase.

**Latest scope clarification:** keep Tracks A/B exactly as assigned and implement the required Pixel Agents-style workspace as Track C **in this same phase, now**. Follow [UI_MILESTONE_PLAN.md](UI_MILESTONE_PLAN.md). This supersedes earlier deferral wording. Local A/B source `30b5c39` and findings `e70a3b0` are now reported delivered and must be preserved. Build/replay Track C without new inference; the closed 41/39 market run stays closed and any separately recorded UI live check must preserve the original combined 60/60 phase ceiling (at most 19/21 additional).

```text
Continue on feat-generic-broker; pull safely and preserve current local changes,
including the five changing runtime files and private backups/stash.

Read docs/plans/kepler-research-revamp/FRESH_SOURCE_REVIEW.md,
MARKET_CONTEXT_IMPLEMENTATION.md, UI_MILESTONE_PLAN.md, MARKET_CONTEXT_FINDINGS.md
and the runbook. A/B source `30b5c39` and findings `e70a3b0` are already pushed; preserve
that implementation and focus remaining work on required Track C. Do not restart
the provider study or rewrite the recorded failed/abstaining room results.
Keep the installed Codex adapter/model pair, current active participant policy,
inactive tuning candidates, broker controls and manual live-entry approval.

Track A reference: the three integrity fixes are reported delivered at `30b5c39`.
Retain them and rerun relevant regressions only for paths touched by UI integration:
1. Streams ending at EOF/[DONE] without a recognized finish reason cannot become
   completed messages or actionable tool calls, even if JSON parses. Preserve
   legitimate stop/tool/length, failure/cancellation, IDs and usage accounting.
2. A successor search must not widen the earlier cutoff of its predecessor.
   Test A at t1 -> B at t3 -> read A, plus reversion and frozen allowlists.
3. Accurately disclose omitted undated records at the service's two-item cap,
   with bounded continuation or explicit limits, including later dated pages.
Use cloud-review-34a3f40 probes as historical reproducers; add corrected regressions.

Track B reference: the read-only context service/cards are reported delivered.
Preserve their truthful unavailable-quote/entitlement/calendar states and completed
qualification. Do not repeat the provider study just to build the visual office.
Inspect/reuse existing market-data/broker clients, macro and scheduler code.
The present _gift_nifty_check only logs; it is not a data implementation.
Verify current official instrument/contracts, provider entitlement and quote,
history/socket capabilities separately. Do not hardcode old instrument tokens.
Use official NSE IX/SGX/provider sources for current sessions/calendars and delays.
If auth needs normal user interaction, report the blocker without asking for
secret values; continue independent provider/calendar/UI work.

Return versioned snapshots with actual identity, source, quote units/contract,
exchange/provider/receive time, delay, session, reference basis and quality reasons.
Preserve unknowns, closed/stale/delayed/unavailable distinctions, cutoff availability
and controlled rate/refresh/connection limits. GIFT futures versus Nifty cash basis
is not a predicted opening gap; STI context is not proof of causality.
Use permitted delayed data only when labeled. Never invent a quote or claim live
support because a master entry or HTTP response exists. Preserve news snapshots;
use an appropriate market observation store, not prices disguised as news items.

Track C is REQUIRED NOW in this same phase: implement the Pixel Agents-style
visual workspace described in UI_MILESTONE_PLAN.md, not only market status cards.
Use a pixel-art office/war room with character sprites, desks and a discussion
area as the main Research Desk view. Keep it visible before a room is selected.
Connect avatar working/waiting/tool/speaking/error states and message bubbles to
actual events. Clicking an agent opens its real discussion, tools and evidence.
Preserve saved replay/reconnect, uncertainty, keyboard/reduced-motion access and
explicit stale/disconnected state; do not invent work or conversations.
Pin/review and reuse compatible Pixel Agents code/assets, with required notices,
and adapt the existing Kepler events rather than swapping the Codex backend.
Keep room controls/coverage compact or collapsible so the office is central.
Reuse the delivered market_context read tool and integrate its existing source/
session/provenance cards into this workspace. Use one UI owner for screen integration. Preserve
server-side credentials. Connect only a narrow data-refresh hook; broader
research scheduling and trading authority remain outside this slice.

Implement Track C independently of any remaining provider follow-up, using
saved real rooms and explicit offline event fixtures. It is not optional or postponed to another phase. UI replay needs no
new model calls; the completed market run remains closed. If a live check is needed, use a new
explicitly recorded UI run within the combined phase ceiling, not another fresh
60/60 allocation: 41 model / 39 tools are already recorded, leaving at most 19/21.

Use Terra high reasoning for protocol/cutoff/provider integration and renderer/
visual-state logic; smaller agents can handle bounded calendar/asset inventories,
fixtures and UI copy. Assign separate
file owners and one integrator; independently review terminal streams and as-of data.
Preserve the A/B fixes and limitations while integrating C. Verify affected event
and cutoff behavior if changed; no repeat of completed discovery is required. Do not repeat the source/prompt experiment or change serving engines.

The market verification run is completed at 41 model / 39 tool admissions. Do not
reopen it or rerun A/B just to verify the office. Use offline fixtures, saved real
rooms and actual browser checks first, normally with zero new model requests.
If live model-backed UI verification is necessary, declare a separate UI run and
reconcile it with the closed market totals: at most 19 additional model / 21 tool
admissions, including continuations/retries/cancellation. The combined ceiling
remains 60/60. Log any provider activity separately. No model download.
Replay the retained source-summary/market rooms as recorded, including their
failures, repeated claims and abstentions. A new office view is not a claim that
those conversations are repaired. Do not force consensus or invent messages.

Run focused backend/protected disposable checks, frontend tests/typecheck/build,
and real LAN/localhost office rendering, agent/event/evidence interactions, market
snapshots, unavailable states, cancellation/reload/API restart. Capture actual UI
screenshots including no selected room; a form-only screen is not completion.
If GIFT entitlement/source is blocked, deliver the truthful service/UI state and
working independent inputs; report the exact gap rather than label it supported.

Append a dated Track C section to MARKET_CONTEXT_FINDINGS.md or create linked
VISUAL_WORKSPACE_FINDINGS.md, preserving original A/B findings and accounting.
Record measured UI outcomes; commit/push source and
sanitized docs, and return the handback below. Preserve runtime files, source history,
broker services and manual approval. Continue reversible work within this scope;
only a concrete dependent blocker needs clarification, not another framework gate.
```

## Copyable handback

```text
KEPLER MARKET-CONTEXT FINDINGS
Starting / source / evidence commits and branch:
I1 terminal-stream correction and actual rejection/dispatch tests:
I2 earlier-cutoff/reversion preservation:
I3 undated omissions/continuation:
GIFT instrument/contract + provider and quote/history/socket capability:
Singapore exact index/proxy + provider/delay capability:
Calendar/session/timezone/holiday/reference sources and versions:
Real snapshot statuses, timestamps/units/delay/basis and unavailable gaps:
Snapshot storage/as-of availability and data preservation:
Required Pixel workspace delivered (sprites/office, real states/bubbles, click-through):
Office no-selection/live/saved/error/reconnect screenshots and interaction checks:
Tool/market cards/collector behavior delivered:
Offline/disposable/frontend checks passed/skipped/failed:
Live source-summary/context rooms, actual useful facts and uncertainty:
New run ID and model/tool/provider counts, actual/reserved/unknown usage:
LAN/localhost cancellation/reload/API-restart evidence:
Broker/control/manual-approval and runtime-file preservation:
Sanitized artifacts pushed / private evidence locations:
Remaining data/model limits and next task:
```

Create the findings page with actual implementation outcomes. This handoff defines required work; the planning commit has not implemented the fixes, providers or visual workspace.
