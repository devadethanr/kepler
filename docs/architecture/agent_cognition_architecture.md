# Agent Cognition Architecture

> Last Updated: April 17, 2026
> This document defines the target cognitive architecture for `swingtradev3`.
> It complements `live_trading_one_shot_plan.md` by specifying the agent roles, memory model, decision rights, and phase-by-phase orchestration.

## Purpose

The target system is not a linear “scan -> score -> order” bot. It is a bounded autonomous trading system with:

- **Slow Brain**: overnight and pre-market multi-agent deliberation
- **Fast Brain**: market-hours deterministic execution and risk control
- **Memory**: knowledge graph plus Postgres execution and trade history
- **Policy Layer**: dynamic overlays, not free-form config mutation
- **Execution Core**: broker-truth worker
- **Recovery Layer**: reconciliation, kill switches, and incident handling

## Design Goals

1. Produce genuinely better trade intents than a single-pass scorer.
2. Keep market-hours execution deterministic, fast, and broker-correct.
3. Make memory explicit and queryable.
4. Allow intelligent adaptation without giving the model unrestricted runtime control.
5. Be restart-safe, auditable, and testable.

## Hard Constraints

- Broker truth is authoritative.
- No LLM is allowed to place orders directly.
- No LLM is allowed to mutate `config.yaml` directly.
- Market-hours hot-path logic must work if the LLM layer is unavailable.
- Google MCP Toolbox is read-only for agent access to Postgres views.
- Direct Postgres access is reserved for the worker, reconciler, and other deterministic runtime services.

## Top-Level Runtime

```text
                          ┌──────────────────────┐
                          │     Reflex UI        │
                          │  Telegram / REST     │
                          └──────────┬───────────┘
                                     │
                          control + read models
                                     │
                    ┌────────────────▼────────────────┐
                    │        FastAPI Control Plane    │
                    │ intents, approvals, dashboards  │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │    Postgres Truth    │
                          │ orders, fills, posns │
                          └───────┬───────┬──────┘
                                  │       │
                       read-only  │       │  direct
                       MCP/SDK     │       │  write/read
                                  │       │
                ┌─────────────────▼─┐   ┌─▼──────────────────┐
                │  Slow Brain Desk  │   │  Fast Brain Worker  │
                │ overnight/premark │   │ market-hours core   │
                └──────────┬────────┘   └─────┬─────┬─────────┘
                           │                  │     │
                           ▼                  ▼     ▼
                    entry intents        Kite REST  Kite WS
                                              │       │
                                              └──┬────┘
                                                 ▼
                                           Recovery Layer
```

## Service Topology

### `app`

- FastAPI control plane
- read APIs
- operator actions
- SSE and dashboard read models
- no hot-path execution ownership

### `worker`

- the only service allowed to:
  - submit broker orders
  - modify GTTs
  - close positions
  - write execution truth
  - apply policy overlays

### `db`

- Postgres source of truth
- append-only execution events
- projections and views for agent context

### `toolbox`

- Google MCP Toolbox for Databases
- read-only Postgres toolsets for slow-brain and analyst agents
- never used by the execution worker for writes

### `dashboard`

- Reflex UI
- reads projections only

### `kite-mcp`

- optional broker-side helper
- diagnostic or fallback tool integration only
- not the primary execution truth channel

## Brain Split

## Slow Brain

The Slow Brain is responsible for research, thesis generation, adversarial challenge, portfolio fit, and pre-market session planning.

Characteristics:

- higher latency is acceptable
- multi-agent reasoning is acceptable
- outputs must be structured and bounded
- all final outputs become `entry_intents` or `policy_proposals`

### Slow-Brain Roles

#### 1. `RegimeSynthesizer`

Type:

- deterministic with optional LLM narration

Responsibilities:

- classify regime
- summarize macro/flow/volatility state
- produce the regime packet for the desk

Inputs:

- market regime indicators
- VIX / breadth / FII-DII / overnight news

Outputs:

- `regime_snapshot`
- `session_constraints`

Authority:

- none over execution

#### 2. `UniverseFunnel`

Type:

- deterministic

Responsibilities:

- reduce the universe
- gather candidate evidence bundles

Inputs:

- market/news/flow/options/technical scans

Outputs:

- candidate dossiers

Authority:

- none over execution

#### 3. `EvidenceAssembler`

Type:

- deterministic

Responsibilities:

- normalize all candidate context into a compact structured packet
- attach relevant memory from Postgres and the knowledge graph

Inputs:

- candidate dossier
- similar past trades
- current portfolio exposure
- knowledge-graph context

Outputs:

- `candidate_context_v1`

Authority:

- none over execution

#### 4. `ThesisAgent`

Type:

- LLM

Responsibilities:

- build the strongest possible long thesis
- specify setup quality, catalyst strength, invalidation logic

Inputs:

- `candidate_context_v1`
- strategy philosophy
- regime packet

Outputs:

- `thesis_report`

Authority:

- can recommend
- cannot allocate

#### 5. `SkepticAgent`

Type:

- LLM

Responsibilities:

- attack the thesis
- identify hidden risk, fragility, late-entry risk, correlation risk

Inputs:

- same as `ThesisAgent`
- `thesis_report`

Outputs:

- `skeptic_report`

Authority:

- can veto only through structured risk flags
- cannot execute

#### 6. `PortfolioRiskJudge`

Type:

- LLM or deterministic hybrid

Responsibilities:

- assess fit against:
  - existing positions
  - sector concentration
  - regime
  - cash
  - risk budget
  - current policy overlays

Inputs:

- thesis + skeptic outputs
- live portfolio/risk views

Outputs:

- `portfolio_fit_report`
- recommended sizing band

Authority:

- may downgrade or reject
- cannot place orders

#### 7. `FinalIntentJudge`

Type:

- LLM with strict structured output

Responsibilities:

- emit the final `entry_intent`
- include confidence band, reasons, invalidation points, and evidence trace

Inputs:

- all prior reports

Outputs:

- `entry_intent`
- optional `policy_proposal`

Authority:

- can create intents only

#### 8. `SessionPlanner`

Type:

- one pre-market judge

Responsibilities:

- rank approved intents
- convert them into a pre-market execution plan
- decide which entries are active today

Inputs:

- approved intents
- live funds
- regime
- current positions
- operator controls

Outputs:

- `session_execution_plan`

Authority:

- can activate, defer, or cancel planned intents
- cannot bypass kill switches

## Fast Brain

The Fast Brain is not a debating system. It is a deterministic event-driven engine for broker interaction, risk control, and recovery.

Characteristics:

- sub-second to low-second reaction time
- zero dependence on multi-agent discussion
- broker-truth-first
- must remain safe under LLM outage

### Fast-Brain Components

#### 1. `ExecutionCoordinator`

Responsibilities:

- consume `session_execution_plan`
- submit entry orders
- track order states
- move intents through the execution state machine

#### 2. `BrokerReducer`

Responsibilities:

- ingest WebSocket updates, postbacks, and REST snapshots
- deduplicate and normalize broker events
- update `broker_orders`, `fills`, `positions`, `protective_triggers`

#### 3. `ProtectionManager`

Responsibilities:

- arm GTT only after confirmed entry fill
- maintain one OCO trigger per position
- track trigger status and resulting exit order lifecycle

#### 4. `TrailingEngine`

Responsibilities:

- apply deterministic trailing rules from effective policy
- throttle modifications
- log every change

#### 5. `Reconciler`

Responsibilities:

- startup sync
- runtime drift detection
- snapshot alignment with positions, orders, GTT, and holdings

#### 6. `RiskGuard`

Responsibilities:

- enforce portfolio and operational risk limits
- block new entries
- flip exit-only mode
- request flatten

#### 7. `IncidentManager`

Responsibilities:

- persist incidents
- classify severity
- escalate to operator controls

#### 8. `ExceptionAnalyst`

Type:

- single bounded LLM agent

Responsibilities:

- analyze rare abnormal situations
- recommend only from an allowed action set

Inputs:

- incident packet
- execution state
- broker truth
- relevant market/news context

Outputs:

- `exception_recommendation`

Allowed actions:

- `hold_current_plan`
- `tighten_stop`
- `pause_new_entries`
- `reduce_position`
- `flatten_position`
- `escalate_operator`

Authority:

- advisory unless explicitly enabled for a narrow bounded policy
- never submits raw broker actions directly

## Memory Architecture

The system uses three memory classes.

### Long-Term Memory

- markdown knowledge graph under `context/knowledge/wiki`
- thesis evolution
- stock notes
- sector notes
- trade journals

Use:

- qualitative context
- historical analogs
- narrative continuity

### Operational Memory

- Postgres source of truth
- orders
- fills
- positions
- protective triggers
- trades
- incidents
- reconciliations
- active policy overlays

Use:

- all live trading decisions
- all operator views
- all recovery logic

### Session Memory

- short-lived orchestrator/session context
- candidate packets
- current research batch state

Use:

- one run of the research desk
- one pre-market planning session

## Postgres As Memory

Postgres is the authority for:

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

Agents should not read these base tables directly. They should read curated views.

### Required Read Models

- `regime_snapshot_view`
- `candidate_memory_view`
- `portfolio_risk_view`
- `open_positions_view`
- `similar_trades_view`
- `execution_incidents_view`
- `policy_effective_view`
- `session_readiness_view`
- `trade_lesson_view`

## Google MCP Toolbox Usage

Use Google MCP Toolbox for Databases only as a read-only agent access layer over Postgres.

### Why It Fits

- good for slow-brain agent retrieval
- good for analyst and post-trade queries
- good for ops/incident copilots

### Why It Must Stay Out Of The Hot Path

- execution worker needs direct low-latency DB access
- reconciliation needs deterministic writes
- kill switches and protection logic cannot depend on an LLM tool broker
- Toolbox and several prebuilt flows are not intended as production trading write paths

### Toolset Design

Create separate read-only toolsets:

- `research_readonly`
- `allocator_readonly`
- `posttrade_readonly`
- `ops_readonly`

Only expose parameterized curated SQL tools such as:

