# Postgres + Memgraph Context Memory

This is the Phase 11 architecture decision for graph memory.

## Decision

Use both databases, with strict ownership boundaries:

```text
Postgres = execution truth      (protects money)
Memgraph = context graph truth  (improves memory and reasoning)
Files    = temporary caches and compatibility exports only
```

Memgraph is not a replacement for Postgres. It owns the context, research, and
learning graph. Postgres remains authoritative for execution, controls, and audit.

## Why Both Exist

Postgres is the right store for deterministic trading state:

- one order intent should not be submitted twice
- a position must have one current lifecycle state
- kill switches must be reliable
- approvals must be auditable
- trades, fills, and protective triggers must reconcile exactly
- worker locks and transactions must be deterministic

Memgraph is the right store for relationship traversal and retrieval:

- show stocks similar to past winners in this regime
- connect news themes to sectors and symbols
- identify repeated failure patterns across trades
- retrieve lessons that apply to a candidate
- attach research memory to stock, sector, regime, sentiment, and outcome context

Plain English: Memgraph can suggest. Postgres decides. Worker executes.

## Ownership

Postgres owns execution-critical state:

- `entry_intents`
- `approvals`
- `order_intents`
- `broker_orders`
- `broker_fills`
- `positions`
- `protective_triggers`
- `trades`
- `operator_controls`
- `failure_incidents`
- `reconciliation_runs`
- `auth_sessions`
- `policy_overlays`

Memgraph owns context and cognition state:

- `Stock`
- `Sector`
- `Index`
- `ResearchRun`
- `ResearchCandidate`
- `NewsArticle`
- `RegimeSnapshot`
- `SignalSnapshot`
- `TechnicalSnapshot`
- `FundamentalSnapshot`
- `SentimentSnapshot`
- `TradeMemory`
- `Observation`
- `Lesson`
- `FailurePattern`
- `SkillVersion`

Core edges:

- `MEMBER_OF`
- `BELONGS_TO_SECTOR`
- `ANALYZED_IN`
- `HAS_SIGNAL`
- `MENTIONS`
- `AFFECTS_STOCK`
- `UNDER_REGIME`
- `GENERATED_INTENT`
- `EXECUTED_AS`
- `CLOSED_AS`
- `PRODUCED_OBSERVATION`
- `SUPPORTS_LESSON`
- `SIMILAR_TO`
- `FAILED_DURING`

Every node and edge should carry:

- `source`
- `source_id`
- `source_path` or `postgres_table` / `postgres_pk`
- `observed_at`
- `ingested_at`
- `payload_hash`
- `confidence`
- `projection_version`

## Dev Stack

Phase 11 adds official open-source Memgraph development services:

- `memgraph`: `memgraph/memgraph-mage:latest`
- `memgraph-lab`: `memgraph/lab:latest`
- Compose profile: `memory`
- Bolt: `localhost:${MEMGRAPH_BOLT_PORT:-7687}`
- Lab: `http://localhost:${MEMGRAPH_LAB_PORT:-3000}`
- Monitoring/log WebSocket: `localhost:${MEMGRAPH_MONITORING_PORT:-7444}`

`make dev` and `make dev-detach` start the `memory` profile automatically. The app and
worker do not depend on Memgraph to boot because graph downtime must not affect trading
safety.

Dev durability settings:

- Memgraph data is persisted in the `memgraph_data` Docker volume.
- Memgraph logs are persisted in the `memgraph_logs` Docker volume.
- Periodic snapshots and WAL are enabled.
- The dev memory cap is controlled by `MEMGRAPH_MEMORY_LIMIT_MIB` and defaults to `2048`.

Runbook:

- [docs/runbooks/memgraph-backup-restore.md](../runbooks/memgraph-backup-restore.md)

## Connection Flow

```text
Research / agents / market data
        |
        v
Postgres execution truth          Memgraph context truth
        |                                 ^
        |                                 |
        +-------- GraphProjector ---------+
                  (one-way, async)
```

Controlled bridges:

- `GraphProjector`: reads Postgres execution events and writes derived memory to Memgraph
- `ContextGraphRepository`: typed Memgraph access layer; no raw Cypher scattered across agents
- `ContextBuilder`: reads Memgraph for agent prompts and research context
- `IntentWriter`: converts approved research output into Postgres `entry_intents`
- `PolicyProposalWriter`: converts graph/learning insight into Postgres `policy_overlay`
  proposals, never direct config mutation

Allowed directionality:

- Postgres -> Memgraph
- Memgraph -> research context
- Memgraph -> entry intent proposal -> Postgres
- Memgraph -> policy proposal -> Postgres

Not allowed:

- Memgraph -> live order decision
- Memgraph -> direct position mutation
- Memgraph -> direct kill-switch mutation
- Memgraph -> direct config mutation

## What Moves Out Of Files

Move these file-backed stores into graph memory, either directly or through a projector:

- `swingtradev3/context/knowledge/wiki`: stock/sector notes, scan history, wikilinks
- `swingtradev3/context/research`: dated scan outputs and per-stock research evidence
- `news_cache.json`, `sentiment_cache.json`: durable news/articles/entities/sentiment
- `trade_observations.json`, `observations.json`: lessons and event observations
- meaningful operational incidents from Postgres, projected as `FailurePattern` memory
- `SKILL.md` / strategy versions as `SkillVersion` nodes

Keep as file caches for now:

- `macro_cache.json`
- `options_cache.json`
- `timesfm_cache.json`
- `fundamentals_cache.json`
- `institutional_flows_cache.json`

When any cache value influences a research decision, persist a graph fact linked to the
`ResearchRun` node.

## Hard Invariant

If Memgraph is down, trading safety must still work.

The only acceptable degradation is less historical or research context. These outcomes are
not acceptable:

- cannot reconcile
- cannot place or flatten
- cannot enforce kill switches
- cannot recover positions

## Official Sources Checked

- Memgraph Docker Compose: https://memgraph.com/docs/getting-started/install-memgraph/docker-compose
- Memgraph configuration flags: https://memgraph.com/docs/database-management/configuration
- Python client: https://memgraph.com/docs/client-libraries/python
- Vector search: https://memgraph.com/docs/querying/vector-search
- MAGE algorithms: https://memgraph.com/docs/advanced-algorithms/available-algorithms
- Durability: https://memgraph.com/docs/fundamentals/data-durability
- Backup/restore: https://memgraph.com/docs/database-management/backup-and-restore
- JSON import: https://memgraph.com/docs/data-migration/json

