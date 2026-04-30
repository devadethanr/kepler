
My Read
  Do not “rework the entire storage and memory system” into Memgraph. That would be dangerous.

  Do rework the context/knowledge layer into a proper graph memory system, with Memgraph as the leading candidate.

  The correct split is:

  Postgres = execution truth
  Memgraph = context / research / learning graph
  Files = temporary caches + compatibility exports only

  Postgres must remain authoritative for:
  positions, orders, fills, approvals, trades, protective_triggers, operator_controls, failure_incidents, policy_overlays, auth/session state.

  Memgraph should own:
  research memory, stock/sector relationships, news/entity links, lessons, trade-pattern memory, failure-pattern context, skill/version memory, and GraphRAG retrieval.

  Why
  The current repo already has Postgres execution truth in swingtradev3/memory/models.py:23, compatibility projections in swingtradev3/memory/projections.py:26, and a file-backed “KG” in swingtradev3/knowledge/wiki_renderer.py:36.

  But the current KG is not a real temporal/queryable graph. It writes markdown and _graph.json style render data. The future-feature doc correctly identifies this gap in docs/future-feature.md:141.

  Feasibility
  Memgraph is feasible and probably stronger than the “Active Graph KG” idea for this use case, if we accept one tradeoff: it is a new database service.

  Good fit:

  - real property graph with Cypher
  - Docker Compose support with memgraph/memgraph-mage + memgraph/lab
  - Python access through Neo4j driver over Bolt
  - MAGE graph algorithms
  - native text and vector search
  - useful Lab UI for graph debugging

  Concern:

  - it violates the old “no new DB” preference in docs/future-feature.md:152
  - it adds backup, durability, auth, memory-limit, and versioning work
  - it must never enter the execution hot path

  Official sources checked:

  - Memgraph Docker Compose: https://memgraph.com/docs/getting-started/install-memgraph/docker-compose
  - Python client: https://memgraph.com/docs/client-libraries/python
  - Vector search: https://memgraph.com/docs/querying/vector-search
  - Algorithms/MAGE: https://memgraph.com/docs/advanced-algorithms/available-algorithms
  - Durability: https://memgraph.com/docs/fundamentals/data-durability
  - Backup/restore: https://memgraph.com/docs/database-management/backup-and-restore
  - JSON import: https://memgraph.com/docs/data-migration/json

  What Should Move
  Move these into graph memory, either directly or via projector:

  - swingtradev3/context/knowledge/wiki: stock/sector notes, scan history, wikilinks
  - swingtradev3/context/research: dated scan outputs and per-stock research evidence
  - news_cache.json, sentiment_cache.json: durable news/articles/entities/sentiment
  - trade_observations.json, observations.json: lessons and event observations
  - meaningful operational incidents from Postgres, projected as failure-pattern memory
  - SKILL.md / strategy versions as SkillVersion or Rule nodes

  Keep as file cache for now:

  - macro_cache.json
  - options_cache.json
  - timesfm_cache.json
  - fundamentals_cache.json
  - institutional_flows_cache.json

  But when any of those values influence a research decision, persist a graph fact linked to that research run.

  Graph Shape
  Core nodes:
  Stock, Sector, Index, ResearchRun, ResearchCandidate, NewsArticle, SignalSnapshot, TechnicalSnapshot, FundamentalSnapshot, SentimentSnapshot, RegimeSnapshot, TradeMemory, FailurePattern, Observation, Lesson, SkillVersion.

  Core edges:
  MEMBER_OF, BELONGS_TO_SECTOR, ANALYZED_IN, HAS_SIGNAL, MENTIONS, AFFECTS_STOCK, UNDER_REGIME, GENERATED_INTENT, EXECUTED_AS, CLOSED_AS, PRODUCED_OBSERVATION, SUPPORTS_LESSON, SIMILAR_TO, FAILED_DURING.

  Every node/edge should carry:
  source, source_id, source_path or postgres_table/postgres_pk, observed_at, ingested_at, payload_hash, confidence, projection_version.

  Phase Placement
  Do not put this inside canonical Phase 8.

  Phase 8 should stay dashboard/API/projection migration.

  This should become a separate phase, probably:

  Phase 14: Context Graph Memory

  or a clearly named parallel track:

  Memory Graph Track 0-3

  Reason: Phase 8 is part of the execution-safe floor. Memgraph is cognition/memory infrastructure. Mixing them will slow down Phase 8 and increase risk.

  Recommended Direction
  Adopt Memgraph, but only as a projected context graph.

  Implementation path:

  1. Finish Phase 8 read-side migration first.
  2. Add Memgraph services behind an optional Docker Compose profile.
  3. Add swingtradev3/context_graph/ with a typed repository and projector.
  4. Import current markdown KG and research JSON into Memgraph idempotently.
  5. Project selected Postgres execution rows into graph memory.
  6. Preserve existing dashboard KG API shape, but later back it with Memgraph.
  7. Make Slow Brain read from Memgraph through typed methods only.
  8. Keep worker/fast execution completely independent of Memgraph.

  Hard Invariant
  If Memgraph is down, trading safety must still work.

  The only acceptable degradation is:
  “less historical/research context available.”

  Not:
  “cannot reconcile”
  “cannot place/flatten”
  “cannot enforce kill switches”
  “cannot recover positions”

  That boundary is non-negotiable.


