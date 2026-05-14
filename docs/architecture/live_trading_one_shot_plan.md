# Live Trading One-Shot Plan

> Last Updated: May 10, 2026
> This is the active end-to-end implementation plan for turning `swingtradev3` into a broker-truth-driven, bounded-autonomy live trading system.
> It merges the execution hardening work from `findings.md` with the Slow Brain / Fast Brain architecture in `agent_cognition_architecture.md` and `agent_cognition_implementation_plan.md`.
> Phases 0-9 build the execution-safe floor. Phases 10-13 add the cognition, policy, and memory layers required for the final non-linear autonomous system.

## Goal

Build a version of `swingtradev3` that can safely support:

- unattended same-day live execution after a supervised morning bootstrap
- autonomous intraday monitoring and trailing
- reliable stop/target handling with broker-confirmed state
- restart-safe, auditable real-money operation

And, after the execution floor is stable, extend it into the full target architecture:

- **Slow Brain**: overnight and pre-market multi-agent deliberation
- **Fast Brain**: market-hours deterministic execution and risk control
- **Memory**: Memgraph context graph plus Postgres execution and trade history
- **Policy Layer**: bounded dynamic overlays, not raw `config.yaml` mutation
- **Execution Core**: broker-truth single-writer worker
- **Recovery Layer**: reconciliation, kill switches, and operator controls

## Reality Check

Some constraints are external, not code bugs:

- As of April 16, 2026, standard Kite `access_token`s expire at **6 AM the next day**.
- Fully unattended multi-day equity exits require **DDPI/POA** or equivalent broker-side holdings authorization support.
- For individual developers, Zerodha recommends **WebSocket order updates** over relying only on postbacks.
- Kite GTT OCO uses **one trigger id**, not separate stop/target ids.

That means the real target is:

1. same-day unattended live automation after daily login and preflight
2. zero-touch multi-day holdings management only if DDPI/POA is available

## Non-Negotiable Design Decisions

1. Broker truth beats local state.
2. One process owns all live writes and broker mutations.
3. `placed` never means `filled`.
4. Protective orders are armed only after a confirmed entry fill.
5. LLMs stay out of the execution hot path.
6. API and dashboard read projections; they do not mutate execution state directly.
7. JSON files become compatibility projections, not the source of truth.

## Target Runtime

```text
 Slow Brain Desk / Telegram / UI
              |
              v
       FastAPI control plane
              |
              v
   intents / approvals / controls
              |
              v
       execution-worker (single writer)
      /        |         |          \
     /         |         |           \
Kite REST   Kite WS   Reconciler   GTT watchdog
     \         |         |           /
      \        |         |          /
               v
            Postgres
          /     |      \
         /      |       \
        v       v        v
   projections audit   read-only
               log     Toolbox views
                |
      dashboard / SSE / reports
```

## Service Split

### Keep

- `app`: FastAPI routes, read APIs, control endpoints, SSE
- `dashboard`: Reflex UI
- `kite-mcp`: optional sidecar for diagnostics and fallback tooling

### Add

- `worker`: the only service allowed to submit orders, modify GTTs, close positions, or write execution state
- `db`: Postgres for transactional execution state
- `toolbox`: Google MCP Toolbox for read-only agent access to curated Postgres views

## Why Postgres, Not JSON

For the final target, go straight to Postgres.

- `state.json`, `trades.json`, and `pending_approvals.json` are not transactional.
- the system needs unique constraints, recovery queries, append-only audit events, and concurrent read/write safety
- API + worker + optional postback ingress will share the same state

Use SQLAlchemy + Alembic. Keep the repository layer DB-agnostic, but do not ship the final live system on file-backed JSON.

## Target Data Model

Create these tables first:

- `entry_intents`
- `approvals`
- `order_intents`
- `broker_orders`
- `broker_fills`
- `protective_triggers`
- `positions`
- `trades`
- `execution_events`
- `policy_overlays`
- `reconciliation_runs`
- `auth_sessions`
- `operator_controls`
- `failure_incidents`
- `universes`
- `universe_memberships`
- `universe_runs`

### Core IDs

Persist all of these:

- `intent_id`
- `approval_id`
- `order_intent_id`
- `broker_order_id`
- `exchange_order_id`
- `broker_tag`
- `oco_gtt_id`
- `position_id`
- `trade_id`

### State Machines

Use explicit state machines, not booleans.

`order_intents`

- `proposed`
- `awaiting_approval`
- `approved`
- `queued`
- `submitting`
- `submitted`
- `entry_open`
- `entry_partially_filled`
- `entry_filled`
- `protection_pending`
- `protected`
- `failed`
- `cancelled`
- `expired`

`positions`

- `pending_entry`
- `open`
- `closing`
- `closed`
- `reconcile_required`
- `operator_intervention`

`protective_triggers`

- `pending_arm`
- `armed`
- `triggered`
- `exit_order_open`
- `exit_filled`
- `rejected`
- `cancelled`
- `expired`
- `disabled`
- `recreate_required`

### Multi-Universe Rule

Support multiple research universes, but one unified book.

- research can run across several universes in parallel
- `entry_intents` must carry `source_universe_id`
- duplicate symbols across universes must merge into one canonical instrument before allocation
- one global portfolio allocator and one execution worker own the final decision and execution path

### Removal Rule

When a phase replaces a module, route, or runtime path, remove the superseded code in that same phase.

- do not keep deprecated classes, routes, or worker paths as compatibility shims unless an external dependency still requires them
- remove or rewrite stale tests in the same change
- the repo should have one authoritative execution path at a time

## Phase Plan

### Phase 0 [X]: Preconditions And Freeze

Before writing new live features:

- add `LIVE_TRADING_ENABLED=false` and `NEW_ENTRIES_ENABLED=false` defaults
- require paid Kite Connect data access
- confirm whether the account has **DDPI/POA**
- document the daily operator bootstrap: login, auth check, broker funds check, positions sync, websocket connect
- freeze new strategy/autonomy work until the execution core is rebuilt

Immediate cleanup items:

- fix the `quantity` signature mismatch between `order_agent.py` and `order_execution.py`
- remove the duplicate `retry_failed_event` definition in `event_bus.py`
- stop treating placed live orders as filled

Phase 0 completion means guardrails, preflight, WebSocket readiness, and local-state reconciliation are in place. It does not mean multi-day unattended holdings management is enabled; that remains blocked until broker-side holdings authorization moves out of `demat_consent=consent`.

### Phase 1 [X]: Create The Execution Core

New modules:

- `swingtradev3/memory/db.py`
- `swingtradev3/memory/models.py`
- `swingtradev3/memory/repositories.py`
- `swingtradev3/memory/projections.py`
- `swingtradev3/memory/migrations/`

Existing modules to refactor:

- `storage.py`
- `models.py`
- `api/routes/approvals.py`
- `api/routes/trades.py`
- `api/routes/positions.py`

Implementation:

- add Alembic migrations
- import `context/state.json`, `trades.json`, `pending_approvals.json`, and `context/auth/kite_session.json`
- build the DB-backed compatibility bridge under `storage.py`
- keep writing JSON compatibility projections for the dashboard during migration
- model `state.json` and `trades.json` as derived outputs from DB state, not primary data

Definition of done:

- Postgres becomes the source of truth for positions, trades, approvals, and execution events
- JSON files are regenerated from projections
- the app can boot and serve current routes entirely from Postgres-backed projections

### Phase 2 [X]: Separate The Worker

Move live execution out of FastAPI lifespan.

Add:

- `swingtradev3/execution/worker.py`
- `swingtradev3/execution/bootstrap.py`
- `swingtradev3/execution/operator_controls.py`

Refactor:

- `api/main.py`
- `api/tasks/scheduler.py`
- `docker-compose.dev.yml`
- `swingtradev3/Makefile`

Implementation:

- `app` becomes the control plane and read API
- `worker` owns scheduler jobs, broker sessions, reconciliation, and protective logic
- no live scheduler jobs run in FastAPI startup anymore
- only the worker is allowed to write `positions`, `trades`, `broker_orders`, and `protective_triggers`

Definition of done:

- running multiple API instances does not duplicate live jobs
- one worker process owns all broker mutations

### Phase 3 [X]: Rebuild Broker Integration Around Truth