- `get_candidate_memory`
- `get_similar_trades`
- `get_portfolio_risk_snapshot`
- `get_active_policy`
- `get_execution_incidents`
- `get_stock_kg_summary`

Do not expose:

- generic unrestricted SQL execution
- any write-capable DB tool
- any direct broker action through Toolbox

## Policy Layer

The policy layer is how the system becomes adaptive without becoming unstable.

### Split Of Responsibility

- `config.yaml`: human-owned base invariants
- `policy_overlays` in Postgres: bounded dynamic adaptations

### Overlay Scopes

- global
- regime
- session-date
- symbol
- sector

### Overlay Examples

- `min_score_threshold`
- `new_entries_enabled`
- `max_position_size_pct`
- `max_same_sector_positions`
- `trail_stop_at_pct`
- `trail_to_pct`
- `use_debate_for_top_n`

### Required Fields

- `policy_key`
- `base_value`
- `override_value`
- `scope`
- `reason`
- `proposed_by`
- `approved_by`
- `effective_from`
- `expires_at`
- `rollback_token`

### Policy Governor

The `PolicyGovernor` applies overlays with:

- hard numeric bounds
- expiry
- audit trail
- rollback support
- operator override

The LLM layer may propose overlays. It may not directly rewrite `config.yaml`.

## Phase-Oriented Orchestration

### Evening Research

- `RegimeSynthesizer`
- `UniverseFunnel`
- `EvidenceAssembler`
- `ThesisAgent`
- `SkepticAgent`
- `PortfolioRiskJudge`
- `FinalIntentJudge`

Output:

- `entry_intents`
- optional `policy_proposals`

### Pre-Market

- operator/bootstrap checks
- session readiness reconciliation
- `SessionPlanner`

Output:

- `session_execution_plan`

### Market Hours

- deterministic worker runs plan
- reconciler stays active
- protection manager and trailing engine stay active
- `ExceptionAnalyst` runs only on abnormal incidents

### Post-Market

- `TradeReviewer`
- `PolicyAnalyst`
- knowledge-graph updates

### Monthly / Quarterly

- `LessonAgent`
- human review of staged strategy edits
- controlled promotion of policy and strategy updates

## Agent Count And Debate Policy

The system should not use the same number of agents for every situation.

### Overnight / Pre-Market

Use a small desk:

- one deterministic evidence assembler
- three or four reasoning agents
- one final judge

### Market Hours

Use:

- zero debate agents in the hot path
- one optional exception-analysis agent only on anomalies

### Escalation Rules

Use the full desk only for:

- top-ranked ideas
- large-capital ideas
- borderline thesis/skeptic disagreement
- unusual catalysts

Skip full debate for:

- low-conviction ideas
- routine monitoring
- trailing/stop logic
- broker recovery

## Why This Is L4-Style And Not Linear

This architecture becomes high-autonomy because it closes the loop:

- it observes the market and broker state
- it forms and challenges hypotheses
- it commits structured intentions
- it executes through deterministic worker ownership
- it verifies against broker truth
- it reconciles and recovers from drift
- it learns and updates policy under bounded controls

That is materially different from a pipeline bot that only scores and submits.

## What This Architecture Avoids

- one giant monolithic “super trader” prompt
- a debate room on every tick
- raw LLM control of broker actions
- direct live mutation of `config.yaml`
- file-backed position truth
- hot-path dependence on MCP Toolbox or the dashboard

## Repo Mapping

### New Packages

- `swingtradev3/cognition/`
- `swingtradev3/execution/`
- `swingtradev3/memory/`
- `swingtradev3/policy/`
- `swingtradev3/broker/`
- `swingtradev3/toolbox/`

### Existing Packages To Rework

- `agents/research/`
- `agents/execution/`
- `agents/learning/`
- `api/tasks/`
- `auth/kite/`
- `dashboard/`

## References

Official platform sources:

- https://kite.trade/docs/connect/v3/user/
- https://kite.trade/docs/connect/v3/orders/
- https://kite.trade/docs/connect/v3/postbacks/
- https://kite.trade/docs/connect/v3/websocket/
- https://kite.trade/docs/connect/v3/gtt/
- https://kite.trade/docs/connect/v3/portfolio/
- https://kite.trade/docs/connect/v3/margins/
- https://cloud.google.com/blog/products/ai-machine-learning/new-mcp-integrations-to-google-cloud-databases
- https://googleapis.github.io/genai-toolbox/getting-started/introduction/
- https://googleapis.github.io/genai-toolbox/getting-started/local_quickstart/

Architecture references:

- https://www.anthropic.com/engineering/building-effective-agents
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://adk.dev/get-started/about/
- https://adk.dev/agents/workflow-agents/parallel-agents/
- https://docs.langchain.com/oss/python/langchain/multi-agent
- https://docs.langchain.com/oss/python/deepagents/deep-research
- https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/design-patterns/multi-agent-debate.html
- https://nautilustrader.io/docs/latest/concepts/live/
- https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/key-concepts
- https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/reconciliation
- https://www.freqtrade.io/en/stable/stoploss/
