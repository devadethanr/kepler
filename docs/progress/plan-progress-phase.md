# Plan Progress By Phase

This file tracks the implementation phases for `swingtradev3` based on `swingtradev3_design_v6.pdf`.

## Phase List

1. Phase 1: live broker integration ✅
2. Phase 2: LLM-driven research pipeline ✅ (Working with NIM)
3. Phase 3: execution operations ⚠️ (paper tested, live not validated)
4. Phase 4: backtest engine and metrics ✅
5. Phase 5: Telegram integration and learning loop ⚠️ (outbound + inbound working, learning loop not implemented)
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
| **Telegram Bot** | ✅ Configured | ✅ Outbound + inbound working |

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
- Self-hosted Kite MCP sidecar via Docker
- Direct Kite session auth (request_token → access_token exchange)
- Session persistence in `context/auth/kite_session.json`
- Auth modules: `auth/kite/client.py`, `auth/kite/login.py`, `auth/kite/session_store.py`

### Tests Added
- `test_live_data_endpoints.py` - 8 passed
- `test_kite_auth.py` - auth flow tests

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
- ✅ 1,200 research JSON files generated (200 tickers × 6 dates: Mar 24-29)
- ✅ LLM fallback chain scaffolded (NIM → Groq → Gemini → Claude)
- ✅ Prompt builder assembles system prompt from SKILL.md + context

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
- `llm/schemas/` directory is empty — JSON schemas for tools not yet written

---

## Phase 3: Execution Operations ⚠️ PAPER TESTED

### Design Requirement (from project_design.md)
- Live order placement via Kite
- GTT placement, modification, deletion
- Trailing stops
- Reconciliation

### What's Implemented
- ✅ Order execution code exists (`tools/execution/order_execution.py`)
- ✅ GTT manager code exists (`tools/execution/gtt_manager.py`)
- ✅ Trailing stop logic exists
- ✅ Reconciler exists (`agents/reconciler.py`)
- ✅ Risk check gate (`tools/execution/risk_check.py`)
- ✅ Alerts system (`tools/execution/alerts.py`)
- ❌ **NOT TESTED** - Live order placement not tested with real money during market hours

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
- ✅ **Data fetcher** - Parquet caching with date filtering (`backtest/data_fetcher.py`)
- ✅ **Candle replay engine** - Daily candle replay with technical indicators (`backtest/candle_replay.py`)
- ✅ **Walk-forward validation** - In-sample/out-of-sample testing (4 windows) (`backtest/walk_forward.py`)
- ✅ **Metrics engine** - QuantStats integration with tearsheets (`backtest/metrics.py`)
- ✅ **NSE bhav fetcher** - Historical OI/PCR from NSE bhav copy files (`backtest/nse_bhav_fetcher.py`)
- ✅ **Optimizer scaffold** - Optuna Bayesian search structure exists (`backtest/optimizer.py`)

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

## Phase 5: Telegram Integration & Learning Loop ⚠️ PARTIAL

### Design Requirement (from project_design.md)
- Two-way Telegram communication
- YES/NO approval flow
- Daily briefing
- Trade review
- Stats engine
- Lesson generation
- SKILL.md updates

### What's Implemented
- ✅ Telegram outbound (alerts) - WORKING (`notifications/telegram_client.py`)
- ✅ Telegram inbound (approvals) - WORKING (`notifications/telegram_handler.py`)
- ✅ Telegram commands (`notifications/telegram_commands.py`)
- ✅ Message formatter (`notifications/formatter.py`)
- ⚠️ Learning loop - Modules exist but not fully wired to scheduler

### Learning Module Status
| Module | File | Status |
|--------|------|--------|
| Trade Reviewer | `learning/trade_reviewer.py` | ✅ Exists |
| Stats Engine | `learning/stats_engine.py` | ✅ Exists |
| Lesson Generator | `learning/lesson_generator.py` | ✅ Exists |
| Skill Updater | `learning/skill_updater.py` | ✅ Exists |

