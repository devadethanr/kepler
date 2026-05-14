What Is Working

  - Memgraph infra is up: memgraph, memgraph-lab, app, worker, dashboard are running.
  - Local links:
      - Dashboard: http://localhost:8502
      - API: http://localhost:8001
      - Memgraph Lab: http://localhost:3001
      - Bolt: localhost:7687
  - Runtime graph exists: 1328 nodes, 3800 edges.
  - Memgraph has ExecutionEvent, NewsArticle, Stock, ResearchRun, RegimeSnapshot.
  - Official Memgraph usage is broadly aligned: Docker profile, Bolt, neo4j Python driver, constraints/indexes.

  Major Findings

  - Deprecated file writes are still active. Research still writes context/research/**: swingtradev3/agents/research/pipeline.py:88. Markdown wiki still writes context/knowledge/wiki/**: swingtradev3/agents/research/
    knowledge_graph_agent.py:67. News/sentiment still write JSON caches: swingtradev3/data/news/core.py:42, swingtradev3/tools/analysis/sentiment_analysis.py:55.
  - Graph content is too thin. Runtime has 0 ResearchCandidate, Sector, Observation, TradeMemory, Lesson, FailurePattern, SkillVersion, SentimentSnapshot, TechnicalSnapshot, and FundamentalSnapshot nodes. Stock nodes have no sector or
    description. All 255 NewsArticle nodes have blank titles.
  - News-to-stock mapping is unreliable. The parser uses loose aliases like first company words, causing false mappings such as broad Tata headlines mapping to many Tata stocks, Reliance/Jio mapping to PIIND, etc. The graph then blindly
    creates AFFECTS_STOCK edges: swingtradev3/data/news/parsers.py:63, swingtradev3/context_graph/repository.py:532.
  - Dashboard graph is live but under-displaying data. Backend sends node properties, frontend expects metadata, so timestamps, confidence, tickers, summaries, and payload fields are mostly hidden: swingtradev3/context_graph/models.py:9,
    swingtradev3-dashboard/src/lib/schemas.ts:311.
  - Stock context endpoint returns research/news/observations, but frontend expects summary/evidence/connections, so selected-stock context can appear empty even when data exists: swingtradev3/context_graph/repository.py:1096,
    swingtradev3-dashboard/src/lib/schemas.ts:379.
  - Projector/schema has correctness bugs: OrderIntent, Approval, Position nodes are created but not in the graph label allowlist/schema; Position lacks id; real position materialization events are missed; timestamps are often ingest-time
    rather than event-time.
  - PolicyProposalWriter is broken: it calls repository methods that only exist on ContextBuilder, so it can raise AttributeError instead of degrading.
  - repository.py is too large: 1178 lines. This should become context_graph/repository/ modules before adding more logic.

  Checks Run

  - Read-only Memgraph queries via mgconsole.
  - API checks via Docker curl for /dashboard/knowledge/index, /dashboard/knowledge/graph, /dashboard/knowledge/stock/RELIANCE.
  - make lint failed with 185 Ruff errors, including Phase 11 files and a missing Generator import in tests/test_context_graph/conftest.py.
  - make test-file file=tests/test_api/test_phase8_dashboard.py: 8 passed, 1 failed. The failure is the news dashboard test not finding its inserted item in the live DB limited result set.

  What To Do Next

  1. Treat Phase 11 as incomplete until fixed.
  2. Refactor context_graph/repository.py into a package.
  3. Fix graph schema/labels/edges and metadata invariants.
  4. Stop new writes to deprecated research/wiki/news/sentiment/observation JSON paths.
  5. Replace ScorerAgent wiki reads with ContextBuilder.
  6. Fix news identity: canonical stock metadata, strict aliases, verified_tickers vs mentioned_tickers.
  7. Make research write full ResearchRun and ResearchCandidate graph nodes, with sectors, stock metadata, technical/fundamental/sentiment links.
  8. Fix dashboard API/frontend payload contracts.
  9. Make Memgraph tests non-destructive by default; keep destructive wipe behind an explicit target.
  10. Then run targeted tests, make lint, and full make test.

  Sources checked: Memgraph Docker Compose docs, Python client docs, constraints docs, and indexes docs from memgraph.com.
