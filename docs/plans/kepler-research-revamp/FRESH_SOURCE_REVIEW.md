# Review of the delivered fresh-source slice

Reviewed 2 November 2026, Asia/Kolkata, at `34a3f40`; implementation source `0ba305a`. Terra reviewed storage/provenance and runtime behavior; a smaller Luna agent checked evidence arithmetic/status. Independent cloud checks and reproductions followed.

**Keep the delivered source service and installed Codex/model configuration.** This phase added useful evidence infrastructure. Its six paired rooms do not establish reliable research conclusions. The next work is [MARKET_CONTEXT_IMPLEMENTATION.md](MARKET_CONTEXT_IMPLEMENTATION.md): fix three concrete integrity issues, then implement read-only GIFT/Singapore context, with [local handoff](MARKET_CONTEXT_HANDOFF.md). Neither a new framework nor another prompt-only tuning round is needed.

## Delivered and supported by code/evidence

- Additive source-version/observation/fetch tables preserve namespaced identity, source/version first-seen time, meaningful revisions and A→B→A transitions. Existing news IDs were preserved in the local report; there is no historical backfill claim.
- SEBI/RBI metadata and a reviewed first-party PIB excerpt are available through saved-data reads. Date-only precision, unknown zones, issuer identity gaps and source coverage are explicit. Company filings are not delivered.
- `news_search` / `news_read` use bounded snapshots and Postgres read-only transactions. Current graph links carry source/version/hash references; Postgres snapshots remain authoritative for cutoffs.
- Research Desk shows source/date/identity/revision/quote provenance alongside actual public discussion. Local reports verify LAN/localhost display, API restart and reboot recovery; the original run was not renewed.
- The earlier silent tool-limit reason is repaired. Post-run marked model-limit errors are narrowly attributed by role/turn, preserving unrelated-error precedence.

## Independent checks and their limits

| Check | Cloud result |
|---|---|
| Focused backend/source tests | **87 passed, 11 skipped**; skipped checks need disposable Postgres/graph infrastructure. The destructive graph integration directory was not collected. The pinned host Scrapling parser test passed. |
| Frontend | **22 passed**, TypeScript and build passed, temporary build output. Existing KnowledgeScreen bundle warning remains. |
| Changed Python lint | Ruff passed on **27 files**. Existing Starlette/lxml deprecation warnings remain in tests. |
| Export integrity | All **30** listed evidence files matched sizes and SHA-256s. This validates the sanitized export, not a replay of private DB/browser/GPU operations. |
| Accounting/denominators | Recomputed exported room totals/outcomes/message counts; they match the supplied summary. Unsupported labels remain the authored narrative audit, not a new independent regrading. |
| Integrity probes | Three defects reproduced using actual application classes with temporary SQLite and a controlled loopback HTTP/SSE fixture. No real model inference, graph/broker operation or external fetch. |

The reported **157 backend passes / one Docker parser skip**, actual graph references, 2,003-ID preservation and live UI/reboot checks remain local execution results. This cloud review did not access the user's PC. [Validation and probe evidence](evidence/cloud-review-34a3f40/manifest.json) records exact scope and reproducible source.

## What the paired rooms show

| Three unique questions per arm | Ordinary tools | Saved-source tools |
|---|---:|---:|
| Relevant reviewed title retrieved | 0/3 | 3/3 |
| Published messages | 11 | 23 |
| Clear unsupported/unqualified messages in saved audit | 5/11 | 1/23 |
| Abstentions | 1 | 2 |
| Failures | 2 | 1 |
| Concluded/disagreed rooms | 0 | 0 |

This is useful retrieval evidence. The unsupported-message fractions contain repeated claims and are not independent fact trials, accuracy estimates or a reliable improvement percentage. Saved RBI includes a “record in window” statement despite unknown timezone/window membership. Several ordinary messages repeat one old parser assertion or infer source-wide absence from empty artifact searches. Exact title identification does not verify interpretation.

