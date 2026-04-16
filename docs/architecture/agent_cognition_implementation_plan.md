# Agent Cognition Implementation Plan

> Last Updated: April 16, 2026
> This document is the repo-specific implementation plan for the cognitive and execution overhaul described in `agent_cognition_architecture.md`.

## Scope

This plan implements:

- slow-brain multi-agent deliberation
- fast-brain deterministic execution
- Postgres operational memory
- Google MCP Toolbox read-only toolsets
- dynamic policy overlays
- broker-truth execution and recovery

It assumes the execution hardening plan in `live_trading_one_shot_plan.md` remains in force.

## Success Criteria

The overhaul is successful when:

1. Overnight and pre-market research produce structured `entry_intents` through a small multi-agent desk.
2. Market-hours execution remains deterministic and broker-correct without depending on live LLM availability.
3. All live state is persisted in Postgres.
4. LLM agents read from curated Postgres views and the knowledge graph, not raw JSON.
5. Dynamic adaptation happens through bounded overlays, not direct YAML mutation.
6. The system can restart, reconcile, and recover without duplicating orders or losing protection.

## Delivery Strategy

Implement from the bottom up:

1. Postgres truth and worker ownership
2. Broker ingestion and reconciliation
3. Policy overlays and memory views
4. Slow-brain desk
5. Dashboard and read-side migration
6. Staged live enablement

## Phase 0: Guardrails And Freeze

### Objectives

- stop further hot-path drift
- lock in execution safety constraints

### Changes

- add environment gates:
  - `LIVE_TRADING_ENABLED`
  - `NEW_ENTRIES_ENABLED`
  - `EXIT_ONLY_MODE`
  - `USE_SLOW_BRAIN`
  - `USE_EXCEPTION_ANALYST`
- fix known critical defects:
  - `OrderExecutionAgent` / `place_order_async()` signature mismatch
  - duplicate `retry_failed_event` definition
  - live order path marking `submitted` as `filled`
- document daily operator bootstrap

### Files

- `agents/execution/order_agent.py`
- `tools/execution/order_execution.py`
- `api/tasks/event_bus.py`
- `.env.example`
- `docs/quickstart.md`

### Exit Criteria

- no known blocking correctness bug remains in the current execution path
- live entry flow is disabled by default until worker migration is complete

## Phase 1: Postgres Foundation

### Objectives

- establish the new source of truth

### New Modules

- `swingtradev3/memory/db.py`
- `swingtradev3/memory/models.py`
- `swingtradev3/memory/repositories.py`
- `swingtradev3/memory/projections.py`
- `swingtradev3/memory/migrations/`

### Technology

- PostgreSQL
- SQLAlchemy 2.x
- Alembic

### Core Tables

- `entry_intents`
- `approvals`
- `order_intents`
- `broker_orders`
- `broker_fills`
- `positions`
- `protective_triggers`
- `trades`
- `execution_events`
- `policy_overlays`
- `reconciliation_runs`
- `failure_incidents`
- `operator_controls`
- `auth_sessions`

### Compatibility Projection Layer

Continue generating:

- `context/state.json`
- `context/trades.json`
- `context/pending_approvals.json`

from Postgres projections so existing routes and the dashboard keep functioning during rollout.

### Migration

Import:

- `context/state.json`
- `context/trades.json`
- `context/pending_approvals.json`
- `context/auth/kite_session.json`

### Files To Touch

- `storage.py`
- `models.py`
- `api/routes/positions.py`
- `api/routes/trades.py`
- `api/routes/approvals.py`

### Exit Criteria

- Postgres is the source of truth for positions, trades, and approvals
- legacy JSON files are regenerated, not authored directly

## Phase 2: Worker Ownership

### Objectives

- remove live execution ownership from FastAPI

### New Modules

- `swingtradev3/execution/worker.py`
- `swingtradev3/execution/bootstrap.py`
- `swingtradev3/execution/state_machine.py`
- `swingtradev3/execution/operator_controls.py`

