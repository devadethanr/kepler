# Integrity and market-context findings

3 November 2026, Asia/Kolkata. Source **`30b5c39`** on `feat-generic-broker`.
The checkout started at `6b2b84b`; a later fetch found documentation commit
`410ccef`, which was incorporated with fast-forward only before committing source.
That clarification keeps the visual agent workspace as the next milestone.

**Delivered:** the three reproduced integrity fixes, immutable market-observation
storage, bounded read-only tools, conservative calendar/quality handling and
Research Desk cards. **No live GIFT/STI quote feed is qualified.** The real local
observations explicitly report unavailable quotes. Existing Kite authentication
was expired; current futures identity and data rights remain gaps. No secret was
requested, login refreshed, broker migrated or fallback subscription purchased.

**Model verification is mixed, not a research-quality pass.** A real market room
retrieved the saved observations and discussed missing quotes, but repeated itself
and attached Nifty cash citations to GIFT assertions. The source-summary room
missed two available titles and made false absence claims. Both histories remain
unchanged. The run is closed at **41 model / 39 tool admissions**; no retest or
prompt promotion was used to replace these results.

## I1–I3: corrected behavior and independent review

| Finding | Correction and measured verification |
|---|---|
| I1: EOF or `[DONE]` without a terminal reason | Only recognized `stop`, `tool_calls` and `length` states can complete the relevant stream path. Missing/unknown/conflicting reasons, explicit backend errors, tool/finish mismatches and length-truncated tools fail before completed items or actionable calls are exposed. Text length results remain incomplete. Call IDs are reserved together under the lock before completion events; real model IDs, usage and cancellation accounting remain. |
| I2: predecessor cutoff widened | Both direct and linked predecessor registrations preserve the minimum normalized cutoff. A(t1) → B(t3) → read A retains its earlier context, including A→B→A reversion and frozen-allowlist tests. Bodies are immutable; later supersession metadata cannot leak into that earlier read. |
| I3: omitted undated records | Repository counts matches within its scan; service reports its own two-item omission, later-page omissions and an explicit no-continuation reason. Three, six, eight and 1,001-record fixtures exercise exact counts versus scan lower bounds. Unknown publication dates remain outside known publication-window matches. |

Controlled loopback SSE checks include output-item status, duplicate concurrent
IDs, late upstream errors, non-200/connection failures, budget denial and release.
The **installed pinned Codex + actual RPC/Bridge** rejected valid-looking tool
JSON without a terminal reason with **zero stub executions**; a valid
`tool_calls` control executed the isolated stub once. These are protocol fixtures,
not GPU inference or real provider admissions. Terra independently reviewed the
terminal, historical-read and market-availability paths.

The historical [cloud reproducers](evidence/cloud-review-34a3f40/README.md) are
unchanged evidence of the old defects; new regressions assert corrected behavior.

## Provider qualification: observed capability, not inferred entitlement

| Input | Actual local evidence | Quote / history / socket result |
|---|---|---|
| GIFT Nifty future | Official NSE IX specification/circular metadata inspected. Current public Kite master returned 200, 113,768 rows: `NSEIX:GIFT NIFTY`, `EQ/INDICES`, blank expiry. This is an indicative index entry, **not a resolved FUTIDX contract**. No numerical token is hardcoded. | Existing login expired. Authenticated quote/history/socket probes were blocked, not represented as successful tests or unsupported APIs. No owned subscription opened. Current contract/expiry/roll, entitled quote mapping, actual timestamps and delay are unresolved. |
| Singapore STI | Exact target is the FTSE Straits Times **cash index**, not an ETF or future. No exact STI/Straits/Singapore identity appeared in the downloaded Kite master; a logistics substring was rejected. SGX page fetched successfully but did not supply a usable STI observation. | No locally qualified licensed quote provider or retention/distribution permission. Quote/history/socket remain unverified. No proxy silently substituted. |
| Nifty cash reference | One exact `NSE:NIFTY 50` identity was present in the current master. Master `last_price` was never used as a quote or close. | Expired authentication prevents normal quote/history/socket verification. Last completed cash close and compatible comparison basis remain unknown; no spread or return is produced. |
| Documented alternatives | Upstox describes GIFT index data and separate quote/history/stream interfaces. Its stated 120-second refresh interval does **not** establish exchange delay. | Account entitlement/retention unverified; not enabled, no authenticated requests or paid fallback. |