The three failed rooms exhausted their **16 model admissions** and recorded model denials. The old Codex 429 handling discarded the causal body, so those records say `peer_failure`. The later marked-protocol fix was verified with installed Codex/Bridge at zero provider admissions. Keep the old failures unchanged; this check does not turn them into successful research or rerun the six rooms.

The three abstentions had no recorded budget denial. Public messages show partial retrieval, repeated questions and date/coverage uncertainty; the sanitized export does not establish one common cause for all three. Ordinary graph/files/browser are current views without verified historical capture, so the arms are not a strict historical causal replay.

Accounting matches **93 model / 88 tool admissions**: development 14/12 and frozen 79/76. Reserved context is 3,047,424 tokens; recorded input/output is 643,713/9,962 with two unknown-usage calls. Reservations are not consumed tokens. Unspent allocation is not permission to reopen this completed run.

## New findings to fix

| ID | Reproduced behavior | Required correction |
|---|---|---|
| I1 — stream completion | [adapter.py](../../../swingtradev3/research_room/adapter.py#L269) starts `finish=None` and reports completion unless the reason is `length`. A controlled stream ending at EOF or `[DONE]` without any finish reason produced `response.completed`. A valid-looking tool JSON at EOF was emitted as an actionable function call. The probe did not execute that tool. Explicit stop/length controls behaved as expected. | Require a recognized terminal reason for completed output/actionable calls. Missing/unknown terminal state must remain failed/incomplete; incomplete calls cannot become executable just because their JSON happens to parse. Preserve valid stop/tool/length, cancellation, IDs and accounting. This was not demonstrated as the cause of the historical paired failures. |
| I2 — earlier cutoff widened | [tools.py](../../../swingtradev3/research_room/tools.py#L409) keeps the earliest version cutoff after search, but the predecessor registration at line 425 overwrites it. Retrieving A at January 2, then successor B at January 4, made a later read of A use January 4 and report later supersession metadata. | Keep the earliest applicable cutoff when registering predecessor versions too, or bind reads to an explicit retrieval context. The A body is immutable and the room maximum is not exceeded; the bug exposes later revision metadata relative to the earlier requested search cutoff. Test A(t1) → B(t3) → read A and A→B→A. |
| I3 — omitted undated results | [news_evidence.py](../../../swingtradev3/research_room/news_evidence.py#L78) returns at most two undated records. The repository tracks truncation against its own six-record cap. With three dummy undated matches, the actual service returned two and `undated_truncated=false`, with no undated continuation. | Propagate the service-level omission/cap and count; provide a bounded continuation or label omitted results explicitly, including later dated pages. The existing overall bounded-coverage wording does not replace a correct specific truncation flag. |

See [probe results](evidence/cloud-review-34a3f40/probe-results.json). These are inspection/reproduction findings, not claims of a live account incident. Fix them with offline regressions before trusting model-dependent tests of new market-context tools.

## Next phase decision

The source service is a delivered foundation with limited coverage. Keep improving it through these precise fixes; do not require reliable financial reasoning before building a deterministic, read-only market-data service.

Proceed to **GIFT Nifty and Singapore market context** after the integrity fixes, with provider capability discovery independent of that work. Verify instrument/contract identity, current read-only entitlement, source timestamps/delay, market sessions and snapshots. Show unavailable/delayed/stale states honestly. A small live room can explain verified provider observations and explicit limits; no automatic entry, sizing or protective-order authority is added.

Existing `api/tasks/scheduler.py:_gift_nifty_check` currently only prints during an overnight window. Configuration keys and that log are not GIFT data support. `MacroIndicatorsTool` supplies cached macro values but discards quote timestamps and has a four-hour cache; it is not a qualified live GIFT/STI feed. Reuse appropriate components while adding the required metadata.

Company filing access, complete publication coverage, RBI/PIB timestamp evidence and semantic grounding remain open. TimesFM, broad autonomous room scheduling, Harness² and the optional office view remain later capabilities. A rough implementation-planning estimate is **45–50%**; it is not research accuracy or a time-to-finish estimate.
