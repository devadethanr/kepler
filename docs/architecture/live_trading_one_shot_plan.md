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

### Phase 3: Rebuild Broker Integration Around Truth

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

### Phase 4: Rebuild Entry Execution

Refactor:

- `api/routes/approvals.py`
- `agents/execution/order_agent.py`
- `tools/execution/order_execution.py`
- `api/tasks/morning_briefing.py`

Implementation:

- stop executing by ticker; execute by `order_intent_id`
- stop scanning the whole approval file on every execution cycle
- persist one `order_intent` per candidate
- approval only changes state; it does not directly perform broker actions
- the worker consumes approved intents, submits broker orders, and waits for broker-confirmed fills
- only after `entry_filled` does the worker create the position and request protection

Optional operating mode:

- keep manual approvals as a gate
- later add `AUTO_APPROVE_ENTRIES=true` for unattended operation

Definition of done:

- no route directly places orders
- every entry has a durable audit trail from proposal to fill

### Phase 5: Rebuild Protection And Exit Logic

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

### Phase 6: Reconciliation And Recovery

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

### Phase 7: Safety, Auth, And Operator Controls

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

### Phase 8: Dashboard, API, And Compatibility Projections

Refactor:

- `dashboard/dashboard/state.py`
- `api/routes/positions.py`
- `api/routes/trades.py`
- `api/routes/portfolio.py`
- `api/routes/dashboard.py`

Implementation:

- switch UI to DB-backed projections:
  - intent status
  - broker order state
  - GTT protection state
  - last reconciliation time
  - auth/session status
  - kill-switch state
  - unresolved incidents
- keep `pending_approvals.json`, `state.json`, and `trades.json` only as migration-era compatibility views
- remove the hardcoded dashboard API key fallback
- make SSE read from execution projections or an `execution_events` tail instead of the in-process event bus only

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

## Exact Repo Changes

### Files To De-Emphasize Or Retire From The Hot Path

- `context/state.json`
- `context/trades.json`
- `context/pending_approvals.json`
- `storage.py`
- `api/tasks/scheduler.py` running inside FastAPI lifespan
- `agents/execution/order_agent.py` as the primary execution engine

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
