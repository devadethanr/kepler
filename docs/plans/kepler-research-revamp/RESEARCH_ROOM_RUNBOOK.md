# First research room: local operation

The follow-up fixes and measured remaining limitations are in [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md). Queued cancellation now commits one terminal event, latest objections receive a bounded response opportunity, and terminal views stop reconnecting. Worker interruption still offers a linked fresh attempt; it does not resume old live Codex threads. [ROOM_REVIEW.md](ROOM_REVIEW.md) records the earlier findings.

Implemented from `feat-generic-broker@beaa5df`. See [RESEARCH_ROOM_IMPLEMENTATION.md](RESEARCH_ROOM_IMPLEMENTATION.md) for measured checks and limits. This is an additional read-only research path. Zerodha, reconciliation, protective orders, risk controls and manual live-entry approval retain their existing authority.

## Active personal setup

The normal dashboard at **http://localhost:8502 → Research Desk** is now connected to the running native research services and the normal Kepler database. See [LOCAL_ACTIVATION.md](LOCAL_ACTIVATION.md) for actual UI/cancellation/restart tests. From `swingtradev3/`, use `make research-start`, `make research-status` and `make research-stop`; the retained host virtual environment is selected automatically. The worker starts in a managed scope from the working IDE terminal, preserving sandbox support without changing host security policy. Models/API use user services. This is the default installed path; the separate-terminal commands below remain available for development.

The Docker API relays `/research` over the owner-only shared Unix socket configured by `KEPLER_RESEARCH_SOCKET`. It has already been recreated to activate that path; no broker worker restart was needed. The earlier isolated preview was retired.

The research units are transient: a PC reboot stops them while the normal Docker
stack can restart automatically. From the supported IDE terminal, run `make
research-start` in `swingtradev3/` to recreate the model/API units and managed worker
scope, then `make research-status`. This retains the installed models/configuration;
it does not rebuild Docker or alter broker controls. Reboot recovery and actual
browser/API/worker checks are recorded in [REBOOT_BROWSER_CHECKS.md](REBOOT_BROWSER_CHECKS.md).

## Processes and configuration

The existing API now registers `/research`. Inference belongs to a separate **host** worker, not the broker process. The optional host research API imports only the research routes, existing API-key authentication and existing Postgres storage; it does not start trading, the scheduler or model warmup. Room state still uses `cognition_runs` with phase `research_room_v1`, and immutable messages/evidence/tool events use `cognition_reports` with schema `room.event.v1`. The subsequent [fresh-source slice](FRESH_SOURCE_FINDINGS.md) adds three source-history tables via explicit additive migration `20261102_0008`, applied locally only after a database backup and disposable validation. Source reads do not migrate at startup.

1. Use Python 3.12. Install `swingtradev3/research_room/requirements-host.lock` in an isolated virtual environment, or use the retained local environment at `~/.local/state/kepler-rooms/venv`. These dependencies do not replace the application or model environments.
2. Copy `swingtradev3/research_room/local.example.json` to a new private local configuration file. Point `KEPLER_RESEARCH_CONFIG` at that copy. Check the explicit binary/model/skill paths against this PC. Keep weights, Codex homes and browser profiles outside Git. The example contains measured runtime paths and hashes, not credentials.
3. Set a **host-reachable** `DATABASE_URL` for the existing Kepler Postgres instance. The default Docker hostname `db` is not a host endpoint. Use the existing local database credentials privately; do not paste them into commands saved in Git or reports. Normal application migration/bootstrap remains the existing mechanism. Validation used an exclusively disposable database, never a production schema upgrade.
4. Set `MEMGRAPH_URI` to the actual read-only reachable graph endpoint for this deployment. Graph credentials remain in the environment. Environment values now override graph/Toolbox YAML defaults, including explicit blank credentials. Inspect effective target names without printing passwords. The host normally reaches the published graph port; Docker uses the service hostname.
5. Keep the existing `FASTAPI_API_KEY` authentication policy. The host research API and dashboard proxy must use matching keys. API keys never enter browser JavaScript, model processes, tools or Codex homes.