New modules:

- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/broker/kite_stream.py`
- `swingtradev3/broker/postbacks.py`
- `swingtradev3/broker/reducer.py`

Refactor:

- `auth/kite/client.py`
- `tools/execution/order_execution.py`
- `tools/execution/gtt_manager.py`
- `auth/token_manager.py`

Implementation:

- add REST wrappers for orders, order history, positions, holdings, margins, and GTT detail
- add `KiteTicker` WebSocket handling for order updates and quotes
- add optional verified postback ingestion as a secondary feed
- all inbound broker updates go through one reducer that deduplicates and applies state transitions
- store `tag` on every order intent and broker order
- use margin endpoints before entry submission

Important rule:

- WebSocket is primary for live order updates
- periodic snapshot polling is secondary reconciliation
- postbacks are optional redundancy, not the only truth path

Definition of done:

- the system can restart, reconnect, and reconstruct open orders and positions from broker data

### Phase 4 [X]: Rebuild Entry Execution

Refactor:

- `api/routes/approvals.py`
- remove `agents/execution/order_agent.py`
- `tools/execution/order_execution.py`
- `api/tasks/morning_briefing.py`

Implementation:

- stop executing by ticker; execute by `order_intent_id`
- stop scanning the whole approval file on every execution cycle
- persist one `order_intent` per candidate
- approval actions are addressed by `approval_id`, not ticker
- approval only changes state; it does not directly perform broker actions
- the worker consumes approved intents, submits broker orders, and waits for broker-confirmed fills
- only after `entry_filled` does the worker create the position and request protection
- remove the legacy ADK order execution path; do not keep it as a fallback

Optional operating mode:

- keep manual approvals as a gate
- add `AUTO_APPROVE_ENTRIES=true` for unattended operation

Definition of done:

- no route directly places orders
- every entry has a durable audit trail from proposal to fill

### Phase 5 [X]: Rebuild Protection And Exit Logic

Refactor:

- `models.py`
- `tools/execution/gtt_manager.py`
- `agents/execution/monitor.py`
- `api/tasks/event_handlers.py`

Implementation:

- replace `stop_gtt_id` + `target_gtt_id` with one `oco_gtt_id`
- map all official GTT statuses: `active`, `triggered`, `disabled`, `expired`, `cancelled`, `rejected`, `deleted`
- persist which GTT leg fired and the resulting broker order ids
- treat GTT trigger as advisory until exit order fill is confirmed
- create a `gtt_watchdog` loop that:
  - detects missing protection
  - recreates invalid or cancelled protection
  - marks `operator_intervention` when recovery fails

Trailing rules:

- drive trailing off live quote truth, not stale `current_price`
- enforce hysteresis and minimum step sizes
- throttle updates aggressively because Kite caps modifications per order
- log every protection modification as an execution event

Definition of done:

- stop/target handling is broker-correct and restart-safe

### Phase 6 [X]: Reconciliation And Recovery

New modules:

- `swingtradev3/execution/reconciler.py`
- `swingtradev3/execution/quote_cache.py`

Implementation:

- startup reconciliation before enabling trading:
  - auth valid
  - websocket connected
  - positions synced
  - open orders synced
  - GTTs synced
  - unresolved incidents reviewed
- runtime reconciliation loops:
  - order snapshot reconciliation every 10-15 seconds
  - positions/holdings reconciliation every 60 seconds
  - GTT reconciliation every 60 seconds
  - quote freshness checks continuously
- write one `reconciliation_runs` record per loop
- if drift is detected, mark affected positions `reconcile_required` and block new entries until resolved

Definition of done:

- restart during market hours does not duplicate orders or lose live positions

### Phase 7 [X]: Safety, Auth, And Operator Controls

Implementation:

- add `operator_controls` flags:
  - `trading_enabled`
  - `new_entries_enabled`
  - `exit_only_mode`
  - `flatten_requested`
  - `kill_switch_reason`
- add automatic kill switches for:
  - broker disconnect
  - stale auth
  - repeated order submission failures
  - repeated GTT recovery failures
  - stale quotes
  - daily loss threshold
  - reconciliation drift
- add actual manual flatten / close APIs
- add auth preflight before market open and before first order submission

Critical broker constraint:

- if DDPI/POA is not present, the system must not advertise fully unattended multi-day holdings exits

Definition of done:

- the system fails closed instead of failing dangerously

 ## Phase 8 React Dashboard

  ## Summary

  - Phase 8 will replace the old Reflex dashboard with the root-level React/Vite app at swingtradev3-dashboard.
  - Remove swingtradev3/dashboard and swingtradev3/dashboard_old after the React dashboard boots through Compose.
  - Phase 8 remains dashboard/API/SSE/projection work. The knowledge graph screen stays as an explicit mock until Phase 11.
  - Phase 11 owns the real Postgres + Memgraph context graph/memory phase.

  - Replace Dockerfile.dashboard with a Node/Vite runtime and update docker-compose.dev.yml to mount/build ./swingtradev3-dashboard, not ./swingtradev3/dashboard.
  - Use Vite dev proxy /api -> http://app:8000 so the browser calls same-origin /api/...; inject X-API-Key from dashboard container env in the proxy instead of hardcoding API keys into React.
  - Add frontend data layer packages: @tanstack/react-query for request/mutation cache, zod for response validation, and @microsoft/fetch-event-source for SSE because native EventSource does not support custom request headers.
  - Remove unused AI Studio/server packages from the dashboard app: @google/genai, dotenv, express, @types/express; keep react-force-graph-3d, three, recharts, motion, and lucide-react.
  - Add src/lib/api.ts, src/lib/sse.ts, src/lib/schemas.ts, and feature hooks so screens do not call fetch directly.
  - Keep KnowledgeScreen as a deterministic local mock with an explicit pending-graph badge; remove markdown/file language like “View Markdown Base” and do not read context/knowledge in Phase 8.
  - Refactor existing FastAPI routes so dashboard reads Postgres-backed state, not state.json, trades.json, pending_approvals.json, _graph.json, or _index.json.
  - Make /sse/live durable by tailing execution_events with a cursor/heartbeat model instead of depending only on the in-memory broadcaster.
  - Fix API auth fail-closed behavior: if API auth is enabled and no key is configured, return 403, do not allow access.

  ## Required API Surface

  | UI Area | Routes |
  |---|---|
  | Top bar / shell | GET /health, GET /ops/safety, GET /dashboard/snapshot |
  | Dashboard overview | GET /dashboard/snapshot, GET /dashboard/events?limit=..., GET /sse/live |
  | Orders / approvals | GET /approvals, POST /approvals/{id}/yes, POST /approvals/{id}/no |
  | Execution | GET /dashboard/execution, GET /ops/reconciliation, GET /dashboard/events |
  | Positions | GET /positions, POST /ops/positions/{ticker}/close |
  | Trades / portfolio | GET /trades, GET /portfolio/summary |
  | Incidents | GET /ops/safety, GET /ops/reconciliation, POST /ops/block/clear |
  | Control pane | GET /ops/safety, POST /ops/mode, POST /ops/flatten, DELETE /ops/flatten, POST /scan, GET /scan/status |
  | Tickers / quotes | GET /dashboard/quotes |
  | Brokers | GET /dashboard/broker, GET /ops/safety |
  | Telemetry | GET /dashboard/telemetry, GET /dashboard/events, GET /sse/live |
  | Knowledge graph | local mock only in Phase 8; real API belongs to Phase 11 |


Definition of done:

- the dashboard reflects broker-confirmed state, not stale local assumptions

### Phase 9 [X]: Tests And Staged Enablement

New test areas:

- `tests/test_execution/test_state_machine.py`
- `tests/test_execution/test_broker_reducer.py`
- `tests/test_execution/test_gtt_watchdog.py`
- `tests/test_execution/test_reconciliation.py`
- `tests/test_execution/test_operator_controls.py`
- `tests/test_integration/test_entry_to_exit_lifecycle.py`
- `tests/test_integration/test_restart_recovery.py`

Must-cover scenarios:

- duplicate approval click
- retry after HTTP timeout
- submitted but unfilled entry
- partial fill
- fill confirmed after reconnect
- GTT rejected
- GTT disabled after corporate action
- stop trigger -> exit order open -> exit fill
- target trigger -> exit order rejected -> recovery path
- restart after entry fill but before GTT arm
- restart after GTT trigger but before exit fill is persisted
- stale auth before market open
- broker disconnect during open position
- manual broker-side close

Enablement ladder:

1. unit + integration tests green in Docker
2. paper-mode soak for 10 trading days
3. live-mode with manual entries and automated reconciliation only
4. live-mode with automated entries and supervised exits
5. same-day unattended live mode
6. multi-day unattended mode only after DDPI/POA confirmation and stable daily login operations

Completion evidence as of May 4, 2026:

- `make test` runs in Docker with worker isolation and restores the worker after pytest.
- Backend deterministic gate: 281 passed, 3 skipped, 41 warnings.
- Dashboard API/SSE client gate: 8 passed through the dashboard Docker service.
- Live market/news/LLM evaluation is opt-in via `RUN_LIVE_EVAL=true` and is not part of the deterministic Docker gate.
- The 10-trading-day paper soak and staged live modes remain operational rollout controls that require operator evidence before advancing runtime flags.

### Phase 10 [X]: Policy Layer And Effective Policy

Implementation:

- keep `config.yaml` as the slow-changing base config
- add `policy_overlays` with hard bounds, reason, proposer, expiry, rollback handle, and optional approver
- build `effective_policy` from:
  - base config
  - operator controls
  - active bounded overlays
- allow dynamic changes only through approved overlay keys such as:
  - `min_score_threshold`
  - `max_position_size_pct`
  - `new_entries_enabled`
  - `max_same_sector_positions`
  - `trail_stop_at_pct`
  - `trail_to_pct`
- `debate_top_n`

Definition of done:

- no runtime path mutates `config.yaml`
- adaptive behavior is bounded, auditable, and reversible

Implemented:

- `swingtradev3/policy/` now owns bounded overlay validation, lifecycle transitions, and
  effective-policy resolution.
- `policy_overlays` is used as the durable audit table; overlays carry reason, proposer,
  approver, expiry, rollback handle, and transition history in Postgres.
- `GET /policy/effective`, `GET/POST /policy/overlays`, approve/reject/rollback endpoints, and
  `GET /dashboard/policy` expose the runtime policy and audit trail.
- Runtime entry approval/execution, risk sizing, sector concentration, research score thresholds,
  and trailing thresholds read the effective policy instead of only raw config.
- The dashboard Risk panel shows effective policy values and active overlays.

### Phase 11: Context Graph Memory

> Full design specification: [docs/features/postgress-memgraph.md](../features/postgress-memgraph.md)

#### Core Principle

```
Postgres = execution truth     (protects money)
Memgraph = context graph truth (improves memory and reasoning)
Files    = temporary caches + compatibility exports only
```

If Memgraph is down, trading safety must still work. The only acceptable degradation is:
`"less historical/research context available"` — never `"cannot reconcile"` or `"cannot place/flatten"`.

#### What Postgres Continues To Own

All execution-critical state stays in Postgres:

- `entry_intents`, `approvals`, `order_intents`, `broker_orders`, `broker_fills`
- `positions`, `protective_triggers`, `trades`
- `operator_controls`, `failure_incidents`, `reconciliation_runs`
- `auth_sessions`, `policy_overlays`

#### What Memgraph Owns

Context and cognition state, with no write path back to execution:

- `Stock`, `Sector`, `Index`
- `ResearchRun`, `ResearchCandidate`
- `NewsArticle`, `SignalSnapshot`, `TechnicalSnapshot`, `FundamentalSnapshot`, `SentimentSnapshot`
- `RegimeSnapshot`
- `TradeMemory`
- `Observation`, `Lesson`, `FailurePattern`
- `SkillVersion`
- Edges: `MEMBER_OF`, `BELONGS_TO_SECTOR`, `ANALYZED_IN`, `HAS_SIGNAL`, `MENTIONS`, `AFFECTS_STOCK`, `UNDER_REGIME`, `GENERATED_INTENT`, `EXECUTED_AS`, `CLOSED_AS`, `PRODUCED_OBSERVATION`, `SUPPORTS_LESSON`, `SIMILAR_TO`, `FAILED_DURING`
- Every node/edge carries: `source`, `source_id`, `postgres_table/postgres_pk`, `observed_at`, `ingested_at`, `payload_hash`, `confidence`, `projection_version`

#### New Modules

- `swingtradev3/context_graph/repository.py` — `ContextGraphRepository`: typed Memgraph access layer; no raw Cypher scattered across agents
- `swingtradev3/context_graph/projector.py` — `GraphProjector`: reads Postgres `execution_events` and writes derived memory nodes/edges to Memgraph
- `swingtradev3/context_graph/context_builder.py` — `ContextBuilder`: reads Memgraph for agent prompts and research context
- `swingtradev3/context_graph/intent_writer.py` — `IntentWriter`: converts approved research output from Memgraph into Postgres `entry_intents`
- `swingtradev3/context_graph/policy_proposal_writer.py` — `PolicyProposalWriter`: converts graph/learning insights into Postgres `policy_overlay` candidates; never mutates config directly

#### Infrastructure

- Add `memgraph` behind the optional Docker Compose `memory` profile, using the official `memgraph/memgraph-mage:latest` image
- Add `memgraph-lab` behind the same profile, using the official `memgraph/lab:latest` image for graph debugging (dev only)
- `make dev` and `make dev-detach` start the `memory` profile alongside the normal dev stack; app and worker must not depend on Memgraph to boot
- Persist Memgraph data and logs in Docker volumes, cap the dev memory budget with `MEMGRAPH_MEMORY_LIMIT_MIB`, and keep snapshots/WAL enabled
- Use Python `neo4j` driver over Bolt protocol for all Memgraph access
- Add backup/restore runbook

#### Connection Flow

```
Research / agents / market data
        |
        v
