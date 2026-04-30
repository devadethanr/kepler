# Live Trading One-Shot Plan

> Last Updated: April 17, 2026
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
- **Memory**: knowledge graph plus Postgres execution and trade history
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
  - Phase 8 remains dashboard/API/SSE/projection work. The knowledge graph screen stays as an explicit mock.
  - Phase 14 becomes the real Postgres + Memgraph context graph/memory phase.

  - Replace Dockerfile.dashboard with a Node/Vite runtime and update docker-compose.dev.yml to mount/build ./swingtradev3-dashboard, not ./swingtradev3/dashboard.
  - Use Vite dev proxy /api -> http://app:8000 so the browser calls same-origin /api/...; inject X-API-Key from dashboard container env in the proxy instead of hardcoding API keys into React.
  - Add frontend data layer packages: @tanstack/react-query for request/mutation cache, zod for response validation, and @microsoft/fetch-event-source for SSE because native EventSource does not support custom request headers.
  - Remove unused AI Studio/server packages from the dashboard app: @google/genai, dotenv, express, @types/express; keep react-force-graph-3d, three, recharts, motion, and lucide-react.
  - Add src/lib/api.ts, src/lib/sse.ts, src/lib/schemas.ts, and feature hooks so screens do not call fetch directly.
  - Keep KnowledgeScreen as a deterministic local mock with a visible Phase 14 Mock badge; remove markdown/file language like “View Markdown Base” and do not read context/knowledge in Phase 8.
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
  | Knowledge graph | local mock only in Phase 8; real API deferred to Phase 14 |


Definition of done:

- the dashboard reflects broker-confirmed state, not stale local assumptions

### Phase 9: Tests And Staged Enablement

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

### Phase 10: Policy Layer And Effective Policy

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

### Phase 11: Memory Views And Google MCP Toolbox

Implementation:

- add compact Postgres-backed views for:
  - regime snapshots
  - portfolio risk
  - open positions
  - similar past trades
  - execution incidents
  - effective policy
  - session readiness
- add read-only Google MCP Toolbox toolsets for:
  - research
  - allocator
  - post-trade review
  - ops diagnostics
- do not allow unrestricted SQL and do not allow writes through Toolbox

Definition of done:

- LLM agents read compact, curated Postgres views instead of raw JSON or unrestricted tables
- Toolbox remains fully out of the execution hot path

### Phase 12: Slow Brain Desk And Session Planning

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

Definition of done:

- new entries are produced by the bounded multi-agent desk, not by a single-pass scorer alone
- pre-market activation is portfolio-aware and universe-aware

### Phase 13: Bounded Intraday Exception Reasoning And Learning

Implementation:

- keep the live hot path deterministic
- add one optional `ExceptionAnalyst` only for bounded abnormal-event reasoning:
  - broker inconsistency
  - major gap or shock event
  - corporate-action surprise
  - unexpected regime break on existing positions
- add post-trade reviewer and policy analyst flows that can propose bounded overlays or strategy lessons
- require all intraday reasoning outputs to stay advisory unless explicitly mapped to a narrow deterministic policy hook

Definition of done:

- market-hours execution still works if the LLM layer is unavailable
- intraday reasoning exists only for bounded anomalies, not routine order routing
- the system can learn and adapt without becoming an unbounded linear-bot-with-prompts

## Phase 14 Context Graph Plan
@docs/features/postgress-memgraph.md
  - Add a dedicated “Context Graph / Memory System” phase after Phase 13, or immediately after Phase 8 if we choose to prioritize memory next.
  - Keep Postgres as execution truth: orders, fills, positions, trades, approvals, incidents, reconciliation, auth, operator controls, and policy overlays.
  - Add Memgraph as context graph truth: stocks, sectors, indices, research runs, candidates, news, regimes, signal snapshots, trade memories, lessons, failure patterns, and skill versions.
  - Connect Postgres and Memgraph only through controlled projectors: Postgres execution_events -> GraphProjector -> Memgraph.
  - Do not let Memgraph submit orders, mutate positions, clear incidents, edit config, or participate in worker hot-path execution.
  - Replace file-based knowledge/research memory with typed graph repositories; no migration of old dev data.
  - Update the knowledge graph dashboard screen to read the real graph only in Phase 14.

  ## Documentation Updates

  - Update docs/architecture/live_trading_one_shot_plan.md Phase 8 to reference the React dashboard, DB-backed APIs, durable SSE, and old dashboard removal.
  - Add Phase 14 to docs/architecture/live_trading_one_shot_plan.md for Postgres + Memgraph context graph.
  - Update docs/architecture/agent_cognition_architecture.md memory section to replace markdown KG as long-term memory with Memgraph.
  - Update docs/architecture/agent_cognition_implementation_plan.md dashboard phase to point at swingtradev3-dashboard, and add the Phase 14 graph-memory implementation section.
  - Also update docs/features/future-feature.md because it currently says “no new database” and selects Active Graph KG; that must be superseded if Memgraph is the chosen architecture.

  ## Test Plan

  - Run npm ci, npm run lint, and npm run build in swingtradev3-dashboard.
  - Add frontend API-client tests for request headers, Zod parsing, and SSE reconnect behavior.
  - Add FastAPI tests proving positions, trades, portfolio, approvals, and dashboard routes no longer read JSON files.
  - Add SSE tests for cursor resume, heartbeat, and event ordering from execution_events.
  - Run make test and make phase7-check from swingtradev3.
  - Verify make dev-detach starts the React dashboard at the existing dashboard port.

  ## Assumptions

  - swingtradev3-dashboard is the only dashboard going forward.
  - Old dashboard folders can be deleted after the new Compose runtime works.
  - Knowledge graph UI remains mock-only in Phase 8.
  - No existing context/research/wiki data migration is required.
  - Sources checked for package decisions: TanStack Query docs, Zod docs, MDN EventSource docs, and Microsoft fetch-event-source docs.

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

Reason:

- data model and worker ownership must exist before safe broker integration
- broker integration must exist before entry and protection state machines
- reconciliation and safety must be complete before unattended mode is enabled
- UI comes after execution truth, not before
- policy and memory views come after execution truth because they depend on stable Postgres state
- the slow-brain desk and exception analyst come after the execution floor because agentic reasoning should sit on top of a safe, deterministic runtime

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
