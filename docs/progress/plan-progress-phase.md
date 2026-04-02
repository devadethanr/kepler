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
| **Tavily (News)** | ✅ `tvly-dev-...` | ✅ WORKING |
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
- News: Tavily working (5 articles)
```

### Test Results
**Quick scan (10 stocks):**
- 360ONE: filtered
- ABB: filtered
- ACC: filtered
- APLAPOLLO: score 7.5
- AUBANK: score 7.5
- ADANIENSOL: score 7.5
- ADANIENT: filtered
- ADANIGREEN: filtered
- ADANIPORTS: filtered
- ADANIPOWER: score 7.5

**Estimated time for N200:** ~8.5 min

### What Needs Improvement
- Full N200 scan (costs NIM API calls)
- Morning briefing not tested
- Execution agent not tested

---

## Phase 3: Execution Operations ⚠️ PAPER TESTED

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

### Test Results
- ✅ Order placement in paper mode works
- ✅ Risk check passes (score 8.0 = 40% capital = 32 shares)
- ✅ Fill engine applies slippage
- ✅ GTT simulation works
- ⚠️ Live mode tested - code path works (verified Kite API call)
- ❌ Live order failed - markets closed (tried at 1:30 AM IST)

**Sample paper order:**
```
Ticker: SBIN
Quantity: 32
Entry: ₹1001 (slippage applied)
Stop: ₹980
Target: ₹1100
Position ID: pos-ceb6bf0a57
```

### Live Testing Notes
- To test live: change `config.yaml` `trading.mode: live`
- Must test during market hours (9:15-15:30 IST)
- Requires funds in Zerodha account
- Code path verified - actually calls Kite API

---

## Phase 4: Backtest Engine ✅ COMPLETED

### Design Requirement (from project_design.md)
- Historical replay engine
- Walk-forward validation
- Metrics and reporting
- QuantStats integration

### What's Implemented
- ✅ **Data fetcher** - Parquet caching with date filtering
- ✅ **Candle replay engine** - Daily candle replay with technical indicators
- ✅ **Walk-forward validation** - In-sample/out-of-sample testing (4 windows)
- ✅ **Metrics engine** - QuantStats integration with tearsheets

### Test Results
```
Backtest on 5 stocks (6 months):
- Trades: 9 (7 wins, 2 losses)
- Final Capital: ₹20,783 (from ₹20,000)
- Total Return: 4.0% | Win Rate: 77.8%
- Max Drawdown: 2.0% | Sharpe: 0.71
- Profit Factor: 5.6
- Status: PASSED ✅
```

### Future Work: Optuna Parameter Optimizer (SPIKE/TODO)
**What it does:**
- Automated parameter search using Bayesian optimization
- Tests 100+ combinations of: RSI length, EMA periods, stop multipliers, position sizing
- Finds optimal settings that maximize Sharpe ratio

**Status:** Structure exists (`backtest/optimizer.py`), needs implementation

**Value:** May improve returns by 10-25% with optimized parameters

**When to implement:** When you have 4-6 hours to run overnight optimization

**Estimated improvement:** 10-25% better risk-adjusted returns

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
- ⚠️ Telegram outbound (alerts) - WORKING
- ✅ Telegram inbound (approvals) - FIXED NOW
- ❌ Learning loop - NOT IMPLEMENTED

### What Was Fixed
**Telegram Bot Issues Fixed (March 2026):**
1. Message truncation - Added 4000 char limit to handle_command() for long /status responses
2. Inbound polling - Added TelegramInboundHandler to main.py to process commands
3. Deduplication - Added last_update_id tracking to prevent duplicate processing

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

## Telegram Notifications - IMPROVED ✅

New formatted messages with emojis and simple language:

**Entry Alert:**
```
🟢 State Bank of India (SBIN) - ENTRY FILLED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Quantity: 32 shares
💰 Entry: ₹1,001.00
🛡️ Stop Loss: ₹980.00
🎯 Target: ₹1,100.00
📈 Risk: ₹21.00 per share
```

**Profit Alert:**
```
💚 State Bank of India (SBIN) - TRADE CLOSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 32 shares @ ₹1,100.00
💵 P&L: ₹+3,200 (+10.0%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Reason: 🎯 Target Hit
📈 Entry was: ₹1,000.00
```

**Loss Alert:**
```
❤️ Tata Consultancy (TCS) - TRADE CLOSED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 10 shares @ ₹3,800.00
💵 P&L: ₹-2,000 (-5.0%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔔 Reason: 🛡️ Stop Loss
📈 Entry was: ₹4,000.00
```

**Approval Request:**
```
🔔 NEW TRADE SETUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 Reliance Industries (RELIANCE)
📊 Score: 8.5/10 | Pullback
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Entry Zone: ₹2,800 - ₹2,850
🛡️ Stop Loss: ₹2,700
🎯 Target: ₹3,100
⏰ Hold: ~15 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Why: Strong momentum...
```

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
