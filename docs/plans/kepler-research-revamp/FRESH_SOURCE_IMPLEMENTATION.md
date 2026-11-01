# Next implementation: fresh primary-source evidence

2 November 2026. Starting point: `feat-generic-broker@ae7d45f` plus the review-doc commit. Read [POST_TUNING_REVIEW.md](POST_TUNING_REVIEW.md). The room, LAN UI and most R1–R8 fixes are delivered. Keep Codex, the local adapter, Gemma/Qwen profiles and current active participant instructions.

## Intended result

An agent can ask what changed in a selected company or regulatory topic over a declared time window, retrieve actual available primary-source records, challenge the evidence with its peer, and display a cited summary with honest gaps. The source service prepares and stores evidence; agents retain adaptive discussion rather than a fixed speaking sequence.

This phase is not another model/engine search or prompt-only tuning loop. Retained candidates remain inactive. Good data contracts do not by themselves prove a source true or make the models reliable; the desk continues to distinguish observations, proposed interpretations and uncertainty. Live entries still require manual approval.

## 0 — close the remaining terminal-reason edge

Handle the relevant tool-budget denial when a turn finishes without publishing and the worker exits through the no-mail path. Record the actual call/tool/deadline cause instead of `no_pending_mail`. Add the focused sequence regression and retain current cancel/lease/outcome precedence. Avoid treating an old `last_denial` as the cause of every later exception. No inference is required for this correction.

## 1 — inventory and reuse the current source code

Use the existing modules rather than another ingestion framework:

- `data/news/feed_providers.py`: feed acquisition and per-source results.
- `data/news/core.py`: item building, date parsing, caching and persistence boundaries.
- `data/news/constants.py`: configured sources and source categories.
- `memory/repository/news.py` and existing news tables: canonical reads/storage/provider health.
- `research_room/grounding.py`, `tools.py` and the current desk: typed evidence and public discussion.

Identify which code is safe for the host research environment. The installed minimal host lock is not the entire application dependency set. Reuse normal application ingestion where appropriate and keep host tools as narrow reads; pin only genuinely needed additional dependencies in the correct isolated environment. Do not install the full model/application stack or load another model merely to fetch news.

Keep the existing broker/news callers compatible. An ingestion owner may write source records and controlled projections; the room gateway stays read-only except for its own messages/events. Do not let an incidental aggregator import silently change room permissions or enable paid provider fallbacks.

## 2 — implement a small usable source set

Start with **two reachable primary-source feeds**. SEBI/RBI are viable candidates from the cloud probe. Revalidate from the local host and record HTTP/format/date/coverage results. A company-disclosure question additionally needs a usable exchange/company source with established issuer identity; the observed empty NSE RSS response is not enough to support “no announcements.”

If company coverage is not yet usable, deliver a clearly scoped regulatory-release task first, such as “What do the configured SEBI/RBI sources show for this date window, and what remains unknown?” Mark company-disclosure coverage incomplete and report the blocker. Do not fabricate a company example or silently substitute a publisher headline as a primary filing.

For each source, record endpoint, source owner/type, content/retention terms checked, identifier and pagination/coverage behavior, date/time convention, refresh budget and error/empty states. Treat exchange filing, regulator release, company IR, broker blog and publisher article as distinct types. Configured heuristic confidence is a ranking hint, not a correctness probability.

Requirements:

- Preserve raw date text, source-declared zone, parsing basis and precision. The observed SEBI date-only format must retain date precision; do not invent a clock time and claim it was published at that instant. Handle timezone-less values only with an explicit source convention. Missing/invalid dates stay unknown.
- Distinguish publication, event, fetch and first-seen time. Show UTC storage and IST display consistently. Enforce decision cutoffs using what was actually available; newly backfilled old publications do not prove availability to an earlier run.
- Separate HTTP failure, challenge/non-feed content, malformed feed, valid empty feed, no query matches, stale source and unknown freshness. HTTP 200 is not complete ingestion success.
- Preserve source/entry IDs and canonical URLs; apply namespaced identity where provider GUIDs could collide. Deduplicate mirrored/syndicated items without treating copies as independent corroboration.
- Use bounded requests, rate limits, retry/backoff and conditional fetch where supported. Carry the existing deadline/cancellation and public-fetch policy into linked-page extraction.
- Respect source access/retention terms. Store permitted snippets, metadata/hashes and references when full retention is inappropriate. PDFs/other unsupported attachments remain explicit references/unavailable content, not invented full text.

Add **Scrapling as the already planned bounded extraction adapter** for a selected permitted HTML source where it helps. Pin its release/dependencies, use ordinary fetching/parsing/selector support and preserve provenance/completeness. Keep RSS parsing simple. Do not introduce a broad crawler, challenge bypass, personal browser profile or unrestricted scraping service. Reuse the existing isolated browser only when a demonstrated page task requires it.

## 3 — preserve evidence snapshots and identity

Extend the existing storage rather than create a competing source-of-truth store. At minimum record:

```text
provider/source_id/source_type, provider_entry_id, canonical_url,
content_hash/version_id, first_seen_at, fetched_at,
published_raw, published_at_or_date, timezone_basis, precision,
event_at_if_known, requested_cutoff, retrieval_scope/completeness,
issuer identifiers and identity_basis, source spans/reference,
status/error/delay and supersedes/revision relation
```

Reuse existing columns where semantics fit. If immutable revisions require additive tables/columns, make the migration explicit, preserve existing rows/IDs, test on disposable Postgres and back up the intended local database before application. No reset, wholesale history rewrite or unannounced schema side effect.