Kite's [quote](https://kite.trade/docs/connect/v3/market-quotes/),
[history](https://kite.trade/docs/connect/v3/historical/) and
[streaming](https://kite.trade/docs/connect/v3/websocket/) documentation establish
different interfaces, not this account's GIFT futures entitlement. Use the existing
normal Kite login workflow (`make login` from `swingtradev3/`, or the normal
dashboard connection flow) for user interaction. Then qualify each capability
with the actual returned identity. Login alone must not relabel the current
network-free collector as a working feed.

The direct source probes fetched NSE IX and SGX JavaScript shells without a
timestamped quote. NSE IX's member contract-master path was documented, but no
current public exchange master was obtained. HTTP 200, a webpage fetch time and a
master entry are insufficient evidence for a recent price.

## Identity, calendars, timestamps and quality

- GIFT observations identify the requested **NIFTY 50 future**, index-point quote
  units and USD settlement separately. Contract, expiry and current multiplier
  stay null. [NSE IX circular 904](https://www.nseix.com/api/content/circulars/NSEIFSC_TRADE_904.pdf)
  is explicitly a historical 2022 specification; its USD 2/point multiplier is not
  asserted current. [Circular 2199](https://www.nseix.com/api/content/circulars/NSEIFSC_TRADE_2199.pdf)
  changed monthly/quarterly expiry to the last Tuesday in 2025, subject to holidays
  and later changes. A rule is not a current contract/roll selection.
- The current [NSE IX site](https://www.nseix.com/) announced a 05:00 IST opening
  effective 26 October 2026. The full effective overnight schedule and business-date
  assignment were not established. **GIFT session and business date stay unknown**;
  the old 02:45/06:30 assumptions are not reused. Special Muhurat timing remains
  explicitly unverified.
- [FTSE Russell STI Ground Rules v3.9, May 2026](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/straits-times-index-ground-rules.pdf)
  identify regular calculation hours 09:00–17:10 Singapore time and no calculation
  on public holidays. This differs from [SGX securities trading phases](https://www.sgx.com/securities/trading):
  securities lunch is not labeled an STI calculation break. Known 2026 holidays
  use the [official Singapore holiday notice](https://www.mom.gov.sg/newsroom/press-releases/2025/0616-public-holidays-for-2026).
  Known half-days, unsupported years and unlisted special-session coverage remain
  uncertain. These are static calendar classifications, not exchange-status feeds.
- UTC storage retains separate exchange, provider, receipt and server-first-seen
  timestamps; UI displays UTC, IST and Singapore. No exchange/provider time or
  delay is manufactured from receipt time. At the frozen cutoff
  **2026-11-03T03:34:09.134789Z**, STI's ordinary calculation session was labeled
  open while its quote remained unavailable; GIFT and Nifty session were unknown.
- Known delay is included in stale-quote tolerance and remains labeled. Unknown
  delay/time yields partial quality for otherwise supplied quotes. Closed-session
  `ok` needs an explicitly identified last close matching a verified completed
  close; arbitrary old quotes do not become valid because a market is closed.
  Out-of-order arrivals remain invalid without lowering the last accepted time.
  Quoted futures require a business date and actual contract/expiry. Synthetic
  price/close/delay tests live only in isolated stores; no real price was obtained.

## Storage, tools, collector and UI

Additive migration **`20261103_0009`** creates
`market_context_observations`; no quote is disguised as a news article. Each row
has an immutable snapshot ID/body and server-observed availability. Later-received
data cannot answer an older cutoff. Frozen ID/scope allowlists and room maximum
cutoffs apply, equal-time ambiguity/retroactive inserts are refused, and A→B→A
plus out-of-order high-water behavior are tested.

Three real **availability-only** observations were saved at
**2026-11-03T03:32:31.864718Z**: GIFT, STI, Nifty cash. All have null prices and
`unavailable` status. They are not three quote successes. GIFT/STI raw hashes cover
availability/specification metadata, explicitly not a raw price response. Source
document hashes and configuration/calendar versions are retained.

`GET /research/market-context` and the `market_context` tool return at most three
saved observations. Reads use read-only transactions, a 3-second SQL statement
limit and **zero provider requests**; they never authenticate, migrate, ingest or
invoke models. A missing older observation produces a typed unavailable record
with null receipt/first-seen values, not a fabricated historical snapshot. A
room-specific API query preserves its cutoff. An ordinary source-experiment arm
does not gain this capability retroactively.

The tool's citation packet is labeled **derived market-observation summary**.
Packet `ok` means the metadata summary was retrieved; the embedded quote status
can still be unavailable. It is neither a verbatim exchange quotation nor semantic
verification of an agent claim. The independent audit shows why that distinction
matters: exact-span validation admitted cross-instrument interpretations.

Research Desk shows current cards and saved evidence cards: requested kind,
unresolved contract, source/specification, document hash, session at observation
and cutoff, quote/receipt/availability times, delay, basis, status and reasons.
Invalid/unavailable quotes and references are suppressed. Existing actual
discussion, source uncertainty, history and cancellation remain visible.

`make research-market-refresh` is an explicit **network-free availability recorder**,
not a quote fetcher. PostgreSQL admission is serialized and has a persistent
60-second minimum interval; cancellation/rate-limit cases write no extra rows.
The existing `_gift_nifty_check` now has a bounded, owned data subprocess hook
instead of a log-only placeholder. It adds no research/model scheduling or order
authority. The running broker worker was **not restarted** to activate that hook;
it will load on a normal later restart. The manual host refresh was exercised.

Before any future enabled provider polling, qualify rights, contract identity,
timestamps and its shared broker rate limit; do not bolt unrestricted calls onto
this hook. No duplicate execution client, continuous socket or paid fallback was
created in this phase.

## Measured checks, model run and browser recovery

| Check | Final result |
|---|---|
| Guarded disposable backend/Postgres | **164 passed, 3 skipped, 0 failed**. Two installed-Codex opt-ins passed separately on host; one unchanged host-only Scrapling dependency is absent in Docker. |
| Host stream/Codex, SQLite, snapshot/news/evaluation checks | **82 passed**; includes real installed Codex against loopback fixtures, no inference. |
| Frontend | **25 passed**, TypeScript and private-output Vite build passed. |
| Changed-file checks | Ruff passed on 25 Python files; whitespace checks passed. |
| Existing warnings | websockets deprecations; existing KnowledgeScreen bundle size. |

The initial new SQLite tests exposed three timezone-column read failures; fixed
by restoring UTC **only for SQLite's already-validated stored columns**, not by
guessing a timezone for provider inputs. The final checks above passed. The
verified internal disposable network/endpoint guard was retained; the destructive
graph integration directory was not collected and the operator graph was not deleted.

A database backup of **1,102,718 bytes** existed before schema application. An
existing config/auth storage read unexpectedly invoked `ensure_database_ready`,
applying the additive migration earlier than the intended disposable-validation
order. This is recorded rather than claiming isolation preceded local upgrade.
The later fresh disposable migration/API checks passed; no existing table rewrite,
downgrade, reset or backfill was performed.

New durably registered run **`market-context-20261102T175740Z`**:

| Frozen identity | Model / tool | Actual result |
|---|---:|---|
| `room:0e1c2e36-dc5a-55f9-91c9-100c1f371139` | 2 / 0 | Active-inference API cancellation; 10 events, no public messages, two unknown-usage calls. |
| `room:4feb11c2-948c-5628-adaf-acf1f7b5ab8a` | 23 / 23 | Source summary: 12 public messages, abstention/outcome; failed to retrieve the two known titles. |
| `room:4004fa0c-3f73-5953-9c4d-6fb7a84c0bfb` | 16 / 16 | Market context: 12 public messages, abstention/message limit; four real saved-data reads. |

Allocation was **12 development + 48 integration model admissions**, separately
the same tool ceiling. All continuations/retries counted. Total **41 / 39**;
reserved context **1,343,488** tokens, reported input **458,776**, output **5,142**,
**two unknown-usage calls**. Reservations are not consumed tokens. Unspent capacity
does not reopen a completed identity or the old 93/88 source run. Active participant
instructions remain SHA-256 `58bd97fdb300db89908729c0fad7297a60f831d3d2687b628e5c5844046969e3`;
model pair, binaries, GGUFs and serving configuration are unchanged. Candidates
remain inactive.

Direct provider qualification used **15 HTTP attempts** (14 public document/page
probes, one public Kite master); 13 returned 200, one returned an unfollowed 301,
one timed out. **Zero authenticated requests, sockets or subscriptions**. The
declared direct-provider ceiling was 40, authenticated ceiling 12 and socket
ceiling one. Official web search/open research is separately recorded; its
transport attempt count is unknown. Enabled collector/tool reads made zero
provider HTTP calls. Exact local model-forward consumption is not inferred for
the two cancelled unknown-usage admissions.

The source-summary failure is not a source-store outage: direct bounded reads with
proper topic/source fields return the saved SEBI accessibility title dated
30 October (date precision/+0530) and the undated PIB Coal India title. The room
put provider labels into literal topic searches, supplied end times after its
cutoff, then incorrectly generalized absence. It never produced the requested
useful primary-source summary. This acceptance check remains failed.

The market room correctly noticed null quotes and missing GIFT contract/provider
qualification, but **11 of 12 messages cited only `market:nifty_cash`**, including
GIFT assertions. It repeated a dispute about metadata usefulness and overstated
unverified entitlement as nonexistent entitlement. No numeric price, predicted gap
or trading action was invented. This is tool/UI verification and a retained
model-quality failure, not a reliable market conclusion. See the
[message-level audit](evidence/market-context-v1/narrative-audit.json).

Actual isolated Chrome verified **localhost:8502** and the current LAN
**192.168.1.41:8502**, rather than the no-longer-assigned `.33`. Cards, expanded
provenance, both actual 12-message discussions, cancelled history and reload/manual
reopen were checked. Controlled research-API shutdown showed useful market,
source, room and model-health 503 states without JavaScript errors or a quote.
Recovery used `make research-start`; models/worker remained running. After API
restart the **10 / 153 / 125** event sequences had identical hashes. Normal views
had no research API or JavaScript errors; favicon 404 remains. The research
services had been found stopped at resumption and were restored; boot ID was
unchanged, so this phase does not claim another reboot caused it.

## Preservation, artifacts and next task

All **2,065** original news IDs and payload hashes survived; normal producers added
nine records (final count **2,074**). Source history stayed **71 versions /
71 transitions / 6 fetch records**, with every original ID retained. Market
collection wrote only three new market-observation rows. Four protected control
records (`trading_enabled`, `new_entries_enabled`, `exit_only_mode`,
`block_new_entries`) match the before copies; normal `worker_status` and
`reconciliation_status` heartbeat records changed. Manual entry approval is true.
Original broker/API/DB/graph/dashboard container IDs remain; no task-driven broker
restart, account operation, control clear or order request occurred.

The five changing runtime files remain **uncommitted**. Three cache/status files
match their initial bytes, activity changed normally, and the full initial event
log prefix survives. Private before copies, full DB backup and stash **`b69b0eb` /
`stash@{0}`** remain. No ignored file was overwritten, reset/clean/force switch or
stash drop performed.

[Sanitized evidence](evidence/market-context-v1/manifest.json) records fixed inputs,
actual public messages, audit, counts, source/probe versions, checks, preservation
and browser hashes. Raw PDFs/HTML/master CSV, private DB/config, hidden reasoning,
screenshots/DOM and full native events remain outside Git at
`~/.local/state/kepler-rooms/market-context-20261102T175740Z/`.

Next: the required [visual agent workspace milestone](UI_MILESTONE_PLAN.md), using
the existing real events. GIFT quote activation still needs normal login plus
actual contract/provider entitlement and a verified current session/roll calendar;
STI needs permitted data access/retention. Semantic cross-instrument citations,
query repair and discussion repetition remain model/tool-quality work. None of
the visual office, TimesFM/advisory integration, broader scheduled rooms or
Harness² was implemented or charged to this phase.

## Copyable findings handback

```text
KEPLER MARKET-CONTEXT FINDINGS
Starting / source / evidence commits and branch: 6b2b84b; safe review FF410ccef; source30b5c39; evidence commit follows in git history; feat-generic-broker.
I1 terminal-stream correction and actual rejection/dispatch tests: recognized finish required before completed items/issued calls; length/error/duplicate/accounting regressions. Installed Codex+Bridge loopback: missing finish0 dispatch, valid tool finish1 stub dispatch; no inference.
I2 earlier-cutoff/reversion preservation: minimum predecessor/direct cutoff; A->B->A and frozen allowlists passed.
I3 undated omissions/continuation: service cap2/later-page omissions explicit; no continuation stated; scan1000 totals lower-bound, not exhaustive.
GIFT instrument/contract + provider and quote/history/socket capability: target NIFTY future, points/USD; current Kite GIFT row EQ/INDICES/blank expiry is not a contract. Auth expired; quote/history/socket blocked/unverified, no subscription.
Singapore exact index/proxy + provider/delay capability: STI cash index; no proxy; no qualified licensed quote provider or established delay/retention.
Calendar/session/timezone/holiday/reference sources and versions: NSEIX current full overnight schedule/business date unknown; FTSE STIv3.9 May2026 + official2026 holidays; regular09:00-17:10SGT, special hours unknown. Reference close absent.
Real snapshot statuses, timestamps/units/delay/basis and unavailable gaps: 3 saved unavailable/null-price observations received2026-11-03T03:32:31.864718Z; no exchange/provider time or delay. STI calendar open at cutoff; GIFT unknown; no spread.
Snapshot storage/as-of availability and data preservation: additive0009 immutable market table; first-seen/cutoff/frozen IDs; all2065 prior news retained,2074 final; source71/71/6 intact.
Tool/UI/collector behavior delivered: read-only market_context/API<=3 records,0provider HTTP; saved/current provenance cards; explicit60s availability refresh, bounded scheduler data hook; no live feed or new room scheduler.
Offline/disposable/frontend checks passed/skipped/failed: guarded164passed/3expectedskips; host82passed incl Codex; frontend25/types/build/Ruff passed. Initial SQLite failure fixed; no unsafe graph fixture.
Live source-summary/context rooms, actual useful facts and uncertainty: both12-message abstentions; source summary failed despite2saved titles; market retrieved null quotes but11/12 citations point only to Nifty cash. No reliability claim.
New run ID and model/tool/provider counts, actual/reserved/unknown usage: market-context-20261102T175740Z;41model/39tool;1343488reserved;458776input/5142output reported;2unknownusage.15directpublicHTTP/0auth/0sockets; web research attempts separately unknown. Allocation60/60 closed.
LAN/localhost cancellation/reload/API-restart evidence: currentLAN.41 +localhost; active-inference APIcancel, useful503states, reload/manualreopen;10/153/125 event hashes unchanged across APIrestart.
Broker/control/manual-approval and runtime-file preservation: original servicecontainerIDs,4protectedcontrols unchanged, approvaltrue; changing5runtimefiles local; stashb69b0eb and private backups retained. Normal heartbeat/news updates preserved.
Sanitized artifacts pushed / private evidence locations: docs evidence/market-context-v1 + findings; private ~/.local/state/kepler-rooms/market-context-20261102T175740Z/.
Remaining data/model limits and next task: no live GIFT/STI qualification; auth/contracts/rights/session gaps and semantic/query/repetition failures. Required visual agent workspace next per UI_MILESTONE_PLAN; not started here.
```

## Track C delivered in this phase — 4 November 2026

The scope update at `c4cedec` supersedes the earlier deferral language above.
Track C is now implemented at source **`3bd12d0`**: the main pixel-art office,
licensed character sprites, real event/state/message projection, agent/evidence
inspectors and saved-event replay. [VISUAL_WORKSPACE_FINDINGS.md](VISUAL_WORKSPACE_FINDINGS.md)
records actual localhost/LAN screenshots, fixture labeling, outage/reconnect,
mobile/accessibility and performance checks. The original A/B findings and room
records above are preserved. UI work added **zero model/tool/provider admissions**;
combined phase remains **41/39**, and the original market run stays closed.
