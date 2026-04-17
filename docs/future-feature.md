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

Implement a proper real-time updatable Knowledge Graph integrated with PostgreSQL with temporal query support.

### Current State

**Current "KG" in Kepler is NOT a real-time queryable knowledge graph.**

- Located at `context/knowledge/wiki/` — only LLM context files
- No graph structure, no temporal queries, no real-time updates

### Requirements

- Integrated with existing PostgreSQL (no new database)
- Real-time updatable embeddings
- Timestamps for temporal queries ("today", "last week", etc. for LLMs)
- Store: stocks, sectors, indices, news, trades, regimes, trade patterns, failures, lessons learned, SKILL.md content
- Open-source/free solution only
- No performance degradation on existing trading system

### Solution Options Reviewed

| Solution | Type | PostgreSQL Native | Auto-Refresh | Production Ready | Verdict |
|----------|------|-------------------|--------------|------------------|---------|
| **Kuzu** | Embedded | No | Manual | Yes | Separate DB |
| **pgraf** | Extension | Yes | Manual | Alpha (v1.0.0a2) | Too early |
| **Active Graph KG** | Extension | Yes | Yes | Yes | **Selected** |
| **Apache AGE + pgvector + Piggie** | Extension | Yes | Manual | Yes | Alternative |

### Recommendation

**Active Graph KG** (selected) for:

- Uses existing PostgreSQL infrastructure (no new DB)
- Auto-refresh embeddings (matches real-time requirement)
- Drift detection for stale knowledge
- Production-ready
- Supports timestamps for temporal queries

**Alternative**: Apache AGE + pgvector + Piggie for more control and benchmark-proven performance (12/12 vs Neo4j).

### KG Nodes to Implement

| Node Type | Description | Temporal |
|-----------|-------------|----------|
| `Stock` | Symbol, name, sector, market cap | Yes (last_updated) |
| `Sector` | Industry/sector classification | Yes (last_updated) |
| `Index` | Nifty 50/100/200, etc. | Yes (last_updated) |
| `News` | Article, source, timestamp | Yes (published_at) |
| `Trade` | Entry, exit, pnl, rationale | Yes (executed_at) |
| `Regime` | Market regime (bull/bear/sideways) | Yes (start_date) |
| `Pattern` | Chart/indicator pattern | Yes (identified_at) |
| `Failure` | Trade failure, cause, lesson | Yes (occurred_at) |
| `Lesson` | Learned insight, context | Yes (learned_at) |
| `Skill` | SKILL.md content | Yes (last_updated) |

### Temporal Query Examples

```sql
-- "What stocks did we trade today?"
MATCH (t:Trade)
WHERE t.executed_at >= CURRENT_DATE
RETURN t;

-- "What lessons from last week?"
MATCH (l:Lesson)
WHERE l.learned_at >= CURRENT_DATE - INTERVAL '7 days'
RETURN l;

-- "News affecting tech sector this week"
MATCH (n:News)-[:AFFECTS_SECTOR]->(s:Sector {name: "Technology"})
WHERE n.published_at >= CURRENT_DATE - INTERVAL '7 days'
RETURN n;
```

### Relevant Files

- `swingtradev3/context/knowledge/wiki/` — current "KG" (LlM context only)
- `swingtradev3/tools/market/news_search.py` — news integration
- `swingtradev3/agents/research/sentiment_agent.py` — sentiment integration
- `swingtradev3/data/universe_updater.py` — universe integration

---

## 5. Implementation Priority

### Phase 1: Quick Wins (Low Effort, High Impact)

1. **Universe Expansion**: Add Nifty 100, Midcap 150, Smallcap 250 URLs to `OFFICIAL_INDEX_PAGES`
2. **Operator News Analysis**: Build operator endpoint on existing sentiment agent

### Phase 2: Core Infrastructure (Medium Effort)

3. **Knowledge Graph**: Deploy Active Graph KG in PostgreSQL, define nodes, add temporal schema
4. **Web Crawler Integration**: Integrate Firecrawl for periodic + on-demand crawling

### Phase 3: Advanced Features (Higher Effort)

5. **Event-Driven Crawler**: Add threshold-based triggers
6. **KG Auto-Refresh**: Connect drift detection to research pipeline

---

## Constraints

- Open-source/free solutions only
- No performance degradation on existing trading system
- Must integrate with existing PostgreSQL infrastructure
- All timestamps must use `timestamptz` for temporal queries