From `swingtradev3/`, in separate terminals with that configuration/environment:

```bash
make research-models RESEARCH_PYTHON=/path/to/research-venv/bin/python
make research-worker RESEARCH_PYTHON=/path/to/research-venv/bin/python
make research-api RESEARCH_PYTHON=/path/to/research-venv/bin/python
```

The supervisor verifies binary/GGUF hashes, refuses occupied ports and starts only its own children. It preserves the measured llama.cpp build 9067, Gemma E4B on the 3060 and Qwen3.5-9B on the 5070 Ti, single-slot 32,768 contexts, 512 generated-token ceiling, reasoning disabled, and default CPU embedding placement. It stops its own children on exit or resource-floor failure (available RAM 1,536 MiB; each assigned GPU 1,024 MiB free). This deliberately preserves the measured default placement; it is not the slower strict all-GPU variant. No driver changes or model downloads occur.

For a native dashboard using the existing React source, configure server-side `FASTAPI_URL` for the normal API and optional `RESEARCH_API_URL=http://127.0.0.1:18012` for the host research API. Then run the normal dashboard command from `swingtradev3-dashboard/`. Both proxies default to the same server-side key; an optional server-only `RESEARCH_API_KEY` supports an independently authenticated host research API. An already running Docker API needs its normal code activation/restart to register new routes; this was performed for the current personal setup, as recorded in LOCAL_ACTIVATION.md. Host binaries, `127.0.0.1` endpoints and the private config are not automatically available inside Docker. Do not point a Docker container at its own loopback and assume that reaches the host worker.

## Research Desk

Open **Research Desk**, enter a target and question, then start a room. Two top-level Codex threads use the two pinned model profiles. They independently retrieve evidence, then receive durably stored mail addressed to them. Further speaking follows the addressed mailbox. There is no prescribed answer, fixed rebuttal round or forced agreement.

Each new `room_message` call has seven compact fields: `recipient`, `text`, `quote_id`, `position`, `claim_kind`, `support_assessment`, `event_id`. Legacy four-field calls remain inference/unassessed. Support assessments are model proposals; deterministic metadata and excerpt validation do not establish narrative truth. Position selects question, challenge, conclude, agree, disagree, abstain or revise. Quote IDs resolve to exact spans in retrieved evidence; the manager supplies canonical source metadata and links replies to mail actually delivered to the thread. This compact contract avoids copying long source text/JSON metadata into a 512-token tool call. A factual conclusion/revision needs a retrieved quote; agreeing needs an actual delivered peer message. Interpretations remain explicitly unverified.

The manager ends a Codex turn after the publication commits. The durable `turn.finished` event retains the real `interrupted` status and `public message committed` reason. It then resumes the same top-level thread for further mail. This prevents redundant generation after publication. An interrupted publication turn is not recorded as a completed model response.

Default room ceilings: 24 model requests, 24 admitted tool actions, 20 minutes, 12 public messages. At most two inferences (one per model) and one tool action run concurrently. A single host worker locks the two endpoint identities and processes rooms serially. Repeated identical actions stop without inventing progress. Four retrieval actions per turn narrow the next model tools to publication; a committed message ends that unit of work.

Counters separate actual reported input/output usage from cumulative whole-context reservations. Each admitted model request permanently reserves 32,768 tokens from `model_call_limit × 32,768`; failures/cancellation are not refunded. Missing usage is an explicit unknown-usage call, not a measured zero. No automatic cloud fallback exists.

History and SSE share one committed sequence. Reconnect uses `Last-Event-ID`; UI merges by immutable event ID. Reloading a saved room shows the same public messages and tool/evidence events. Open an older saved room by its room ID when it falls outside the newest-30 list. The screen shows model health, lease staleness, typed termination reasons, unknown activity, actual versus reserved usage and cancel state. It does not show private model reasoning or invented agent speech.

Cancel affects research only. A worker crash leaves an expired lease, shown as stale; the next worker marks the room interrupted without replaying ambiguous tool intents. **Retry as new room** creates a linked attempt with fresh counters, retaining the old room and unknown actions. It does not pretend to resume an unverified Codex process.

