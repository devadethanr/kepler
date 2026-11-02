# Local Codex handoff — integrity and GIFT/Singapore context

Start from the branch containing `34a3f40` and this review-doc commit. Read the current review first. The source-service phase is delivered and its budget is closed.

Scope/order clarification: complete this integrity/market-context task first. The required visual agent workspace follows under [UI_MILESTONE_PLAN.md](UI_MILESTONE_PLAN.md); do not add its implementation or model calls to this current phase.

```text
Continue on feat-generic-broker; pull safely and preserve current local changes,
including the five changing runtime files and private backups/stash.

Read docs/plans/kepler-research-revamp/FRESH_SOURCE_REVIEW.md,
MARKET_CONTEXT_IMPLEMENTATION.md, FRESH_SOURCE_FINDINGS.md and the runbook.
Keep the installed Codex adapter/model pair, current active participant policy,
inactive tuning candidates, broker controls and manual live-entry approval.

Track A: fix the three independently reproduced integrity issues, offline first.
1. Streams ending at EOF/[DONE] without a recognized finish reason cannot become
   completed messages or actionable tool calls, even if JSON parses. Preserve
   legitimate stop/tool/length, failure/cancellation, IDs and usage accounting.
2. A successor search must not widen the earlier cutoff of its predecessor.
   Test A at t1 -> B at t3 -> read A, plus reversion and frozen allowlists.
3. Accurately disclose omitted undated records at the service's two-item cap,
   with bounded continuation or explicit limits, including later dated pages.
Use cloud-review-34a3f40 probes as historical reproducers; add corrected regressions.

Track B: implement verified read-only GIFT Nifty and Singapore/STI context.
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

Track C: add a bounded market_context read tool and source/session/provenance cards
to the existing Research Desk. Preserve actual discussions, saved history, source
uncertainty and server-side credentials. Connect only a narrow data-refresh hook;
broader autonomous research scheduling and trading authority are outside this slice.

Use Terra high reasoning for protocol/cutoff/provider integration, smaller agents
for bounded calendar fixtures, capability inventory and UI tasks. Assign separate
file owners and one integrator; independently review terminal streams and as-of data.
Provider discovery can run alongside A; complete integrity fixes before new model
verification. Do not repeat the source/prompt experiment or change serving engines.

Verify offline and on real local read-only sources. Keep a new declared run with
at most 60 model admissions (12 development / 48 integration), including model
continuations/retries and model-backed smoke/cancel checks. Separately cap/count
tool admissions at 60 and provider activity under its own limits. No model download.
Check a concise useful source summary and a market-context discussion; preserve
specific abstention/disagreement without forcing consensus or inventing messages.

Run focused backend/protected disposable checks, frontend tests/typecheck/build,
and real LAN/localhost snapshots, unavailable states, cancellation/reload/API restart.
If GIFT entitlement/source is blocked, deliver the truthful service/UI state and
working independent inputs; report the exact gap rather than label it supported.

Update MARKET_CONTEXT_FINDINGS.md with measured outcomes, commit/push source and
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
Tool/UI/collector behavior delivered:
Offline/disposable/frontend checks passed/skipped/failed:
Live source-summary/context rooms, actual useful facts and uncertainty:
New run ID and model/tool/provider counts, actual/reserved/unknown usage:
LAN/localhost cancellation/reload/API-restart evidence:
Broker/control/manual-approval and runtime-file preservation:
Sanitized artifacts pushed / private evidence locations:
Remaining data/model limits and next task:
```

Create the findings page with actual implementation outcomes. The current review has not implemented these fixes or a GIFT/STI provider.