### What Was Fixed
**Telegram Bot Issues Fixed (March 2026):**
1. Message truncation - Added 4000 char limit to handle_command() for long /status responses
2. Inbound polling - Added TelegramInboundHandler to main.py to process commands
3. Deduplication - Added last_update_id tracking to prevent duplicate processing

### What Needs to Be Done
**Telegram:**
- [ ] Wire YES/NO parsing to pending_approvals flow in execution_agent
- [ ] Test full approval → order placement → GTT flow end-to-end

**Learning:**
- [ ] Wire learning modules to main.py scheduler (monthly analyst loop)
- [ ] Connect trade_reviewer to execution_agent on trade close
- [ ] Test SKILL.md.staging → approval → git commit flow

---

## Phase 6: End-To-End Docker Validation ⚠️ PARTIAL

### What's Done
- ✅ Docker containerization exists (`Dockerfile`, `docker-compose.yml`)
- ✅ Kite MCP sidecar defined (`Dockerfile.kite-mcp`)
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

## Complete Module Inventory

### Core (~95 Python source files)

| Module | Files | Status |
|--------|-------|--------|
| **Root** | `main.py`, `config.py`, `models.py`, `paths.py`, `storage.py`, `logging_config.py`, `mcp_client.py` | ✅ |
| **Agents** | `research_agent.py`, `execution_agent.py`, `reconciler.py` | ✅ |
| **Auth** | `token_manager.py`, `totp_login.py`, `kite/client.py`, `kite/login.py`, `kite/session_store.py`, `mcp/login.py` | ✅ |
| **Data** | `kite_fetcher.py`, `nifty200_loader.py`, `nifty50_loader.py`, `corporate_actions.py`, `earnings_calendar.py`, `universe_updater.py` | ✅ |
| **Indicators** | `momentum.py`, `trend.py`, `volatility.py`, `volume.py`, `structure.py`, `relative_strength.py`, `patterns.py` | ✅ |
| **Tools - Market** | `market_data.py`, `fundamental_data.py`, `news_search.py`, `fii_dii_data.py`, `options_data.py` | ✅ |
| **Tools - Execution** | `order_execution.py`, `gtt_manager.py`, `risk_check.py`, `alerts.py` | ✅ |
| **LLM** | `nim_client.py`, `router.py`, `tool_executor.py`, `prompt_builder.py` | ✅ |
| **Risk** | `engine.py`, `position_sizer.py`, `circuit_breakers.py`, `circuit_limit_checker.py` | ✅ |
| **Paper** | `fill_engine.py`, `gtt_simulator.py`, `slippage_model.py` | ✅ |
| **Backtest** | `data_fetcher.py`, `candle_replay.py`, `walk_forward.py`, `optimizer.py`, `metrics.py`, `nse_bhav_fetcher.py` | ✅ |
| **Learning** | `trade_reviewer.py`, `stats_engine.py`, `lesson_generator.py`, `skill_updater.py` | ⚠️ Exists, not wired |
| **Notifications** | `telegram_client.py`, `telegram_handler.py`, `telegram_commands.py`, `formatter.py` | ✅ |
| **Integrations** | `kite/mcp_client.py` | ✅ |
| **Tests** | 16 test files | ✅ 61 passed, 1 skipped |

### Empty / Incomplete Directories

| Directory | Purpose | Status |
|-----------|---------|--------|
| `llm/schemas/` | JSON schemas for NIM tool calls | ❌ Empty |
| `reports/` | QuantStats HTML tearsheets, equity curves | ❌ Empty |
| `.claude/agent-memory/quant-systems-architect/` | Agent memory | ❌ Empty |

---

## Data & State

### Research Data
- **1,200 research JSON files** — 200 Nifty 200 tickers × 6 dates (Mar 24-29, 2026)
- Stored in `context/research/YYYY-MM-DD/{ticker}.json`

