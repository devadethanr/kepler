# Fresh primary-source evidence — findings and handback

Implemented 2 November 2026 on `feat-generic-broker`, starting at **7037018**.
Source commit: **0ba305a**; sanitized findings/evidence are committed separately. The existing
Codex participant instructions, inactive benchmark candidates, model pair and
serving configuration remain unchanged. This is a source-service slice, not
financial qualification or a new prompt study.

## Delivered scope

- Controlled primary-feed acquisition reuses the news package and existing
  `NewsRepository`, `news_articles`, provider conventions and execution-event
  projection. The package's public aggregator export is lazy so minimal host
  reads do not import paid fallbacks or the full application dependency stack.
- Explicit migration **20261102_0008** adds `news_source_versions`,
  `news_source_observations` and `news_source_fetches`. It changes no existing
  row IDs and performs no legacy backfill. SQLite and guarded disposable
  Postgres validation preceded a private full database backup and local upgrade.
- Unchanged retained content reuses its immutable version without duplicate
  ingestion events. Raw fetch hashes remain provenance, rather than causing
  revisions for volatile HTML telemetry. Meaningful content/date/provenance
  changes preserve prior versions; A→B→A history remains observable.
- `news_search` and `news_read` are bounded saved-data reads. Their Postgres
  transactions are read-only; they cannot fetch, migrate, call broker tools or
  mutate graph state. Search returns six dated records plus at most two
  separately labeled undated records. A 1,000-candidate scan and 50 dated-result
  ceiling, pagination limits and incomplete coverage are disclosed.
- Each new room pins a source-availability cutoff. Saved versions must have been
  observed by that cutoff. A frozen allowlist is applied after as-of revision
  ranking and before caps; it cannot make a superseded version current. Reads
  retain the search's cutoff. Legacy rooms without a pin must start a new attempt
  to use source tools. Explicitly linked superseded versions can be read in an
  unrestricted room and remain labeled as superseded.
- Current news articles and the existing controlled graph repository carry source
  key, immutable version, content hash and first-seen references. **61 current
  graph nodes** were reprojected through that repository and read back with the
  expected version references. No arbitrary/model-owned graph write was added.
  The graph remains current-only; Postgres revisions are authoritative for cutoffs.
- The existing Research Desk displays source acquisition/freshness, coverage,
  raw publication date and precision, zone basis, observation/fetch times in UTC
  and IST, revision, identity basis, exact quote and claim provenance. Loading
  and source/service errors leave a usable page.

## Local sources and access boundaries