The same unchanged item should not create endless duplicate events; changed source content preserves its prior revision. A first-seen time is not refreshed on reread. For historical requests require known availability by the cutoff or state that historical availability is unsupported; do not query current overwritten rows and call that a causal replay.

Issuer identity must distinguish exchange/ISIN/provider mapping from text mention, ambiguous alias and the room's requested label. Do not infer an event ID merely from company name or record ID. Keep units/currency/period explicitly known or unknown for any extracted quantities. Do not invent arbitrary prose entailment, event matching or contradiction with string rules.

Link records into the existing graph projection only through the controlled ingestion/projector path, with source/version references. Keep Postgres/source snapshots authoritative; stale/current-only graph views must disclose their cutoff limits. No arbitrary Cypher or model-owned graph mutation is added.

## 4 — give the existing agents useful read tools

Expose bounded `news_search` / `news_read` operations (or names consistent with the existing gateway). Search takes an explicit topic/entity mapping, time window/cutoff, source set and result/page bounds; read resolves an authorized saved record/version. Return provenance, identity basis, date precision, coverage, excerpt offsets and relevant contradictory records.

Keep allowed quote IDs, exact source spans and metadata checks. Label unsupported/missing/future/partial evidence explicitly. A genuine quote may still be irrelevant; the model's support assessment remains unassessed narrative. Direct source facts and heuristic/inferred facts must be visibly distinct.

Both participants can independently ask for sources, challenge coverage and revise their positions. Keep call/time/resource limits shared. Do not force consensus, give a model order authority, or replace the active participant prompt with the benchmark's copy-a-claim contract.

## 5 — extend the current Research Desk

Show source status/coverage, publication precision versus fetch time, issuer/event mapping basis, saved revision and the excerpt used by a claim. Add a source/evidence panel within the existing desk/news surfaces, not another standalone UI. Preserve live messages, older-room access, terminal state, reload and cancellation behavior.

Small optional polish while touching these paths: retain the selected room in a URL/local setting, disable repeated Cancel submissions while pending, and prevent overlapping stale polling responses. Test the actual loopback and LAN origins. The earlier UUID blank-screen defect is resolved; do not spend this phase rediscovering it or replacing the desk with animation.

## 6 — validate behavior on real evidence, not another seen benchmark

First complete offline provider/date/snapshot/idempotency/identity tests and disposable-DB checks. Use synthetic adverse fixtures only in isolated test storage and label them as synthetic. Preserve all old prompt scores; seen cases are regression cases.

Before any fresh model calls, freeze a small new question/evidence set and its independently reviewed expected facts, source coverage, negatives and uncertainty. Include an actual permitted primary-source task, wrong-company/event evidence, date-only/unknown dates, source unavailability, stale revisions, duplicate sources and a real but irrelevant quote. Record which cases are real versus synthetic. Do not ask the models to grade their own outputs.

Compare the **same installed participant policy** on matched tasks with ordinary current tools versus the new saved evidence service. Pin the shared as-of snapshot and define exactly what each arm can retrieve. Keep policy/tool settings otherwise matched so the comparison targets evidence availability/representation, not simultaneous prompt tuning. Use independent copies/room IDs to avoid peer/context contamination.

Measure retrieval coverage, correct issuer/event attribution, relevant-span selection, source/fact correctness against reviewed records, unsupported assertions accepted, supported-case usefulness, calibrated wording/abstention, conversation outcomes, latency/calls and actual-versus-reserved/unknown usage separately. Audit changed narratives rather than applying supplied-claim labels to different text. Report unique questions/cases and all denominators; duplicate room requests are not independent market evidence.

Suggested fresh inference ceiling: **120 total model admissions**, including development, model continuations after tools, paired rooms, retries and model-backed cancellation/UI smoke checks. Allocate at most 24 model admissions to development and 96 to frozen/integrated checks. Separately declare and enforce at most 120 tool admissions for this run, retain the existing per-room tool ceilings, and log provider HTTP requests/rate limits separately. A tool action is not itself a model request; every subsequent generation still consumes the model ceiling. Predeclare a feasible number of paired questions and per-room call/time ceilings; use fewer questions if tool loops require more requests. Do not promise 30 one-call cases for a multi-turn room. Stop at the declared ceiling and report incomplete coverage instead of renewing a budget by changing names or starting a recovered process.

The completed prompt run's 27/30 objective remains failed and belongs to its supplied-claim task. Define new source/room metrics and any functional targets **before** running; do not silently transfer or lower the old threshold. Zero unsupported claims in a small sample is a sample result, not financial qualification. Candidates remain inactive; this phase builds useful evidence capability without requiring their promotion.

## Deliver and hand back

- Run focused backend/provider tests, protected disposable Postgres/graph checks when relevant, frontend tests/typecheck/build and changed-file lint.
- Verify local ingestion, one real live discussion plus a missing/contradictory-source case, source provenance display, cancellation and saved-history/API restart. Check service identities and broker/control preservation.
- Activate only the needed research/API/ingestion changes through the existing runbook and supported IDE launch context. No driver/engine/model changes, token refresh, order action or forecast-authority change.
- Update `FRESH_SOURCE_FINDINGS.md` with measured code/source versions, before/after fields, tests/skips, source access/terms status, immutable snapshot evidence, call accounting, public room records and remaining limits. Commit source and sanitized docs on this branch; preserve changing runtime files and private backups/logs.

Then proceed to GIFT/Singapore context, the repaired informational TimesFM tool and scheduled/event-driven research. Harness² and the optional office view remain later work. Continue reversible implementation within scope; only concrete dependent blockers need clarification, not a new Codex-selection approval.