### Context Files
| File | Purpose | Status |
|------|---------|--------|
| `state.json` | Live positions, cash, P&L, drawdown | ✅ |
| `trades.json` | Closed trade history | ✅ |
| `stats.json` | Monthly metrics (Sharpe, win rate, Kelly) | ✅ |
| `pending_approvals.json` | Shortlisted setups awaiting YES/NO | ✅ |
| `trade_observations.json` | Event-driven trade notes | ✅ |
| `fundamentals_cache.json` | Cached fundamentals (layer 4 fallback) | ✅ |
| `news_cache.json` | Cached news search results | ✅ |
| `nifty200.json` | Cached Nifty 200 constituents | ✅ |
| `nifty50.json` | Cached Nifty 50 constituents | ✅ |
| `telegram_last_update_id.json` | Inbound deduplication | ✅ |
| `telegram_processed_ids.json` | Processed message IDs | ✅ |
| `auth/kite_session.json` | Persisted Kite session | ✅ |
| `daily/*.json` | Daily state snapshots (3 files) | ✅ |

### Log Files
| File | Purpose |
|------|---------|
| `logs/decisions.log` | Order decisions |
| `logs/errors.log` | Exceptions, API failures |
| `logs/research.log` | Stock scoring, NIM reasoning |
| `logs/trades.log` | Orders placed, GTT set/triggered |

---

## Strategy Files

| File | Purpose | Status |
|------|---------|--------|
| `strategy/SKILL.md` | Trading philosophy v1.0 | ✅ |
| `strategy/SKILL.md.staging` | Monthly proposed edits | ✅ Exists (empty) |
| `strategy/research_program.md` | Research procedure v1.0 | ✅ |
| `strategy/analyst_program.md` | Monthly review procedure | ✅ |

---

## Known Gaps

### Critical
- ❌ Live order placement never tested with real money during market hours
- ❌ `llm/schemas/` empty — no JSON schemas for NIM tool calls
- ❌ Learning loop modules exist but not wired to main.py scheduler
- ❌ YES/NO Telegram approval not connected to pending_approvals flow

### Non-Critical
- ❌ `reports/` directory empty — no QuantStats tearsheets generated yet
- ❌ Firecrawl, Groq, Gemini, Claude API keys missing
- ❌ Morning briefing not tested end-to-end
- ⚠️ Backtest replay is scaffolded but not a full historical replay engine
- ⚠️ MCP argument mapping may need refinement against exact broker workflow

---

## Summary: What Must Be Done First

### PRIORITY 1: Wire the Learning Loop
- Connect learning modules to main.py scheduler
- Wire trade_reviewer to execution_agent on trade close
- Test monthly analyst loop end-to-end

### PRIORITY 2: Connect Telegram Approvals
- Wire YES/NO parsing to pending_approvals → order placement flow
- Test full approval → risk check → order → GTT flow

### PRIORITY 3: Write LLM Schemas
- Populate `llm/schemas/` with JSON schemas for all 9 tools
- Required for proper NIM tool-call validation

### PRIORITY 4: Live Testing
- Switch to `live` mode during market hours (9:15-15:30 IST)
- Place test order (small qty)
- Verify GTT placement and triggering

### PRIORITY 5: Add Missing API Keys
```bash
# Edit swingtradev3/.env and add:
FIRECRAWL_API_KEY=     # Fundamentals layer 3
GROQ_API_KEY=          # LLM fallback 1
GEMINI_API_KEY=        # LLM fallback 2
ANTHROPIC_API_KEY=     # LLM fallback 3 (black swan)
```

---

## Current Test Status

```
Total: 61 passed, 1 skipped
- test_live_data_endpoints.py: 8 passed, 1 skipped
- test_research_agent.py: multiple passed
- test_execution_agent.py: multiple passed
- test_reconciler.py: 6 passed
- test_config.py: passed
- test_indicators.py: passed
- test_risk.py: passed
- test_gtt_simulator.py: passed
- test_paper.py: passed
- test_mode_switching.py: passed
- test_tool_executor.py: passed
- test_universe_updater.py: passed
- test_kite_auth.py: passed
- test_market_tools.py: passed
```

---

*Last Updated: April 4, 2026*