## Tool boundaries

- Saved news: `news_search` / `news_read` read observed immutable versions with a room cutoff, explicit source/window/topic bounds, exact title/snippet spans, identity basis and date precision. Undated items are separate from dated matches. Reads do not ingest or write graph/account state. Company-disclosure coverage is unavailable; current regulatory/government feed windows are not comprehensive. A valid empty result is not proof of no announcement. See [fresh-source findings](FRESH_SOURCE_FINDINGS.md) for terms and source limits.
- Graph: parameterized stock lookup against the actual graph, plus one bounded neighbor hop from a retrieved node. No arbitrary Cypher, schema writes, trading/account mutations or historical `as_of` capability. Empty, unavailable and rejected traversal are explicit states. The current graph projection does not prove point-in-time completeness.
- Files/search: an explicitly approved research root, bounded keyword search excerpts and target-relevant paragraphs with adjacent qualifications. The configured workspace target can search that approved workspace corpus. Files are opened through directory descriptors without symlink traversal; hidden paths, escapes, hard links and oversized/nonregular files are refused. Packets disclose scope, offsets, omissions and truncation. `artifact_read_more` and `artifact_search_more` provide bounded continuation (6,000 characters per read, 2,000 scan entries per search, six search results, 10,000 total tree entries). Search offsets refer to a live tree and may shift. Retrieval is bounded, not exhaustive.
- Browser: discover and load the complete pinned official skill before execution. The gateway fetches only exact allowlisted public HTTPS hosts, checks all resolved IPs and redirects, pins the validated address with TLS/SNI, and sends captured HTML to actual pinned agent-browser/Chrome in a private networkless namespace. Chrome reads that page through its own loopback and closes. There are no credentials, cookies, personal profiles, external subresources or arbitrary shell. This supports bounded page reading, not full navigation with externally loaded JavaScript. Browser jobs share one 100-second deadline from before fetch through DNS/redirect/read/DOM. Owned fetch processes are terminated/joined on cancellation or deadline. Browser continuation refetches the capped 12,000-character DOM body, so offsets may shift; this is not exhaustive page retrieval.
- Citation validation: unknown/cross-target IDs, invented inline IDs, wrong quote provenance and future-known timestamps are rejected. Exact verified excerpts are distinguished from agent interpretation. Source freshness stays unknown when not established. This is not a semantic truth verifier.

Read-only market snapshots and the availability recorder are now delivered; GIFT/STI quote feeds remain unqualified. The required visual workspace comes next. TimesFM, scheduler-triggered rooms, additional specialists, further company-disclosure coverage and Harness² follow later. Forecasts gain no score, position, stop or target influence.

## Controlled primary-source refresh

The current local schema is already upgraded and the host parser dependencies are
pinned in `research_room/requirements-host.lock`. For another installation, first
back up its existing database and explicitly apply the additive migration; do not
reset or backfill legacy history. Run source refresh from `swingtradev3/`:

```bash
make research-ingest ARGS='--run-id manual-primary-refresh --sources sebi_rss rbi_press_releases_rss pib_rss'
```

Use a distinct audit run ID for a new batch. The wrapper uses the already prepared
host database configuration without shell-sourcing JSON, exposing credentials,
starting models, changing broker controls or migrating the schema. Refresh checks
are serialized across processes and refuse another check within 60 seconds. This
is an explicit ingestion owner; model tools remain saved-data reads. Feed failures,
empty/partial content, conditional 304, stale fetch and unknown coverage are distinct.

One approved PIB release can be ingested with `--pib-release URL` plus
`--first-party-reviewed` after reviewing its terms and third-party exclusions.
The flag records that review; it is not automatic copyright detection. Only exact
PIB release hosts/paths and numeric release IDs are allowed; no broad crawl or
challenge bypass is available. SEBI/RBI feed intake is metadata/link-only. Source
fetch freshness defaults to 24 hours (`source_stale_after_seconds` in the host
research settings); recent checking does not establish publication freshness.