Postgres execution truth          Memgraph context truth
        |                                 ^
        |                                 |
        +-------- GraphProjector ---------+
                  (one-way, async)
```

Allowed directionality:

- `Postgres → Memgraph` (via GraphProjector)
- `Memgraph → research context` (via ContextBuilder)
- `Memgraph → entry intent proposal → Postgres` (via IntentWriter)
- `Memgraph → policy proposal → Postgres` (via PolicyProposalWriter)

Not allowed:

- `Memgraph → live order decision`
- `Memgraph → direct position mutation`
- `Memgraph → direct kill-switch mutation`
- `Memgraph → direct config mutation`

Plain English: **Memgraph can suggest. Postgres decides. Worker executes.**

#### What To Stop Writing To Files

Replace these file-based stores with Memgraph:

- `context/knowledge/wiki/` — stock/sector notes, scan history, wikilinks
- `context/research/` — dated scan outputs and per-stock research evidence
- `news_cache.json`, `sentiment_cache.json` — durable news/articles/entities/sentiment
- `trade_observations.json`, `observations.json` — lessons and event observations
- meaningful operational incidents from Postgres, projected as `FailurePattern` memory
- `SKILL.md` / strategy versions as `SkillVersion` nodes

Keep as file cache for now (not yet promoted to graph):

- `macro_cache.json`, `options_cache.json`, `timesfm_cache.json`, `fundamentals_cache.json`, `institutional_flows_cache.json`
- When any of these values influence a research decision, persist a graph fact linked to the `ResearchRun` node.

#### Dashboard

- Update the knowledge graph screen to read the real Memgraph graph instead of the Phase 8 local mock
- Remove the pending mock badge from the knowledge graph panel
- Back the `/api/knowledge-graph` route with `ContextGraphRepository` queries

#### Documentation Updates Required In This Phase

- Update `docs/architecture/agent_cognition_architecture.md` memory section: replace markdown KG as long-term memory with Memgraph
- Update `docs/architecture/agent_cognition_implementation_plan.md`: add the Phase 11 graph-memory implementation section
- Update `docs/features/future-feature.md`: supersede the old Postgres-only graph entries with the Memgraph architecture decision

#### Definition Of Done

- Memgraph runs as an optional Docker Compose service; `make dev` and `make dev-detach` start it alongside the app and worker through the `memory` profile
- Memgraph Lab is available for local graph debugging
- Memgraph backup/restore is documented in `docs/runbooks/memgraph-backup-restore.md`
- `GraphProjector` is live and projects `execution_events` into Memgraph asynchronously
- `ContextGraphRepository` is the only way agents access Memgraph — no raw Cypher in agent code
- Research pipeline writes `ResearchRun` and candidate summaries to Memgraph, not to JSON files
- Knowledge graph dashboard screen reads real graph data from Memgraph
- Memgraph downtime does not affect order placement, reconciliation, or kill switch operation
- File-based memory stores (`context/knowledge/`, `context/research/`, observation caches) are no longer written by new code paths

### Phase 12: Memory Views And Google MCP Toolbox

Implementation:

- add compact **Postgres-backed** views for execution state:
  - portfolio risk
  - open positions
  - execution incidents
  - effective policy
  - session readiness
- add compact **Memgraph-backed** views for context/cognition state (Memgraph is live from Phase 11):
  - regime snapshots (reads `RegimeSnapshot` nodes from Memgraph)
  - similar past trades (reads `TradeMemory` nodes and `SIMILAR_TO` edges from Memgraph)
- add read-only Google MCP Toolbox toolsets for:
  - research (context from Memgraph: `ResearchRun`, `ResearchCandidate`, `SignalSnapshot`)
  - allocator (execution state from Postgres: positions, risk budget, effective policy)
  - post-trade review (hybrid: `TradeMemory` from Memgraph, trade rows from Postgres)
  - ops diagnostics (Postgres: incidents, reconciliation runs, operator controls)
- do not allow unrestricted SQL or unrestricted Cypher — all access goes through typed views
- do not allow writes through Toolbox
- if Memgraph is down, Toolbox falls back gracefully on Postgres-only context; execution is never blocked

Definition of done:

- LLM agents read compact, curated views (Postgres or Memgraph as appropriate) instead of raw JSON or unrestricted tables
- Toolbox is Memgraph-aware and Postgres-aware, with clean typed access for each data domain
- Toolbox remains fully out of the execution hot path
- Memgraph downtime degrades context quality only — it never blocks execution, reconciliation, or kill switches

### Phase 13: Slow Brain Desk And Session Planning

Implementation:

- add the overnight and pre-market agent desk:
  - `RegimeSynthesizer`
  - `UniverseFunnel`
  - `EvidenceAssembler`
  - `ThesisAgent`
  - `SkepticAgent`
  - `PortfolioRiskJudge`
  - `FinalIntentJudge`
  - `SessionPlanner`
- make all outputs structured:
  - `entry_intent`
  - `portfolio_fit_report`
  - optional `policy_proposal`
- keep the pre-market desk portfolio-aware across all active universes
- agents read regime and trade context from Memgraph (Phase 11) via the Toolbox (Phase 12)

Definition of done:

- new entries are produced by the bounded multi-agent desk, not by a single-pass scorer alone
- pre-market activation is portfolio-aware and universe-aware

### Phase 14: Bounded Intraday Exception Reasoning And Learning

Implementation:

- keep the live hot path deterministic
- add one optional `ExceptionAnalyst` only for bounded abnormal-event reasoning:
  - broker inconsistency
  - major gap or shock event
  - corporate-action surprise
  - unexpected regime break on existing positions
- add post-trade reviewer and policy analyst flows that can propose bounded overlays or strategy lessons
- require all intraday reasoning outputs to stay advisory unless explicitly mapped to a narrow deterministic policy hook
- post-trade lessons and failure patterns are written to Memgraph (Phase 11) for future reasoning cycles

Definition of done:

- market-hours execution still works if the LLM layer is unavailable
- intraday reasoning exists only for bounded anomalies, not routine order routing
- the system can learn and adapt without becoming an unbounded linear-bot-with-prompts

## Exact Repo Changes

### Files To De-Emphasize Or Retire From The Hot Path

- `context/state.json`
- `context/trades.json`
- `context/pending_approvals.json`
- `storage.py`
- `api/tasks/scheduler.py` running inside FastAPI lifespan
- the legacy ADK order execution path

### Existing Files To Refactor Heavily

- `api/routes/approvals.py`
- `api/routes/trades.py`
- `api/main.py`
- `auth/kite/client.py`
- `auth/token_manager.py`
- `tools/execution/order_execution.py`
- `tools/execution/gtt_manager.py`
- `agents/execution/monitor.py`
- `api/tasks/event_handlers.py`
- `dashboard/dashboard/state.py`

### Logic Worth Reusing

- `backtest/engine.py` for entry/exit accounting patterns
- `risk/engine.py` and `tools/execution/risk_check.py` for risk budget logic
- `api/tasks/activity_manager.py` as an operator-facing status surface

## What Not To Do

- do not keep live execution inside route-triggered ADK background tasks
- do not keep the scheduler inside FastAPI startup for the final live design
- do not continue modeling OCO GTT as two ids
- do not keep position truth in local JSON
- do not trail stops from stale cached prices
- do not let the dashboard or API mutate broker state directly
- do not use the LLM layer for real-time execution decisions
- do not let Google MCP Toolbox participate in hot-path writes
- do not let any agent mutate `config.yaml` directly at runtime
- do not run a multi-agent debate inside the market-hours execution path
- do not split live execution across one worker per universe

## Delivery Order

If the goal is one clean push instead of another partial retrofit, implement in this order:

1. Phase 0 and Phase 1
2. Phase 2 and Phase 3
3. Phase 4 and Phase 5
4. Phase 6 and Phase 7
5. Phase 8 and Phase 9
6. Phase 10 and Phase 11
7. Phase 12 and Phase 13
8. Phase 14

Reason:

- data model and worker ownership must exist before safe broker integration
- broker integration must exist before entry and protection state machines
- reconciliation and safety must be complete before unattended mode is enabled
- UI comes after execution truth, not before
- policy (Phase 10) comes after execution truth because `policy_overlays` depend on stable Postgres state
- **Phase 11 (Context Graph) precedes Phase 12 (Toolbox)** so the Toolbox is built correctly the first time — regime snapshots and trade memories go straight into Memgraph, never as throwaway Postgres views
- **Phase 12 (Toolbox) precedes Phase 13 (Slow Brain)** because Slow Brain agents need structured, curated access to both Postgres and Memgraph via the Toolbox
- **Phase 14 (Exception Reasoning)** comes last because it sits on top of the full stack: execution floor, Toolbox, and Slow Brain desk
- post-trade lessons feed back into the Phase 11 Memgraph graph, closing the learning loop

> See [docs/features/postgress-memgraph.md](../features/postgress-memgraph.md) for the full design rationale behind the Postgres + Memgraph split.

## Sources

Official broker sources:

- https://kite.trade/docs/connect/v3/user/
- https://kite.trade/docs/connect/v3/exceptions/
- https://kite.trade/docs/connect/v3/orders/
- https://kite.trade/docs/connect/v3/postbacks/
- https://kite.trade/docs/connect/v3/websocket/
- https://kite.trade/docs/connect/v3/gtt/
- https://kite.trade/docs/connect/v3/portfolio/
- https://kite.trade/docs/connect/v3/margins/
- https://support.zerodha.com/category/trading-and-markets/charts-and-orders/gtt/articles/what-is-the-good-till-triggered-gtt-feature
- https://support.zerodha.com/category/trading-and-markets/charts-and-orders/gtt/articles/gtts-disabled-cancelled-expired
- https://support.zerodha.com/category/trading-and-markets/charts-and-orders/gtt/articles/why-did-my-gtt-order-trigger-but-was-not-executed
- https://support.zerodha.com/category/trading-and-markets/trading-faqs/general/articles/validity-of-cdsl-tpin-authorisation
- https://support.zerodha.com/category/trading-and-markets/general-kite/kite-api/articles/how-do-i-sign-up-for-kite-connect

Open-source architecture references:

- https://nautilustrader.io/docs/latest/concepts/live/
- https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/key-concepts
- https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/event-handlers
- https://github.com/zerodha/kite-connect-python-example
- https://github.com/vnpy/vnpy
- https://github.com/QuantConnect/Lean.Brokerages.Tastytrade
- https://docs.freqtrade.io/en/2024.9/advanced-setup/
- https://hummingbot.org/client/global-configs/kill-switch/