==========================================================


We need both because they solve different problems.

  Postgres is for truth and transactions.
  Memgraph is for context, relationships, retrieval, and reasoning.

  Trying to make one do both will either make execution unsafe or make memory/reasoning weak.

  1. Why Separate Postgres And Memgraph
  Postgres is excellent when the system needs strict correctness:

  - one order intent should not be submitted twice
  - a position must have one current lifecycle state
  - a kill switch must be reliable
  - approvals must be auditable
  - trades/fills must reconcile exactly
  - worker locks and transactions must be deterministic

  Memgraph is excellent when the system needs relationship traversal:

  - “show me stocks similar to past winners in this regime”
  - “what news themes affected this sector recently?”
  - “which failure patterns repeat across trades?”
  - “which lessons apply to this candidate?”
  - “connect this stock to sector, pattern, regime, sentiment, past trades, and outcomes”

  Those are graph questions. They are awkward in SQL and natural in a graph DB.

  So:

  - Postgres protects money.
  - Memgraph improves memory and reasoning.

  2. What Each Handles
  Postgres handles execution-critical state:

  - entry_intents
  - approvals
  - order_intents
  - broker_orders
  - broker_fills
  - positions
  - protective_triggers
  - trades
  - operator_controls
  - failure_incidents
  - reconciliation_runs
  - auth_sessions
  - policy_overlays

  Memgraph handles context/cognition state:

  - Stock
  - Sector
  - Index
  - ResearchRun
  - ResearchCandidate
  - NewsArticle
  - RegimeSnapshot
  - SignalSnapshot
  - Pattern
  - TradeMemory
  - Observation
  - Lesson
  - FailurePattern
  - SkillVersion
  - relationships like AFFECTS, BELONGS_TO, SIMILAR_TO, UNDER_REGIME, SUPPORTED_BY, FAILED_BECAUSE_OF

  No .md / .json source of truth needed. Files can be removed as primary memory.

  3. How Each Is Consumed
  Postgres consumers:

  - worker
  - reconciler
  - execution coordinator
  - risk checks
  - operator controls
  - dashboard execution panels
  - API execution/read endpoints
  - phase checks

  These consumers need exact state.

  Memgraph consumers:

  - Slow Brain agents
  - research/scoring context builder
  - post-trade reviewer
  - exception analyst later
  - dashboard knowledge graph view
  - operator research tools
  - GraphRAG/context retrieval

  These consumers need connected memory, similarity, temporal relationships, and explanations.

  Important rule:
  The worker does not read Memgraph before placing/modifying/canceling orders.

  4. No File-Based System
  Agreed.

  Target state should be:

  - no .md as memory source
  - no .json as memory source
  - no context/research/*.json as canonical research memory
  - no _graph.json dashboard graph source
  - no state.json, trades.json, pending_approvals.json as runtime source

  Instead:

  - Postgres stores execution truth.
  - Memgraph stores context graph truth.
  - Files are either deleted, ignored, or optional debug exports only.

  Since this is development, we do not need to migrate old data. Cleaner path:

  1. stop writing new memory to files
  2. introduce DB-backed writers
  3. let old context files die
  4. start fresh with graph memory

  5. How Postgres And Memgraph Connect
  They should connect through a one-way projector, not direct shared writes.

  Flow:

  Research / agents / market data
          |
          v
  Postgres execution truth       Memgraph context truth
          |                              ^
          |                              |
          +---- graph projector ---------+

  More concretely:

  1. Execution event happens.
     Example: order filled, trade closed, incident opened.

  - worker writes canonical row/event to Postgres
  - graph projector reads the Postgres event
  - graph projector writes derived memory node/edge to Memgraph

  2. Research event happens.
     Example: scanner analyzes TCS.

  - research pipeline writes ResearchRun / candidate summary to Memgraph
  - if candidate becomes actionable, it writes structured entry_intent to Postgres
  - execution then proceeds only from Postgres

  3. Learning event happens.
     Example: post-trade reviewer identifies lesson.

  - lesson goes to Memgraph
  - if it proposes policy change, proposal goes to Postgres as policy_overlay candidate
  - policy governor must approve/apply from Postgres

  Connection Points
  Use these controlled bridges:

  - GraphProjector
    Reads Postgres execution events and writes Memgraph context.
  - ContextGraphRepository
    Typed Memgraph access layer. No raw Cypher scattered across agents.
  - ContextBuilder
    Reads Memgraph for agent prompts/research context.
  - IntentWriter
    Converts approved research output into Postgres entry_intents.
  - PolicyProposalWriter
    Converts graph/learning insight into Postgres policy proposal, not direct config mutation.

  6. Critical Directionality
  Allowed:

  Postgres -> Memgraph
  Memgraph -> research context
  Memgraph -> entry intent proposal -> Postgres
  Memgraph -> policy proposal -> Postgres

  Not allowed:

  Memgraph -> live order decision
  Memgraph -> direct position mutation
  Memgraph -> direct kill-switch mutation
  Memgraph -> direct config mutation

  Plain English:
  Memgraph can suggest. Postgres decides. Worker executes.