The completed model evaluation has a fixed, durably registered plan under run
`fresh-source-20261101T195640Z`. `research_room.source_eval` rejects a replacement
plan for that ID; reboot/cancellation do not renew its allocation. Do not reuse its
now-seen cases as untouched validation. Its actual counters remain 93 model and
88 tool admissions after recovery. See the findings for failed-room history and
the subsequent zero-admission protocol correction.

## Graph-test safety

`app-test`, `memgraph-test` and `db-test` now share an internal disposable network, with no application/production network or published ports. The graph fixture requires exact `MEMGRAPH_TEST_TARGET`, `MEMGRAPH_TEST_DATABASE` and `MEMGRAPH_TEST_ACK=kepler-disposable-only`. The launcher independently inspects the Compose service container IP and confirms that app/test graph share the same internal network; it injects `MEMGRAPH_TEST_EXPECTED_ADDRESS` for the fixture. The guard checks that address against DNS and the connected driver endpoint, then checks the session server again before deletion in the explicitly named database. A hostname containing “test” alone is insufficient. Unsafe configuration fails before schema/deletion.

`make test-file` / `make test-memgraph` no longer stop the broker worker. They use and clean only disposable test services. Use focused checks first. Do not run graph fixtures directly against the operator graph, change the guard to bypass it, or reuse a production endpoint as the expected target.

If a transient research API unit was explicitly stopped, `--collect` can remove it. Use `make research-start` to recreate the owned unit; `systemctl start` cannot recreate a collected unit. An active API can still be restarted independently with `systemctl --user restart kepler-research-api.service`.

## Read-only market context

The current local schema includes additive migration `20261103_0009` and the
separate `market_context_observations` table. New installations must back up their
database, validate the additive migration in the disposable stack and explicitly
upgrade; no reset/backfill is needed. See [market findings](MARKET_CONTEXT_FINDINGS.md)
for the actual local migration order, qualification gaps and measured tests.

From `swingtradev3/`:

```bash
make research-start
make research-market-refresh
```

Refresh currently saves **unavailable availability/specification records**, makes
zero provider HTTP calls and never logs in, subscribes, fetches a quote, starts a
room or places an order. It reads the existing private host DB configuration,
serializes collection and refuses another collection within 60 seconds. No
migration is invoked by the recorder. A successful refresh is not a successful
market feed. The recorded source/contract/calendar/delay gaps stay explicit.

The authenticated `/research/market-context` endpoint accepts `scope` (`all`,
`gift_nifty`, `singapore_sti`, `nifty_cash`), an optional aware `cutoff`, and optional
`room_id` to respect its pinned cutoff. The dashboard uses `/api/research` through
the existing proxy/Unix socket. Model `market_context` reads are budgeted and
saved-data only, with at most three observations; missing history is unavailable,
not a current quote backdated into an old room. UI separates quote quality from
calendar state and observation-time state from cutoff-time state.

For actual GIFT/Nifty quote qualification, use the normal user Kite login workflow
without sharing secret values, then check master identity, quote, history and
owned socket capability separately. The observed `EQ/INDICES` GIFT row with blank
expiry does not establish a futures contract. STI needs a permitted licensed source;
an ETF/futures proxy must be labeled explicitly. Never assume webpage receipt or
provider refresh frequency is exchange quote time/delay.

`_gift_nifty_check` now invokes an owned availability-only subprocess with a
five-second deadline. No broker worker was restarted to load this change. When
that process is normally restarted, it will load the hook; it still has no quote
provider, model scheduling or trade authority. Before enabling a future provider,
qualify contract/session/reference/rights and reuse its shared broker rate limit.

The market validation plan is registered once in cognition storage under
`market-context-20261102T175740Z`, separately capped at 60 model and 60 tool
admissions. Its completed counters are **41 / 39**. Do not change its allocation,
reuse cancelled identities or reopen the old source run. Future work needs its own
declared scope and budget; the required visual workspace can reuse saved history
without fresh inference.
