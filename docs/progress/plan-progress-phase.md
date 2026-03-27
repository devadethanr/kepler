# Plan Progress By Phase

This file tracks the implementation phases for `swingtradev3` based on `swingtradev3_design_v6.pdf`.

## Phase List

1. Phase 1: live broker integration ✅
2. Phase 2: LLM-driven research pipeline ⚠️ (API keys missing)
3. Phase 3: execution operations ⚠️ (not tested with live orders)
4. Phase 4: backtest engine and metrics ❌
5. Phase 5: Telegram integration and learning loop ❌
6. Phase 6: end-to-end Docker validation ⚠️

---

## Current API Key Status

| Service | Configured | Working |
|---------|-----------|--------|
| **Zerodha Kite (Paid)** | ✅ `m0q3d9nvg75ug0zg` | ✅ LTP, Historical, Quote WORKING |
| **NVIDIA NIM** | ✅ `nvapi-dZsJ...` | ✅ `meta/llama-3.1-70b-instruct` WORKING |
| **Tavily (News)** | ❌ `TAVILY_API_KEY=` | ⚠️ DDGS fallback works |
| **Firecrawl (Fundamentals)** | ❌ `FIRECRAWL_API_KEY=` | ❌ NOT WORKING |
| **Groq (LLM Fallback)** | ❌ `GROQ_API_KEY=` | ❌ NOT WORKING |
| **Gemini (LLM Fallback)** | ❌ `GEMINI_API_KEY=` | ❌ NOT WORKING |
| **Claude (LLM Fallback)** | ❌ `ANTHROPIC_API_KEY=` | ❌ NOT WORKING |
| **Telegram Bot** | ✅ Configured | ⚠️ Outbound only |

> Note: NIM model changed to `meta/llama-3.1-70b-instruct` (Kimi K2.5 timed out). Streaming support added to `nim_client.py`.

---

## Phase 1: Live Broker Integration ✅ COMPLETED

### What Works
- Direct Kite API with paid subscription
- LTP fetching
- Historical data fetching
- Quote fetching
- KiteFetcher for N50/N200
- MCP fallback for instrument search

### Tests Added
- `test_live_data_endpoints.py` - 8 passed

### Code Fixes
- `data/kite_fetcher.py` - Allow direct Kite in paper mode

---

## Phase 2: LLM-Driven Research Pipeline ✅ WORKING

### Design Requirement (from project_design.md)
The research agent uses NIM to analyze stocks:
1. Fetch market data (Kite) → 2. Fetch fundamentals → 3. Fetch news → 4. Call NIM with SKILL.md → 5. Get score/decision

### What's Working
- ✅ NIM client with streaming support (`llm/nim_client.py`)
- ✅ Model config-driven (`config.yaml`: `meta/llama-3.1-70b-instruct`)
- ✅ News search with DDGS fallback
- ✅ Research agent - Tested on SBIN, got score 8.5
- ✅ Tool executor with setup_type normalization (`llm/tool_executor.py`)
- ✅ Kite data fetching in paper mode

### Test Result
```
Research on SBIN:
- Score: 8.5
- Setup: pullback
- Entry zone: 1000-1020
- Stop: 980
- Target: 1100
- Confidence: "strong bull structure above 200 EMA, pullback to 50 EMA"
```

### What Needs Improvement
- Tavily API key missing (using DDGS fallback) - optional
- Full N200 scan not tested yet
- Morning briefing not tested

---

## Phase 3: Execution Operations ❌ NOT FULLY TESTED

### Design Requirement (from project_design.md)
- Live order placement via Kite
- GTT placement, modification, deletion
- Trailing stops
- Reconciliation

### What's Implemented
- ✅ Order execution code exists
- ✅ GTT manager code exists
- ✅ Trailing stop logic exists
- ✅ Reconciler exists
- ❌ **NOT TESTED** - Live order placement not tested with real money

### What Needs to Be Done
- [ ] Test live order placement (change to `live` mode in config)
- [ ] Test GTT placement with real broker
- [ ] Test GTT modification (trailing stops)
- [ ] Test GTT deletion

---

## Phase 4: Backtest Engine ❌ NOT STARTED

### Design Requirement (from project_design.md)
- Historical replay engine
- Walk-forward validation
- Metrics and reporting
- QuantStats integration

### What's Implemented
- ❌ Nothing significant

### What Needs to Be Done
- [ ] Implement `backtest/data_fetcher.py` - Chunk historical data with parquet cache
- [ ] Implement `backtest/candle_replay.py` - Daily candle replay
- [ ] Implement `backtest/walk_forward.py` - In-sample/out-of-sample validation
- [ ] Implement `backtest/metrics.py` - QuantStats tearsheets
- [ ] Implement `backtest/optimizer.py` - Optuna parameter search

---

## Phase 5: Telegram Integration & Learning Loop ❌ NOT IMPLEMENTED

### Design Requirement (from project_design.md)
- Two-way Telegram communication
- YES/NO approval flow
- Daily briefing
- Trade review
- Stats engine
- Lesson generation
- SKILL.md updates

### What's Implemented
- ⚠️ Telegram outbound (alerts) - PARTIAL
- ❌ Telegram inbound (approvals) - NOT IMPLEMENTED
- ❌ Learning loop - NOT IMPLEMENTED

### What Needs to Be Done
**Telegram:**
- [ ] Implement inbound message handler
- [ ] Parse YES/NO commands from users
- [ ] Connect to pending_approvals flow

**Learning:**
- [ ] Implement `learning/trade_reviewer.py` - Event-driven trade logging
- [ ] Implement `learning/stats_engine.py` - Monthly stats
- [ ] Implement `learning/lesson_generator.py` - NIM proposes SKILL changes
- [ ] Implement `learning/skill_updater.py` - Git commit SKILL updates

---

## Phase 6: End-To-End Docker Validation ⚠️ PARTIAL

### What's Done
- ✅ Docker containerization exists
- ✅ Basic tests pass (61 passed)
- ❌ Full E2E not validated

### What Needs to Be Done
- [ ] Full paper-mode E2E test
- [ ] Full live-mode E2E test (dry run)
- [ ] MCP fallback E2E test

---

## Summary: What Must Be Done First

### PRIORITY 1: Add API Keys

```bash
# Edit swingtradev3/.env and add:

# NVIDIA NIM (REQUIRED for research)
NIM_API_KEY=nvapi-xxxxx

# News Search (REQUIRED for research)
TAVILY_API_KEY=tvly-xxxxx

# Optional - Fallback LLMs
GROQ_API_KEY=gsk_xxxxx
GEMINI_API_KEY=AIzaxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### PRIORITY 2: Validate Phase 2 (Research with NIM)
- Run research agent manually
- Verify NIM returns scores
- Verify briefing generates

### PRIORITY 3: Test Phase 3 (Live Orders)
- Switch to `live` mode
- Place test order (small qty)
- Verify GTT works

---

## Current Test Status

```
Total: 61 passed, 1 skipped
- test_live_data_endpoints.py: 8 passed, 1 skipped
- test_research_agent.py: multiple passed
- test_execution_agent.py: multiple passed
- test_reconciler.py: 6 passed
- Other tests: passed
```

---

*Last Updated: March 28, 2026*