### Runtime Changes

- `app` becomes control plane + reads
- `worker` becomes single writer for live trading state
- scheduler jobs that mutate live execution move into `worker`

### Files To Touch

- `api/main.py`
- `api/tasks/scheduler.py`
- `docker-compose.dev.yml`
- `swingtradev3/Makefile`

### Service Additions

- `db`
- `worker`
- optional `toolbox`

### Exit Criteria

- only `worker` can submit broker actions
- multiple API instances do not duplicate scheduler mutations

## Phase 3: Broker Integration Overhaul

### Objectives

- make broker truth the foundation of execution state

### New Modules

- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/broker/kite_stream.py`
- `swingtradev3/broker/postbacks.py`
- `swingtradev3/broker/reducer.py`
- `swingtradev3/broker/types.py`

### Required Capabilities

- REST access for:
  - order placement
  - order history
  - positions
  - holdings
  - margins
  - GTT details
- WebSocket for:
  - order updates
  - quotes
- optional postback ingestion for redundancy

### Rules

- WebSocket is primary for live order updates
- reducer normalizes and deduplicates all inbound broker events
- order placement returns `submitted`, never `filled`
- GTT is modeled as one OCO trigger id

### Files To Refactor

- `auth/kite/client.py`
- `tools/execution/order_execution.py`
- `tools/execution/gtt_manager.py`
- `auth/token_manager.py`

### Exit Criteria

- worker can reconstruct positions, orders, and GTT state from broker data after restart

## Phase 4: Policy Layer

### Objectives

- support intelligent adaptation without uncontrolled mutation

### New Modules

- `swingtradev3/policy/models.py`
- `swingtradev3/policy/governor.py`
- `swingtradev3/policy/effective_policy.py`
- `swingtradev3/policy/bounds.py`

### Design

- keep `config.yaml` as base config
- introduce `policy_overlays` in Postgres
- build an `effective_policy` object at runtime from:
  - base config
  - operator controls
  - active overlays

### Overlay Control

- every overlay has:
  - reason
  - proposer
  - optional approver
  - expiry
  - rollback handle
- enforce hard bounds in code

### Candidate Overlay Keys

- `min_score_threshold`
- `max_position_size_pct`
- `new_entries_enabled`
- `max_same_sector_positions`
- `trail_stop_at_pct`
- `trail_to_pct`
- `debate_top_n`

### Exit Criteria

- no code path needs to mutate `config.yaml` at runtime
- dynamic policy lives in Postgres with full auditability

## Phase 5: Memory Views And MCP Toolbox

### Objectives

- expose safe, compact agent-facing memory

### New Modules

- `swingtradev3/memory/views.py`
- `swingtradev3/memory/context_builders.py`
- `swingtradev3/toolbox/toolsets.yaml`
- `swingtradev3/toolbox/README.md`

### Required Views

- `regime_snapshot_view`
- `candidate_memory_view`
- `portfolio_risk_view`
- `open_positions_view`
- `similar_trades_view`
- `trade_lesson_view`
- `execution_incidents_view`
- `policy_effective_view`
- `session_readiness_view`

### Google MCP Toolbox Usage

Use Toolbox only for read-only agent access.

Toolsets:

- `research_readonly`
- `allocator_readonly`
- `posttrade_readonly`
- `ops_readonly`

Rules:

- read-only DB role
- parameterized curated SQL tools only
- no unrestricted SQL
- no writes
- no worker dependency on Toolbox

### Exit Criteria

- LLM agents can query compact Postgres-backed memory without touching raw tables

## Phase 6: Slow Brain Desk

### Objectives

- replace single-pass scoring with bounded multi-agent deliberation

### New Modules

- `swingtradev3/cognition/slow_brain/orchestrator.py`
- `swingtradev3/cognition/slow_brain/evidence_assembler.py`
- `swingtradev3/cognition/slow_brain/thesis_agent.py`
- `swingtradev3/cognition/slow_brain/skeptic_agent.py`
- `swingtradev3/cognition/slow_brain/portfolio_risk_judge.py`
- `swingtradev3/cognition/slow_brain/final_intent_judge.py`
- `swingtradev3/cognition/types.py`

### Desk Flow

1. `RegimeSynthesizer`
2. `UniverseFunnel`
3. `EvidenceAssembler`
4. `ThesisAgent`
5. `SkepticAgent`
6. `PortfolioRiskJudge`
7. `FinalIntentJudge`

### Routing Rules

- only top-ranked or ambiguous candidates go through full thesis/skeptic challenge
- low-conviction candidates stay on a lightweight path
- every agent outputs structured JSON, not prose-only discussions

### Output Contract

- `entry_intent`
- optional `policy_proposal`

### Existing Modules To Refactor

- `agents/research/pipeline.py`
- `agents/research/scorer_agent.py`
- `llm/prompt_builder.py`
- `knowledge/wiki_renderer.py`

### Exit Criteria

- research no longer depends on one single scoring pass
- final intents include evidence trace, risk trace, and confidence band

## Phase 7: Pre-Market Session Planning

### Objectives

- decide what actually becomes tradable today

### New Modules

- `swingtradev3/cognition/pre_market/session_planner.py`
- `swingtradev3/cognition/pre_market/readiness.py`

### Inputs

- approved intents
- portfolio and cash state
- market readiness
- policy overlays
- operator controls

### Outputs

- `session_execution_plan`

### Rules

- planner can activate, defer, or cancel intents
- planner cannot override kill switch or exit-only mode

### Exit Criteria

- market-hours worker consumes a single structured session plan

## Phase 8: Fast Brain Core

### Objectives

- build deterministic market-hours execution and protection management

### New Modules

- `swingtradev3/execution/coordinator.py`
- `swingtradev3/execution/protection_manager.py`
- `swingtradev3/execution/trailing_engine.py`
- `swingtradev3/execution/reconciler.py`
- `swingtradev3/execution/incident_manager.py`
- `swingtradev3/execution/risk_guard.py`

### Required Behavior

- consume `session_execution_plan`
- submit entries
- track partial fills
- arm OCO GTT after confirmed fill
- trail using deterministic rules and quote truth
- reconcile continuously
- escalate incidents

### Existing Modules To Replace Or Shrink

- `agents/execution/order_agent.py`
- `agents/execution/monitor.py`
- `api/tasks/event_handlers.py`

### Exit Criteria

- all live order and protection behavior is deterministic and broker-truth-driven

## Phase 9: Exception Analyst

### Objectives

- allow bounded intraday reasoning without making the hot path conversational

### New Modules

- `swingtradev3/cognition/exception_analyst.py`
- `swingtradev3/cognition/exception_packets.py`

### Trigger Conditions

- major news shock
- sudden regime break
- broker-state inconsistency
- GTT rejection or repeated recovery failure
- corporate action surprise

### Guardrails

- max runtime budget
- bounded allowed action set
- deterministic fallback if timeout/error
- no raw broker action rights

### Exit Criteria

- intraday reasoning exists only as bounded exception handling

## Phase 10: Learning And Adaptation

### Objectives

- close the feedback loop without uncontrolled self-modification

### New Modules

- `swingtradev3/cognition/learning/trade_reviewer.py`
- `swingtradev3/cognition/learning/policy_analyst.py`
- `swingtradev3/cognition/learning/strategy_editor.py`

### Learning Outputs

- trade observations
- setup-level lessons
- bounded `policy_proposals`
- staged `SKILL.md` edits

### Rules

- policy proposals go through `PolicyGovernor`
- `SKILL.md` changes stay staged until explicitly promoted
- no automatic promotion of unbounded strategy changes

### Existing Modules To Refactor

- `agents/learning/reviewer.py`
- `agents/learning/lesson_agent.py`

### Exit Criteria

- the system can learn from outcomes while remaining controlled

## Phase 11: Dashboard And Operator UX

### Objectives

- make the new architecture observable and operable

### UI Surfaces

- intent pipeline
- broker order state
- open positions
- protection status
- reconciliation freshness
- auth status
- policy overlays
- incidents and kill switches
- exception-analysis recommendations

### Existing Files To Refactor

- `dashboard/dashboard/state.py`
- `dashboard/dashboard/pages/approvals.py`
- `dashboard/dashboard/pages/portfolio.py`
- `dashboard/dashboard/pages/activity.py`
- `api/routes/dashboard.py`

### Exit Criteria

- operator can see the full state machine, not just file-backed snapshots

## Phase 12: Testing And Rollout

### New Test Areas

- state machine tests
- reducer tests
- GTT watchdog tests
- reconciliation tests
- policy governor tests
- Toolbox read-model tests
- slow-brain structured output tests
- exception-analyst bounded-action tests
- end-to-end entry-to-exit lifecycle tests
- restart recovery tests

### Rollout Ladder

1. unit and integration tests green
2. Dockerized paper-mode soak
3. live mode with manual approvals and deterministic execution only
4. overnight slow-brain enabled
5. pre-market session planner enabled
6. exception analyst enabled for advisory only
7. same-day unattended mode enabled
8. multi-day unattended mode only if DDPI/POA and daily login operations are confirmed

## Agent Catalog Summary

### Research / Deliberation

- `RegimeSynthesizer`
- `UniverseFunnel`
- `EvidenceAssembler`
- `ThesisAgent`
- `SkepticAgent`
- `PortfolioRiskJudge`
- `FinalIntentJudge`
- `SessionPlanner`

### Market-Hours Core

- `ExecutionCoordinator`
- `BrokerReducer`
- `ProtectionManager`
- `TrailingEngine`
- `Reconciler`
- `RiskGuard`
- `IncidentManager`
- `ExceptionAnalyst`

### Learning

- `TradeReviewer`
- `PolicyAnalyst`
- `StrategyEditor`

## Repo-Level File Plan

### New Top-Level Packages

- `swingtradev3/broker/`
- `swingtradev3/cognition/`
- `swingtradev3/execution/`
- `swingtradev3/memory/`
- `swingtradev3/policy/`
- `swingtradev3/toolbox/`

### Legacy Paths To De-Emphasize

- `context/state.json`
- `context/trades.json`
- `context/pending_approvals.json`
- route-triggered execution through ADK background runs
- scheduler ownership inside FastAPI lifespan

## What Must Not Change

- execution worker remains single writer
- broker truth remains authoritative
- Toolbox remains read-only
- `config.yaml` remains base config, not a live mutable control plane
- LLMs remain out of direct broker action paths

## References

- `agent_cognition_architecture.md`
- `live_trading_one_shot_plan.md`
- `findings.md`

External sources:

- https://kite.trade/docs/connect/v3/user/
- https://kite.trade/docs/connect/v3/orders/
- https://kite.trade/docs/connect/v3/postbacks/
- https://kite.trade/docs/connect/v3/websocket/
- https://kite.trade/docs/connect/v3/gtt/
- https://kite.trade/docs/connect/v3/portfolio/
- https://kite.trade/docs/connect/v3/margins/
- https://cloud.google.com/blog/products/ai-machine-learning/new-mcp-integrations-to-google-cloud-databases
- https://googleapis.github.io/genai-toolbox/getting-started/introduction/
- https://googleapis.github.io/genai-toolbox/resources/tools/postgres/
- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://adk.dev/get-started/about/
- https://docs.langchain.com/oss/python/langchain/multi-agent
- https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/multi-agent-debate.html
- https://nautilustrader.io/docs/latest/concepts/live/
