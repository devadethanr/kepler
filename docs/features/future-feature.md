# Kepler Future Features

Planned feature extensions for the Kepler autonomous trading system.

## Table of Contents

1. [Custom Web Crawler](#1-custom-web-crawler)
2. [Operator News Analysis](#2-operator-news-analysis)
3. [Universe Expansion](#3-universe-expansion)
4. [Knowledge Graph](#4-knowledge-graph)
5. [Implementation Priority](#5-implementation-priority)

---

## 1. Custom Web Crawler

### Feature Summary

Add a custom web crawler for fetching latest financial/business news with three trigger modes:

- **Periodic**: Scheduled runs (e.g., every 15 minutes during market hours)
- **On-demand**: Manual trigger via operator command
- **Event-driven**: Triggered by specific market events or threshold breaches

### Requirements

- Open-source/free solution only
- No performance degradation on existing trading system
- Support for Indian market news sources (NSE, BSE, economic times, moneycontrol, etc.)
- LLM-ready output format for downstream processing

### Solution Options

| Tool | Type | Pros | Cons |
|------|------|-----|------|
| **Firecrawl** | Managed API | Already in dependencies, robust | Rate limits, paid tier |
| **Crawl4AI** | Self-hosted | Open source, local LLM-ready | Requires hosting |
| **Scrapy** | Framework | Full control, free | More boilerplate |

### Recommendation

**Firecrawl** is already in dependencies. Use for initial implementation. Consider **Crawl4AI** for local deployment if needed.

### Relevant Files

- `swingtradev3/tools/market/news_search.py` — existing news search to integrate with
- `swingtradev3/agents/research/sentiment_agent.py` — for sentiment analysis integration

---

## 2. Operator News Analysis

### Feature Summary

Add operator-side feature to analyze news text/URLs and auto-queue related stocks for research:

1. Operator pastes/uploads news article or URL
2. System extracts key entities (companies, sectors, keywords)
3. System matches entities to universe stocks
4. Auto-queue matched stocks for research sentiment analysis
5. Present findings back to operator with Buy/Hold/Sell signals

### Requirements

- Support text paste and URL input
- Named entity recognition for Indian stock symbols
- Seamless integration with existing research pipeline
- Operator-friendly UI (dashboard or CLI)

### Solution Options

- Use existing LLM for entity extraction + pattern matching
- Integrate with `sentiment_agent.py` for sentiment scoring
- Query existing universe data for entity matching

### Recommendation

Build on existing `sentiment_agent.py` with a new operator endpoint. Use LLM for NER, match against universe via existing loaders.

### Relevant Files

- `swingtradev3/tools/market/news_search.py` — news fetching
- `swingtradev3/agents/research/sentiment_agent.py` — sentiment analysis
- `swingtradev3/data/nifty200_loader.py` — universe matching
- `swingtradev3/data/universe_updater.py` — universe management

---

## 3. Universe Expansion

### Feature Summary

Expand stock universe from current coverage to all Indian indices:

- **Current**: Nifty 50
- **Target**: Nifty 50, Nifty 100, Nifty 200, Nifty Midcap 150, Nifty Smallcap 250

### Existing Infrastructure

The `data/universe_updater.py` already supports adding new indices via the `OFFICIAL_INDEX_PAGES` dictionary:

```python
OFFICIAL_INDEX_PAGES = {
    "nifty50": "https://www.nseindia.com/...",
    "nifty200": "https://www.nseindia.com/...",
    # Add: nifty100, midcap150, smallcap250
}
```

Existing loaders:

- `Nifty200Loader` — already implemented
- `Nifty50Loader` — already implemented

### Required Additions

| Index | URL to Add | Loader |
|-------|------------|--------|
| Nifty 100 | Add to `OFFICIAL_INDEX_PAGES` | Reuse `Nifty200Loader` |
| Midcap 150 | Add to `OFFICIAL_INDEX_PAGES` | Reuse `Nifty200Loader` |
| Smallcap 250 | Add to `OFFICIAL_INDEX_PAGES` | Reuse `Nifty200Loader` |

### Implementation Steps

1. Add URLs for new indices to `OFFICIAL_INDEX_PAGES`
2. Run universe update to fetch new stocks
3. Add new stocks to watchlist
4. Ensure no performance degradation with expanded universe

### Relevant Files

- `swingtradev3/data/universe_updater.py` — for adding new universes
- `swingtradev3/data/nifty200_loader.py` — universe loader

---

## 4. Knowledge Graph

### Feature Summary

Implement the Phase 11 Memgraph context graph for real-time queryable research,
relationship, and learning memory. Postgres remains execution truth.

### Current State

**Current "KG" in Kepler is not a real-time queryable graph.**

- Located at `context/knowledge/wiki/`, primarily as LLM context files
- Related JSON files are caches or compatibility exports, not graph storage
- No durable graph traversal layer, temporal graph query layer, or GraphRAG retrieval surface

### Decision

Use Memgraph for context graph memory:

- official open-source Docker image: `memgraph/memgraph-mage:latest`
- dev graph UI: `memgraph/lab:latest`
- Compose profile: `memory`
- started by `make dev` and `make dev-detach`
- backup/restore runbook: `docs/runbooks/memgraph-backup-restore.md`

The older Postgres-only graph preference is superseded. The safety requirement is now a
clear split:

```text
Postgres = execution truth
Memgraph = context graph truth
Files    = temporary caches and compatibility exports only
```

### Requirements

- Open-source/free solution only
- No performance degradation on the trading hot path
- No worker dependency on Memgraph
- Timestamps for temporal graph queries ("today", "last week", etc. for LLMs)
- Store stocks, sectors, indices, news, regimes, signals, research runs, trade memories,
  failures, lessons learned, and strategy/skill versions
- Persist source, source id, observed time, ingestion time, payload hash, confidence, and
  projection version on graph facts

### Graph Nodes To Implement

| Node Type | Description | Temporal |
|-----------|-------------|----------|
| `Stock` | Symbol, name, sector, market cap | Yes (`observed_at`) |
| `Sector` | Industry/sector classification | Yes (`observed_at`) |
| `Index` | Nifty 50/100/200, etc. | Yes (`observed_at`) |
| `ResearchRun` | Research batch/session | Yes (`started_at`) |
| `ResearchCandidate` | Candidate evidence summary | Yes (`observed_at`) |
| `NewsArticle` | Article, source, entity links | Yes (`published_at`) |
| `RegimeSnapshot` | Market regime state | Yes (`observed_at`) |
| `SignalSnapshot` | Technical/fundamental/sentiment signal | Yes (`observed_at`) |
| `TradeMemory` | Executed trade outcome context | Yes (`executed_at`) |
| `FailurePattern` | Repeated failure cause/context | Yes (`observed_at`) |
| `Lesson` | Learned insight and applicability | Yes (`learned_at`) |
| `SkillVersion` | Strategy/SKILL.md version metadata | Yes (`last_updated`) |

### Temporal Query Examples

```cypher
MATCH (t:TradeMemory)
WHERE t.executed_at >= date()
RETURN t;

MATCH (l:Lesson)
WHERE l.learned_at >= date() - duration({days: 7})
RETURN l;

MATCH (n:NewsArticle)-[:AFFECTS_STOCK]->(s:Stock)-[:BELONGS_TO_SECTOR]->(:Sector {name: "Technology"})
WHERE n.published_at >= date() - duration({days: 7})
RETURN n, s;
```

### Relevant Files

- `docs/features/postgress-memgraph.md` - architecture decision
- `docs/runbooks/memgraph-backup-restore.md` - dev backup/restore
- `docker-compose.dev.yml` - Memgraph and Lab services under the `memory` profile
- `swingtradev3/Makefile` - dev, logs, console, and snapshot targets
- `swingtradev3/context/knowledge/wiki/` - current file-backed memory to retire
- `swingtradev3/tools/market/news_search.py` - future news integration
- `swingtradev3/agents/research/sentiment_agent.py` - future sentiment integration
- `swingtradev3/data/universe_updater.py` - future universe integration

---

## 5. Implementation Priority

### Phase 1: Quick Wins (Low Effort, High Impact)

1. **Universe Expansion**: Add Nifty 100, Midcap 150, Smallcap 250 URLs to `OFFICIAL_INDEX_PAGES`
2. **Operator News Analysis**: Build operator endpoint on existing sentiment agent

### Phase 2: Core Infrastructure (Medium Effort)

3. **Knowledge Graph**: Deploy the Memgraph `memory` profile, define graph nodes/edges, add temporal context schema
4. **Web Crawler Integration**: Integrate Firecrawl for periodic + on-demand crawling

### Phase 3: Advanced Features (Higher Effort)

5. **Event-Driven Crawler**: Add threshold-based triggers
6. **Context Graph Projector**: Connect research, execution-event projection, and post-trade learning to Memgraph

---

## Constraints

- Open-source/free solutions only
- No performance degradation on existing trading system
- Postgres remains execution truth; Memgraph remains context graph truth
- File-backed knowledge and research stores must not become new sources of truth
- All Postgres timestamps must use `timestamptz`; graph facts must include explicit temporal properties