| Source | Observed result | Retention and coverage |
|---|---|---|
| [SEBI RSS](https://www.sebi.gov.in/sebirss.xml) | 200 XML, 30 entries; conditional repeat 304 | Identification metadata/title/link only. [Website policy](https://www.sebi.gov.in/website-policy.html) requires prior permission for reproduction of material; article bodies were not ingested. Current feed window, no archive-completeness claim. |
| [RBI press releases](https://rbi.org.in/pressreleases_rss.xml) | Initial local timeouts; controlled fetch recovered, 200 XML, 10 entries | Identification metadata/title/link only; body-retention permission remains unconfirmed. Earlier timeout observations do not describe the later successful fetch. |
| [PIB English RSS](https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=48) | 200 XML, 20 entries; all lacked publication dates | Government releases, not exchange/company filings. The direct English endpoint avoids the observed bare-host redirects to a Hindi feed. |
| [Reviewed PIB release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2317034&lang=1&reg=6) | 200 HTML; Scrapling extracted 974 normalized text characters | Ministry of Finance first-party release, with attribution. [PIB policy](https://www.pib.gov.in/content/102_2_Copyright-Policy.aspx?lang=1&reg=30) excludes third-party material. Only reviewed text paragraphs were retained; images, attachments and other page content are omitted. |
| NSE company coverage | Local connection/timeout failures; earlier cloud empty RSS is historical | Not enabled. [NSE terms](https://www.nseindia.com/static/nse-terms-of-use) and reproduction/storage restrictions need a suitable access path. Empty or unreachable feeds cannot establish no announcement. |

Scrapling **0.4.15** and its parser dependencies are pinned in the isolated host
lock. No stealth/challenge bypass, crawler, personal profile, paid fallback, model
download or model-serving environment replacement was introduced. A PIB release
must use a numeric release ID on an approved release path/host and have explicit
first-party/terms review before controlled retention.

Requests use exact public HTTPS hosts, global-address validation, TLS/SNI pinning,
bounded bodies, conditional headers, two feed attempts, backoff and a supervised
25-second job deadline. Feed redirects are refused. Refresh admission has a
60-second floor and cross-process database owner locking. HTML uses the existing
supervised public-fetch policy. Unknown request outcomes are not reported as zero.

## Dates, identity and preservation

SEBI's observed `30 Oct, 2026 +0530` now retains a calendar date, explicit source
offset and **date** precision, without inventing a publication instant. A date
interval must fit the requested window and cutoff. Minute/second precision is
also treated conservatively as an interval. RBI raw date/time strings have no
declared zone; UTC publication/window membership remain unknown. PIB RSS dates
are missing; the reviewed HTML's raw Posted On clock has unknown zone. Raw values
are preserved rather than silently assigned IST.

Publication, event, source first-seen, version first-seen, version-transition fetch
and latest feed-check times are distinct. An old publication newly observed today
does not prove availability to yesterday's decision. Unknown dates can be shown
separately but never become dated-window matches. Missing events/units/currency/
period stay unknown rather than being inferred from a name or record ID.

Provider entry identity is namespaced. Raw GUIDs, URL fallback basis, content hashes
and revisions are retained. Regulator/government origin is distinct from verified
issuer identity. All ingested issuer mappings remain **unmapped**; no ticker/ISIN
or event ID was manufactured from a mention or requested room label. Exact URL
duplicate groups are exposed; identical retained-text hashes are hints, not proof
that differently addressed publications independently corroborate one another.
There is no general syndicated-copy or prose contradiction classifier.

The frozen cutoff contained **61 versions**. A later RBI repeat created ten
metadata revisions after a terms-label correction: **71 immutable versions,
61 current source items**. Older IDs and first-seen history remain intact; the
paired rooms continued to resolve their original cutoff versions. SEBI repeat
returned 304 and changed zero items. A third RBI repeat was not performed, so
its live repeat must not be reported as an unchanged-content idempotency pass.

All **2,003 original news IDs** still exist. The source owner's 71 ingestion events
overwrote **zero** of those IDs. Nine legacy payloads received normal existing
SEBI ingestion updates at 06:00 IST while work was paused, and one other legacy
article was added. Those updates were retained, not replaced with the backup.
The final current article count is 2,065, including 61 source-owned current items.

## Terminal reasons and demonstrated failures

The requested denied-tool → normal silent/no-mail sequence now records `tool_limit`
instead of `no_pending_mail`. Denials carry role/turn identity and sequence; a
later turn/publication invalidates stale attribution. Valid outcomes, cancellation
and unrelated exceptions keep precedence. Regressions use real durable SQLite
admissions and cancellation, with no inference.

The development room exposed a real null-time bug: a minute-precision PIB record
with unknown timezone had no UTC datetime, causing every source search to return
`unavailable/AttributeError`. Its **12 model/12 tool** calls and abstention are
retained. Offline regression now treats that record as undated; direct saved-data
reads found all three frozen references before paired generation. The separate
development cancellation interrupted active inference: **2 model/0 tool** calls,
one terminal cancellation. No failed room was retried under a new identity.

Three paired rooms later hit model limits and recorded generic `peer_failure`
because Codex discarded an HTTP 429 response body. Those historical records are
unchanged. After the paired run, the adapter was corrected to send a marked
Responses failure. The **installed Codex + actual Bridge** preserved that marker
in a deliberately exhausted, isolated zero-admission room, producing typed
`call_limit` with **zero model/tool admissions**. Only a matching role/turn denial
plus the explicit marker is classified; a generic 429, stale denial or unrelated
error is not. Captured-protocol and real HTTP Bridge regressions pass. This
diagnostic correction was not used to relabel old results or claim a model gain.

## Frozen comparison and grounding audit

Run **fresh-source-20261101T195640Z** froze three new real questions, independently
authored and reviewed before inference: SEBI accessibility identification, RBI
Treasury-bill identification with unknown zone, and PIB Coal India mention versus
company-disclosure coverage. Synthetic adverse records stayed exclusively in
disposable test storage. The source case SHA is
`b5b8a502bf2ac854a1516e0fb866ef1117f51fd0d7819fa5c1cf778ea629011e`.

Two development rooms allocated 24 model/tool admissions; six paired rooms
allocated 96 of each, at 16 per room. One immutable run-plan hash and the allocated
room IDs are durably registered in existing cognition storage. Altering the plan
for the same run is rejected; cancellation/reboot does not refund or renew it.

Both arms kept the same active instructions, models, question, explicit window,
cutoff and ordinary tool policy. Only the saved arm received source operations
and the frozen source-version allowlist. Ordinary graph/files/browser tools are
current views, not proven point-in-time captures: this is a functional comparison
of evidence access, **not a strictly controlled historical causal replay**.

The pre-generation rubric separated relevant-source retrieval, attribution,
source-fact correctness, publication uncertainty, usefulness, unsupported public
assertions, conversation outcomes and resource use. There was no new financial
accuracy threshold and no transfer of the old 27/30 assessment target.

| Observed metric | Ordinary tools | Saved-source tools |
|---|---:|---:|
| Unique questions / rooms | 3 / 3 | 3 / 3 |
| Relevant reviewed title retrieved | 0/3 | 3/3 |
| Public messages | 11 | 23 |
| Messages with admitted references | 3, historical non-primary artifact | 20, repeated references to three primary titles |
| Clear unsupported/unqualified assertion messages | 5/11 | 1/23 |
| Completed conclusion / disagreement | 0 / 0 | 0 / 0 |
| Abstention / failed | 1 / 2 | 2 / 1 |

The unsupported counts are **message-level** independent audits, not independent
market facts. Three ordinary messages repeat one stale parser-state assertion;
one RBI and one PIB ordinary message infer feed absence from empty artifact
searches. The saved RBI room says a record is “in the window” while its timezone
and membership are unknown. Ambiguous PIB “disclosure”/one-record/headline wording
is recorded separately, not automatically counted as a false fact. Saved rooms
found useful identification facts but still repeated themselves and incompletely
explained date/coverage limits. Exact title citations do not verify interpretation.
No invented rates, deadlines, ISINs or event IDs were found in this small saved-arm
sample. This does not establish general or financial accuracy.

Actual usage: **93 model admissions, 88 tool admissions**; development **14/12**,
frozen **79/76**. Reservations **3,047,424** tokens; reported input **643,713** and
output **9,962**, with **2 unknown-usage calls**. Reported usage is incomplete, not
zero for those calls. Twenty-seven model and 32 tool admissions remain unspent;
the run is complete, not silently renewed. Provider HTTP requests, observed
rejections and the zero-admission protocol check are separate. Exact HTTP totals
are unknown: five measured feed requests, one HTML job bounded at four, at least
21 earlier probe responses/attempts, and a lost orchestration attempt conservatively
bounded at ten. See [results](FRESH_SOURCE_RESULTS.md) and
[sanitized evidence](evidence/fresh-source-v1/accounting.json).

## Verification and local activation

- **157 backend/provider/guarded disposable Postgres/graph tests passed; one
  Docker Scrapling test skipped** because the parser is host-only. The same
  extraction passed with the pinned host parser. Host source/identity/cutoff
  regressions and the actual Codex zero-admission protocol check passed.
- **22 frontend tests**, TypeScript and private-output Vite build passed.
  Changed-file Ruff and whitespace checks passed. Existing dependency deprecation
  and large KnowledgeScreen chunk warnings remain.
- The first disposable graph launch exceeded its old startup grace; a test-only
  90-second start period fixed it. The internal disposable network, independent
  endpoint checks and deletion guard were retained. No operator-graph deletion
  fixture was run.
- Actual isolated Chrome on **localhost:8502** and **192.168.1.33:8502** displayed
  all three saved-source rooms with expanded quote/revision/date/identity fields.
  No JavaScript exception or research HTTP error occurred; favicon 404 remains.
  A real stopped research API produced useful 503 states on both origins.
- A host reboot at **21:55:33 IST, 2 November** removed transient research units
  and earlier `/tmp` browser captures. Recovery used `make research-start` with
  the original configuration and original run ID. All run counters stayed the
  same; no model generation was repeated. Fresh browser evidence was saved to
  the persistent private run directory.
- A subsequent API-only restart retained identical event hashes for the saved
  rooms (**109/88/75 events**). Reload plus manual reopen restored each history.
  Selected-room persistence across full reload remains optional/unimplemented.
- Original broker/API/database/graph/dashboard **container IDs remain the same**;
  their start times advanced with the host reboot. No task-driven broker restart,
  driver change, migration of brokers, login/token refresh or order action occurred.
  Research models/API/worker are running through the runbook. Source refresh is
  explicit, not a new autonomous ingestion daemon.
- Trading/new-entry/exit-only/block control records matched their private
  before snapshots. `require_entry_approval` is still **true**. The existing Desk
  can show stale-auth/degraded indicators; this task does not clear broker controls.

The five tracked runtime files remain local: `agent_activity.json`,
`event_log.jsonl`, `macro_cache.json`, `regime_cache.json`, `scan_status.json`.
The three cache/status files match the initial bytes; the event log retains its
entire original prefix, and activity changed normally. Initial copies, database
dump and newer local state are preserved. Backup stash **b69b0eb / stash@{0}**
was retained. No reset, clean, forced switch, stash drop or filled credential commit.

## Artifacts and remaining scope

Public artifacts contain selected identification metadata, frozen hashes and
allocation, sanitized public discussion/counters, audit findings and check/recovery
metadata. They exclude raw HTML, model reasoning, credentials, private DBs and
runtime/account contents. Private evidence is at
`~/.local/state/kepler-rooms/fresh-source-20261101T195640Z/`, including the original
database backup, source probes, native records, frozen execution sources and
`browser/` screenshots/hash checks.

Remaining limits: company filings lack an authorized established-issuer source;
regulatory feeds are rolling and not comprehensive; RBI timezone is unestablished;
PIB feed dates are missing; body retention is restricted; source cards disclose
unknown snapshot coverage alongside bounded retrieval completeness. Differently
addressed syndication and semantic contradiction are not solved. Publication-level
unit/currency/period extraction and semantic claim validation remain unassessed.
The models still confuse availability with publication/window membership and fail
to finish some bounded discussions. Candidates remain inactive. Future work is
better source coverage/semantic calibration, then GIFT/Singapore context,
informational TimesFM and scheduling. None was started in this slice.

## Copyable findings handback

```text
KEPLER FRESH-SOURCE FINDINGS
Starting / final commit and branch: 7037018 -> source 0ba305a, subsequent docs commit in git history; feat-generic-broker.
Remaining terminal-reason fix and regression: silent tool-denial exit -> tool_limit; stale/outcome/cancel precedence tested. Marked model denial survives real Codex with zero admissions; old failed records retained.
Sources tested, HTTP/content status, source type and access/retention terms: SEBI 200/30 + repeat304; RBI recovered200/10; PIB RSS200/20 + reviewed HTML. Regulator/government metadata, no company filings; SEBI/RBI bodies excluded, PIB attributed first-party only.
Observed publication formats, precision/zone and cutoff handling: SEBI date/+0530; RBI clock zone unknown; PIB RSS missing dates, HTML zone unknown. Availability requires first observation by cutoff; unknown dates stay unplaced.
Issuer/event identity basis and ambiguity handling: namespaced record identity, raw GUID/URL fallback; regulator origin/text mention != verified issuer/event. No IDs inferred from requested labels.
First-seen/version/dedup behavior and existing-data preservation: 61 frozen versions, 71 later immutable versions/61 source items; old refs retained. All 2003 legacy IDs preserved; source owner overwrote none. Normal background updates retained.
Tools/controlled graph linkage and UI fields delivered: read-only news_search/news_read, bounded revisions/spans/coverage; 61 controlled current graph refs; Desk date/identity/revision/claim provenance.
Offline/disposable tests passed/skipped/failed: 157 passed/1 host-only Scrapling skip; host extraction passed; 22 frontend, types/build/Ruff passed. Initial test health startup fixed; recorded development source bug fixed offline.
Frozen real/synthetic task counts, rubric and paired arm definition: 3 new real questions x 2 arms; adverse synthetic fixtures isolated. Same active policy, saved-source access difference; ordinary current views limit causal attribution.
Active instructions/model/tool/snapshot hashes: frozen/final execution manifests (tool b3222457...); INSTRUCTIONS 58bd97fdb300db89908729c0fad7297a60f831d3d2687b628e5c5844046969e3; cases b5b8a502...; installed models/config unchanged.
Run ID, total model requests and actual/reserved/unknown usage: fresh-source-20261101T195640Z; 93 admitted model/88 tool; 3047424 reserved; 643713 input/9962 output reported, 2 unknown. No reboot renewal.
Retrieval coverage, useful supported facts, attribution and unsupported claims: titles 3/3 saved vs0/3 ordinary; unsupported assertion messages1/23 vs5/11, repeated facts not independent. No financial-accuracy claim; 3 abstentions/3 failed paired rooms.
Actual rooms, cancellation, reload/API restart and service activation: 6 paired +2 development rooms retained; active-inference cancel passed; LAN/localhost source cards and109/88/75 event hashes survive restart; research units recovered after host reboot.
Broker/control/manual-approval and runtime-file preservation: original container IDs; host reboot advanced starts; no task broker restart. Control records unchanged, manual approval true; five runtime files local, stash b69b0eb retained.
Sanitized evidence pushed and private evidence locations: evidence/fresh-source-v1 and findings/results; private ~/.local/state/kepler-rooms/fresh-source-20261101T195640Z/.
Remaining source/model limits and next capability: incomplete company coverage, dates/terms/syndication/semantic grounding and bounded discussion completion. GIFT/TimesFM/scheduling remain later work.
```
