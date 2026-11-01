# First usable research room — implementation and verification

Normal-app activation follow-up: the first report below records the earlier isolated verification. The user subsequently authorized normal API activation; that is now complete at :8502 with running research services and normal database history. See [LOCAL_ACTIVATION.md](LOCAL_ACTIVATION.md) for 89 passing focused checks and live UI/browser/cancel/restart results.

1 November 2026. Branch `feat-generic-broker`, starting HEAD `beaa5df`. Changes remain in the working tree. No commit, push, broker migration, production restart or new live-entry authority was performed.

**The first room slice is connected and verified.** Two native Codex threads used the pinned local model pair, retrieved actual research files/current graph, exchanged five addressed public messages, and ended with preserved disagreement and an analyst abstention. The Research Desk showed those actual records and restored them after reload. Source excerpt validation passed; **general model extraction accuracy remains poor** and is not relabelled as solved.

Operate it with [RESEARCH_ROOM_RUNBOOK.md](RESEARCH_ROOM_RUNBOOK.md). Runtime code and hashes are in `swingtradev3/research_room/`; sanitized review evidence is in [evidence/review-v1/manifest.json](evidence/review-v1/manifest.json). The [official App Server interface](https://learn.chatgpt.com/docs/app-server) supplies the thread/turn/dynamic-tool contract; actual compatibility was checked against the retained pinned binary, not inferred from newer documentation.

## Delivered application paths

| Area | Concrete change |
|---|---|
| Runtime reuse | Adapted the actual F `bridge.py` and `codex_working.py`, preserving text/function Responses translation, prefix handling, streamed IDs/sequence, call ownership and replay checks. Original source hashes, binary/model/skill pins and generated schema-bundle fingerprint are recorded in `research_room/provenance.json` and `local.example.json`. |
| Pinned serving | Optional owned-child llama.cpp supervisor, two distinct UUID-assigned GPUs, one slot per model, context 32,768/output 512, thinking disabled, measured default CPU embeddings retained. No vLLM/SGLang changes, downloads, driver changes or replacement of existing model services. |
| Room ownership | Separate host worker, two external top-level Codex threads, independent initial investigation and addressed-mail scheduling. No prescribed sentence, answer, rebuttal order or forced agreement. Explicit agreement must refer to an actually delivered peer position; objections and abstentions remain in history. |
| Durability | Existing Postgres cognition run/report tables hold room state, immutable messages, evidence/tool results, intent IDs, thread/turn/call IDs, leases and budget records. State plus replay/outbox record commit in the same transaction under a row lock. No new tables or migration of production data. |
| Publication | Compact four-field tool (`recipient`, `text`, `quote_id`, `position`). Quote IDs resolve to canonical exact excerpts and source metadata. The manager interrupts a turn only after its public message commits, records the actual terminal status, then uses the same thread for delivered mail. |
| Tools | Actual parameterized graph lookup and bounded neighbor retrieval, guarded research-file read/search, full pinned skill discovery/load and real isolated agent-browser DOM extraction of validated public HTML. No arbitrary Cypher, shell, broker/account credentials, execution tools or cloud fallback. |
| Operational behavior | Shared durable model/tool/deadline admission, per-model in-flight lock, repeated-action stop, explicit unknown usage, cancellation, stale-lease display and linked fresh attempts instead of ambiguous tool replay after a crash. |
| API | Authenticated room create/list/get/history/SSE/cancel/retry/health routes, registered in the existing API. Optional minimal host API avoids starting scheduler, broker loop or model warmup. |
| Dashboard | Research Desk in the existing React application: create/select/cancel/retry, actual public discussion, quoted excerpts, tool/evidence drawers, counters, model health, stale connection/lease state and cursor replay. Agent interpretation is visibly distinguished from verified excerpts. An optional server-only research proxy supports host deployment. |

The model still proposes all public text. The gateway does not manufacture a successful tool result or replace a model's conclusion. Narrowing the offered tools after four retrieval actions bounds a turn, and quote-ID enums reduce copying errors; these are capability/representation controls, not scripted research outcomes. Malformed tool arguments receive a persisted typed denial before any action so the agent can repair them. Unsupported tool namespaces and invalid protocol/replay input still fail closed.

## Graph isolation fixed before destructive tests

The audit's configuration bug is corrected: graph and Toolbox environment settings override explicit YAML values, including false/blank values. Local LLM, slow-brain, trading-mode and approval flags retain their prior semantics.

Test graph, test Postgres and app-test now share only an internal disposable network. The launcher independently inspects the Compose graph service container identity/IP, verifies the app and graph are on that same internal network, and injects `MEMGRAPH_TEST_EXPECTED_ADDRESS`. The fixture additionally requires the exact disposable URI, explicit expected database and acknowledgement, verifies the actual driver endpoint and session server against that independent address, and uses `session(database=...)` for every wipe. Production-like, loopback, mismatched, missing-ack and missing/incorrect independent-address targets are refused before a destructive query. No guard was bypassed.

The safety/unit checks and actual disposable endpoint probe ran before the first destructive disposable graph test. Final focused verification passed **84 tests**. The production graph was queried read-only: actual `RELIANCE` lookup and neighbor retrieval both returned `ok`. No production graph schema or deletion command ran.

The Makefile test wrapper no longer stops/restarts the trading worker. Final test containers for app/graph were removed after verification; the dedicated test Postgres was retained for preview history and backed up outside Git.

## Connected native room result

Run: `validation-20261101T063228` (local state under `~/.local/state/kepler-rooms/`). Successful room: `room:a874b9d5-c43a-445b-be0f-cd2934703b98`.

Question: which broker and live-entry policy the first room must retain, using actual Kepler implementation documents and the current graph. The current graph returned an honest empty result for the project target; it was not replaced by fixture evidence. Both models retrieved actual repository documents.

- **Five public messages**, with replies linked to delivered peer mail. Initial investigations ran concurrently on distinct local endpoints.
- **13 admitted model requests / 13 admitted tool actions**; actual reported input/output tokens **83,519 / 827**. Whole-context reservations **425,984**, zero unknown-usage calls in this room. Reservations are not actual consumption.
- The analyst initially confused the research runtime with the trading broker. The skeptic explicitly challenged that mistake and cited the Zerodha/manual-approval requirement. The analyst acknowledged the documented requirements and ultimately abstained from unsupported claims about other brokers/workflows.
- Final room status **disagreement** preserves the skeptic's objection and the analyst's abstention. It is not a consensus or financial answer-quality pass.
- Every displayed structured excerpt resolves to retrieved source text. Public interpretation can still be wrong; the UI says so. Newly added inline-ID checks also reject invented source/span IDs embedded in public text.
- The exported [public transcript](evidence/review-v1/integrated-room-public.json) contains actual public messages and actual terminal turn statuses. It contains no private reasoning transcript.

Earlier integration attempts are retained outside Git, including too-literal searches, overlong search results, invalid publication arguments, quote paraphrases, truncated calls and tool-schema errors. They are failures, not successful rooms. Fixes include short search excerpts, explicit truncation, source-bound quote IDs, compact publication arguments, typed gateway errors and turn termination after publication. No additional grounding benchmark was silently rerun after its ceiling.

## Actual tool and operational checks

| Check | Result and limit |
|---|---|
| Actual graph | Current production graph read-only lookup and neighbor retrieval: `ok`; project-target empty result preserved. Historical `as_of` is unsupported and extra arguments are denied. |
| Actual browser | Pinned agent-browser 0.41.0/Chrome read `https://www.sebi.gov.in/` through the public-fetch/networkless DOM path. Both native Codex models discovered/loaded the full pinned skill and executed browser reads during integration. Those browser-room attempts later failed publication and are not claimed as successful rooms. Only the tool executions passed. |
| Browser bounds | Exact public HTTPS host allowlist, public-only resolved IPs, validated/pinned redirects, no credentials/profiles, private namespace, bounded page/job and cleanup. External dynamic resources/navigation are unavailable in this first reader. |
| Active cancellation | Cancel requested with **two active model admissions**. Room reached `cancelled` in **6.56 s**; two unknown-usage calls recorded without fake measured usage. No broker operation or service stop occurred. |
| Crash/lease/duplicate behavior | Unit/real-Postgres checks cover expired leases, stale-owner refusal, idempotent events/tool results, changed/cross-role replay refusal, atomic claim/admission, cancellation fencing, immutable cursor replay and linked fresh attempts. No ambiguous intent is automatically executed again. |
| Dashboard | Actual browser selected the saved room, rendered both agents' discussion, reloaded and selected the same history successfully. SSE cursor replay/dedup also has API/client regression coverage. |
| Checks | `ruff check` changed Python files: pass. Focused pytest: **84 passed**. Dashboard `npm run lint`: pass; `npm test`: **16 passed**; build: pass to a separate local output directory. Existing large knowledge-graph bundle warning remains. |

No full application suite or trading integration suite was run. Trading/execution/risk/approval code was not changed. No production database migration was executed.

## Grounding audit and frozen comparison

G0/G1 exports preserve the original synthetic corpus, exact scorer/prompt/schema, original selected IDs/answers, expected-vs-actual errors and hashes. Original final profiles were 30 requests per model but **20 unique record IDs**, with repeated cache/role/changed-entity profiles. They were not 30 unique semantic tasks.

The original selected-record instruction was explicit. Its gold answers follow the declared cutoff, missing-evidence, contradiction and 30-day staleness policy; no gold/scorer defect was found that explains the failures. Normalizing citation order leaves **2/30** unchanged for both models. Status errors occurred in **27/30** per model; cross-record citations occurred in **1/30 Gemma** and **8/30 Qwen**. Same-entity events in unrelated records were often merged into a global conflict. The labels and historical result were not rewritten.

Fresh G2 predeclared 30 unique synthetic records per lane/arm, fixed 32,768/512/temperature-0 configuration, no retry allowance, and **120 requests total**. A kept the independent shared register; B retrieved only the selected record, retaining its contradictory source when present. The extraction evaluator and deterministic literal baseline were frozen before calls. The baseline solves this explicitly structured fixture; it is not a real-market reasoning benchmark.

| Model | A schema / exact | B schema / exact | B citation false positives |
|---|---|---|---|
| Gemma E4B | 30/30 / **5/30** | 30/30 / **4/30** | 5 |
| Qwen3.5-9B | 30/30 / **5/30** | 30/30 / **9/30** | 0 |

**The ≥27/30 scoped-accuracy gate failed for both.** The scoped JSON packet itself confused record ID with entity for many Gemma cases; temporal/conflict classification remained weak in both lanes. No improvement claim is made. This led to deterministic source metadata/quote-span resolution and fail-closed citation checks in integration, rather than trusting the models to classify facts or invent provenance. The synthetic evaluator rejects mismatched proposals; that does not prove arbitrary narrative text correct.

The unscripted room above is a connected application/interaction check, not a qualified research-accuracy evaluation. Future work should improve task representation and deterministic entity/time handling before asserting financial correctness. Do not add a new model/runtime matrix or reopen the Codex selection to explain these measured limits.

## Preservation and current operation

- All **11 pre-existing service containers** retained their identities and remain running, including trading app/worker, database, graph, broker MCP and unrelated Hush services. No production service was stopped or recreated.
- The two originally modified runtime files remain modified. The running system also changed `macro_cache.json`, `regime_cache.json` and `scan_status.json` during the work; those newer values remain in place. The original event-log prefix is preserved; production continues appending/updating runtime state. Initial and final copies were retained privately; newer state was not restored over with older snapshots. No stash/reset/clean/forced switch, commit or push occurred.
- Validation admission ledger: **155 bridge model admissions** across all room attempts, including failed/cancelled requests, plus **120** direct grounding requests = **275** total. Initial budgets and prospective amendments are retained in the run manifest (final ceiling 280; no extra model downloads). Resource floors and serving configuration were retained.
- Validation model services and research worker were stopped; owned model ports are free. Saved-room preview remains available at **http://127.0.0.1:18513 → Research Desk**, using a separate host research API and disposable Postgres history. Normal dashboard reads use the existing API; no trading controls were used. Model health correctly shows unavailable until research services are started.
- Preview history is also backed up to `validation-postgres.sql` in the private local run directory. It is not a production-room deployment. The already running Docker API was not restarted to load the new router. Use the runbook to activate the host path or the normal deployment workflow later.

## Remaining work

1. Improve entity/time/claim interpretation and test representative questions. Exact-source citations do not establish semantic correctness; the measured extraction gate remains failed.
2. First browser capability is bounded public HTML reading. More involved navigation, external scripts, feeds and authenticated sources need a separate capability implementation, not a broader shell grant.
3. Production deployment activation, sustained multi-room/long-context testing and operator workflow polish remain. Crash recovery starts a linked fresh attempt; verified App Server thread/process resume after a worker crash is not claimed.
4. Source freshness, complete contradiction retrieval, historical point-in-time graphs/news and representative financial accuracy are unproven. Bounded packets disclose omitted text. Empty/unavailable inputs remain visible.
5. TimesFM cache/input defects, forecast qualification, GIFT/STI/news ingestion, scheduling, additional specialists and Harness² are not changed by this slice. No forecast score/risk/stop/target influence was introduced.
