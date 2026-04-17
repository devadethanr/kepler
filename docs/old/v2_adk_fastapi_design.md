# swingtradev3 Current Architecture: ADK + FastAPI + Reflex

> Last Updated: April 16, 2026
> This top section is the current source of truth. The older draft below is retained only as historical appendix material.

## Current Runtime Summary

The shipped runtime is a **Docker-first FastAPI + Google ADK + Reflex** system with file-backed state under `swingtradev3/context/`.

### Active Services

| Service | Purpose | Dev Port |
|---------|---------|----------|
| `app` | FastAPI API, scheduler, ADK agents, file-backed runtime state | `8001 -> 8000` |
| `dashboard` | Reflex frontend and backend | `8502 -> 3000`, `8002 -> 8000` |
| `kite-mcp` | Zerodha MCP sidecar used alongside direct Kite session handling | `8081 -> 8080` |

### Startup Behavior

- `api/main.py` creates runtime directories, starts the scheduler, and warms FinBERT and TimesFM asynchronously.
- Global API-key auth is applied through FastAPI dependencies.
- CORS is restricted to the local Reflex frontend/backend origins.

## Core Architecture Decisions Reflected In Code

| Decision | Current Implementation |
|----------|------------------------|
| UI stack | Reflex, not Streamlit |
| Research orchestration | ADK `SequentialAgent` pipeline |
| Scheduling | `schedule` library inside FastAPI lifespan, with IST-aware phase detection |
| Eventing | in-process async event bus with JSONL history and failed-event persistence |
| Agent visibility | `AgentActivityManager` + SSE updates to the dashboard |
| Knowledge model | markdown wiki + `_index.json` + `_graph.json` |
| Persistence | file-backed JSON/markdown/parquet under `context/`, `reports/`, and `.backtest_cache` |
| Control plane | dashboard + REST API first, Telegram second |

## Main Runtime Flows

### Research Flow

`RegimeAgent -> FilterAgent -> BatchScannerAgent -> ScorerAgent -> ResultsSaverAgent -> KnowledgeGraphAgent`

- `ScorerAgent` reads historical stock context inline from the knowledge graph before scoring.
- `ResultsSaverAgent` writes per-scan JSON under `context/research/YYYY-MM-DD/`.
- `KnowledgeGraphAgent` updates markdown notes and graph/index artifacts after results are saved.

### Execution Flow

- `/approvals/{ticker}/yes` updates `pending_approvals.json` and triggers the ADK order agent in the background.
- `OrderExecutionAgent` applies regime-aware sizing, risk checks, and order placement.
- `execution_monitor` checks GTT state and trailing-stop logic during market hours.

### Scheduler / Events / UI Flow

- `TradingScheduler` owns the 24-hour cycle and publishes phase changes.
- `EventBus` persists event history and retries failed handlers with backoff.
- `AgentActivityManager` persists live status and broadcasts via SSE.
- Reflex bootstraps via REST and stays live through `/sse/live`.

## Current Dashboard Surface

Implemented pages in `dashboard/dashboard/dashboard.py`:

- Command Center
- Portfolio
- Research
- Approvals
- Knowledge Graph
- Agent Activity

Still missing as first-class pages:

- Trade Journal
- Learning

The Approvals page currently exists as UI shell but still needs live data and action wiring.

## Current Known Validation Gap

Dockerized validation must use the `swingtradev3/Makefile`. Current known failing test:

- `make test-file file=tests/test_agents/test_execution_monitor.py`

Reason:

- the execution monitor now skips work outside market hours, but the trailing-stop test still assumes unconditional execution

## Archived Draft Below

The remainder of this file documents earlier design thinking. It is useful for historical context, but it is no longer the authoritative architecture spec.

## Archived Early Draft

### 1. Manual Agent Orchestration
```python
# Current: manual scheduling in main.py
research_agent.run()  # Called by schedule library
execution_agent.run()  # Called by schedule library
# No coordination between agents
# No shared state management
# No evaluation of agent decisions
```

### 2. No Evaluation Framework
- No way to systematically test if agents make good decisions
- Backtest engine exists but doesn't evaluate agent reasoning quality
- No A/B testing of different agent configurations

### 3. No External API
- No REST API for external integrations
- No WebSocket for real-time data streaming
- Telegram is the only interface
- No web dashboard possible

### 4. Rigid Tool-Call Loop
- Current `llm/tool_executor.py` is a custom implementation
- No structured output schemas
- No fallback chain integration with ADK
- No agent-to-agent delegation

### 5. State Management
- JSON files in `context/` directory
- No session management
- No memory across runs
- No state versioning

### 6. No 24-Hour Operational Cycle
- No overnight monitoring of global markets or breaking news
- No pre-market preparation or morning briefing generation
- No continuous position monitoring during market hours
- No post-market analysis or data collection
- No weekend portfolio review or monthly analyst loop
- System only runs when manually triggered

### 7. No Separation of Concerns
- Data fetching, analysis, decision-making, and execution are mixed
- Can't test components independently
- Changes in one area cascade through others
- No clear contracts between modules

---

## 24-Hour Operational Cycle

**This is a 24/7 autonomous system. It never sleeps — it monitors, learns, and prepares continuously. Here's what it does at every phase of the day:**

### Phase 1: Overnight Monitoring (10:00 PM - 6:00 AM IST)

**What happens while you sleep:**

| Task | Frequency | Purpose |
|------|-----------|---------|
| **Global market tracking** | Every 2 hours | US markets (S&P 500, Nasdaq), Asian markets (Nikkei, Hang Seng, Shanghai) — if global markets crash, prepare for gap-down |
| **Continuous news monitoring** | Every 30 minutes | Breaking news, earnings releases, regulatory changes, geopolitical events — detect catalysts before market opens |
| **Macro data updates** | Every 4 hours | Crude oil, USD/INR, US 10Y yield, VIX futures — macro shifts affect sector rotation |
| **GIFT Nifty monitoring** | Every 15 minutes (5 AM onwards) | Early indicator of Indian market opening direction |
| **Corporate action alerts** | Real-time | Dividends, splits, bonus announcements — adjust GTT stops automatically |
| **F&O expiry calendar check** | Daily at midnight | Alert if tomorrow is expiry week — adjust strategy accordingly |

**Output by 6:00 AM:**
- Overnight market summary (global performance, key news, macro shifts)
- GIFT Nifty direction indicator
- Any corporate actions affecting open positions
- Updated sentiment scores for held stocks

### Phase 2: Pre-Market Preparation (6:00 AM - 9:15 AM IST)

**What happens before market opens:**

| Time | Task | Purpose |
|------|------|---------|
| 6:00 AM | **Overnight news digest** | Compile all overnight news, score sentiment impact on held stocks + shortlist |
| 6:30 AM | **Morning regime check** | Re-evaluate market regime based on global cues, GIFT Nifty, macro data |
| 7:00 AM | **FII/DII preliminary data** | Check if any early institutional activity signals |
| 7:30 AM | **Earnings calendar check** | Any earnings today? Adjust strategy for affected stocks |
| 8:00 AM | **Morning briefing generation** | NIM generates comprehensive morning report: regime, overnight summary, held positions status, today's watchlist |
| 8:30 AM | **Send morning briefing** | Telegram + Dashboard notification with today's plan |
| 8:45 AM | **Approval reminders** | Remind about pending approvals that are still valid (price hasn't moved >3%) |
| 9:00 AM | **Pre-market setup** | Load all data, verify Kite connection, check PAUSE file, validate state |

**Morning Briefing Example:**
```
🌅 MORNING BRIEFING - April 5, 2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 MARKET REGIME: Bull (confidence: 0.82)
   Nifty 50: 22,450 (+0.3%) | VIX: 12.5 (low)
   GIFT Nifty: +45 points (gap-up expected)

🌍 OVERNIGHT SUMMARY:
   US: S&P +0.8%, Nasdaq +1.2%
   Asia: Nikkei +0.5%, Hang Seng -0.3%
   Crude: $78.5 (-1.2%) → Positive for paints/tyres
   USD/INR: 83.15 (stable)

📈 OPEN POSITIONS (3):
   RELIANCE: Entry ₹2,850 | Current ₹2,920 (+2.5%) | GTT active
   HDFCBANK: Entry ₹1,650 | Current ₹1,680 (+1.8%) | GTT active
   TCS: Entry ₹3,800 | Current ₹3,750 (-1.3%) | Watch support

🔔 PENDING APPROVALS (2):
   INFY: Score 7.8 | Entry ₹1,520-1,540 | Expires in 2 days
   SBIN: Score 7.2 | Entry ₹820-835 | Price moved 2% above zone

📋 TODAY'S WATCHLIST:
   RELIANCE: Environmental clearance catalyst → Monitor for breakout
   TCS: Near support ₹3,720 → Watch for bounce
   BANKNIFTY: FII buying continues → Banking stocks in focus

⚠️ ALERTS:
   - TCS earnings on April 10 (5 days) → Consider tightening stop
   - F&O expiry on April 25 → Normal week
```

### Phase 3: Market Hours Execution (9:15 AM - 3:30 PM IST)

**What happens during market hours:**

| Time | Task | Frequency |
|------|------|-----------|
| 9:15-9:45 AM | **Opening range detection** | Monitor first 30-min candle, avoid entries during noise |
| 9:45 AM onwards | **Position monitoring** | Every 15 minutes |
| 9:45 AM onwards | **GTT health checks** | Every 30 minutes — verify GTTs still exist in Kite |
| 10:00 AM | **Intraday news scan** | Any breaking news affecting held stocks? |
| 10:30 AM | **Entry timing window** | Check if any approved setups have optimal entry conditions |
| 11:00 AM | **Mid-morning regime check** | Has regime changed? Adjust if needed |
| 12:00 PM | **Lunch-time volume check** | Volume typically drops — avoid entries 12-1 PM |
| 1:00 PM | **Afternoon position review** | Re-evaluate all positions, trail stops if profitable |
| 2:00 PM | **Late-day news scan** | Any afternoon developments? |
| 2:30 PM | **Final entry window** | Last chance for entries (avoid after 3:00 PM) |
| 3:00 PM | **Closing preparation** | Record EOD data, prepare for post-market analysis |
| 3:30 PM | **Market close actions** | Final position snapshot, GTT verification, state save |

**Position Monitoring Logic:**
```
Every 15 minutes:
  For each open position:
    1. Fetch current LTP
    2. Check if GTT still exists in Kite
    3. If GTT missing → ALERT immediately (never auto-replace)
    4. If profitable > 5% → Consider trailing stop
    5. If approaching stop loss → ALERT
    6. If volume drying up → Flag for exit intelligence review
    7. If parabolic move (>15% in 3 days) → ALERT for partial profit booking
```

### Phase 4: Post-Market Analysis (3:30 PM - 6:00 PM IST)

**What happens after market closes:**

| Time | Task | Purpose |
|------|------|---------|
| 3:30 PM | **EOD data collection** | Fetch final OHLCV for all 200 stocks, save to parquet cache |
| 3:45 PM | **Position P&L calculation** | Update unrealized P&L for all open positions |
| 4:00 PM | **FII/DII final data** | Fetch institutional flow data for the day |
| 4:15 PM | **Options chain analysis** | PCR, OI changes, max pain for F&O stocks |
| 4:30 PM | **Corporate action check** | Any dividends, splits, bonuses announced today? |
| 5:00 PM | **Trade observation logging** | Log any interesting patterns observed today |
| 5:30 PM | **State snapshot** | Save complete state to `context/daily/YYYY-MM-DD.json` |

### Phase 5: Evening Research Pipeline (6:00 PM - 9:00 PM IST)

**The main research cycle:**

| Time | Task | Duration |
|------|------|----------|
| 6:00 PM | **Research pipeline starts** | Triggered by scheduler |
| 6:00-6:15 PM | Layer 0: Broad signal sweep | News, FII/DII, options, block deals |
| 6:15-6:30 PM | Layer 1-2: Priority scoring + filtering | 200 → ~15-25 qualified stocks |
| 6:30-8:00 PM | Layer 3: Deep analysis (parallel batches) | ~15-25 stocks × 4 agents each |
| 8:00-8:30 PM | Layer 4: LLM scoring + shortlisting | Top 7 stocks with scores ≥ 7.0 |
| 8:30 PM | **Send evening briefing** | Telegram + Dashboard with shortlist |
| 8:45 PM | **Approval window opens** | User can review and approve/reject |

### Phase 6: Night Wind-Down (9:00 PM - 10:00 PM IST)

| Task | Purpose |
|------|---------|
| Final news scan | Any late-breaking developments? |
| State persistence | Save all session state to JSON |
| Log rotation | Archive today's logs |
| System health check | Verify all components healthy |
| Enter overnight monitoring mode | Switch to low-frequency monitoring |

### Weekend Activities

| Day | Task |
|-----|------|
| **Saturday** | Weekly portfolio review, performance stats update |
| **Sunday (First of month)** | Monthly analyst loop — trade review, SKILL.md proposals, stats recalculation |
| **Sunday (Other weeks)** | System maintenance, dependency updates, log cleanup |

### Task Classification

| Task Type | Frequency | Trigger | ADK Component |
|-----------|-----------|---------|---------------|
| **Continuous** | Every 15-30 min | Background loop | ADK LoopAgent (execution_monitor) |
| **Scheduled** | Specific times | Cron scheduler | FastAPI background tasks |
| **Event-driven** | On trade close, GTT trigger, news alert | Webhook/callback | ADK callbacks |
| **On-demand** | User-triggered via API/Dashboard | Manual trigger | FastAPI endpoints |

---

## Separation of Concerns: 10-Layer Architecture

**With the 24-hour cycle, multi-signal funnel, ADK agents, FastAPI, Streamlit, and all new data sources — clean separation of concerns is critical. Without it, this becomes an unmaintainable tangled mess.**

### The 10 Layers

Each layer is **independent, testable, and replaceable**. They communicate through well-defined contracts.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: SCHEDULER (When things happen)                        │
│  ─────────────────────────────────────────────────────────────  │
│  - 24-hour cycle orchestration                                  │
│  - Cron triggers, event listeners                               │
│  - FastAPI background tasks                                     │
│  → Triggers other layers, does NO analysis itself               │
│                                                                 │
│  Files: api/tasks/scheduler.py, api/tasks/research_task.py      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: DATA SOURCES (Where data comes from)                  │
│  ─────────────────────────────────────────────────────────────  │
│  - Kite API (OHLCV, quotes, historical, GTT, orders)           │
│  - NSE (FII/DII, block deals, options chain, corporate actions)│
│  - News APIs (Tavily, RSS feeds, Reddit)                        │
│  - Macro APIs (FRED, RBI, Yahoo Finance)                        │
│  - Local caches (parquet, JSON)                                 │
│  → Pure data fetching, ZERO analysis, ZERO decisions            │
│                                                                 │
│  Files: data/kite_fetcher.py, data/institutional_flows.py,      │
│         data/news_aggregator.py, data/macro_indicators.py,      │
│         data/options_analyzer.py, data/earnings_analyzer.py     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: SIGNAL ENGINE (What the data means)                   │
│  ─────────────────────────────────────────────────────────────  │
│  - Technical indicators (TA-Lib, pandas-ta)                     │
│  - Sentiment analysis (FinBERT, keyword detection)              │
│  - Regime detection (Nifty trend, VIX, breadth)                 │
│  - Options analysis (PCR, IV, OI changes)                       │
│  - Volume analysis (VWAP, CMF, OBV, delivery %)                 │
│  - Relative strength (vs index, sector, peers)                  │
│  → Pure computation, ZERO decisions, ZERO agent logic           │
│                                                                 │
│  Files: data/indicators/*, tools/analysis/sentiment_analysis.py,│
│         tools/analysis/regime_detection.py,                     │
│         tools/analysis/correlation_check.py,                    │
│         tools/analysis/entry_timing.py                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: AGENTS (What to do with the signals)                  │
│  ─────────────────────────────────────────────────────────────  │
│  - ADK LlmAgents (reasoning, scoring, decisions)                │
│  - ADK SequentialAgent (research pipeline)                      │
│  - ADK ParallelAgent (batch stock analysis)                     │
│  - ADK LoopAgent (position monitoring)                          │
│  - ADK human-in-the-loop (approvals)                            │
│  → Pure decision-making, ZERO data fetching, ZERO execution     │
│                                                                 │
│  Files: agents/root.py, agents/research/*, agents/execution/*,  │
│         agents/learning/*, agents/macro/*                       │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: RISK ENGINE (Can we do it?)                           │
│  ─────────────────────────────────────────────────────────────  │
│  - Per-trade risk check (max 1.5% risk)                         │
│  - Portfolio correlation check                                  │
│  - Circuit breakers (drawdown, weekly loss)                     │
│  - Position sizing (Kelly, confidence-based)                    │
│  - Regime-adjusted sizing                                       │
│  → Pure validation gate, says YES/NO, does NOT execute          │
│                                                                 │
│  Files: risk/engine.py, risk/position_sizer.py,                 │
│         risk/circuit_breakers.py, risk/correlation_checker.py   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: EXECUTION (Doing it)                                  │
│  ─────────────────────────────────────────────────────────────  │
│  - Order placement (Kite API)                                   │
│  - GTT management (place, modify, cancel, trail)                │
│  - Corporate action handling (adjust stops)                     │
│  - Paper/live mode routing                                      │
│  → Pure execution, ZERO analysis, ZERO decisions                │
│                                                                 │
│  Files: tools/execution/order_execution.py,                     │
│         tools/execution/gtt_manager.py,                         │
│         tools/execution/alerts.py                               │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 7: STATE & PERSISTENCE (Remembering)                     │
│  ─────────────────────────────────────────────────────────────  │
│  - ADK session.state (in-memory)                                │
│  - File-based JSON persistence (context/)                       │
│  - Parquet cache (historical data)                              │
│  - Trade history (trades.json)                                  │
│  - Session snapshots (context/daily/)                           │
│  → Pure storage, ZERO logic                                     │
│                                                                 │
│  Files: context/*, storage.py                                   │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 8: API & DASHBOARD (Showing it)                          │
│  ─────────────────────────────────────────────────────────────  │
│  - FastAPI REST endpoints                                       │
│  - FastAPI WebSocket (real-time alerts)                         │
│  - Streamlit dashboard (charts, tables, approvals)              │
│  → Pure presentation, ZERO logic, ZERO decisions                │
│                                                                 │
│  Files: api/*, dashboard/*                                      │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 9: NOTIFICATIONS (Alerting)                              │
│  ─────────────────────────────────────────────────────────────  │
│  - Telegram (mobile alerts)                                     │
│  - WebSocket broadcasts (dashboard updates)                     │
│  - Log files (audit trail)                                      │
│  → Pure messaging, ZERO logic                                   │
│                                                                 │
│  Files: notifications/telegram_client.py, logs/*                │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 10: LEARNING (Improving)                                 │
│  ─────────────────────────────────────────────────────────────  │
│  - Trade review (thesis vs outcome)                             │
│  - Stats engine (Sharpe, win rate, Kelly)                       │
│  - Lesson generation (SKILL.md proposals)                       │
│  - Skill updater (git commit on approval)                       │
│  → Pure retrospective analysis, ZERO live decisions             │
│                                                                 │
│  Files: agents/learning/*, learning/stats_engine.py             │
└─────────────────────────────────────────────────────────────────┘
```

### Separation Rules (Enforced by Design)

| Rule | What It Means | Violation Example |
|------|--------------|-------------------|
| **Data sources never analyze** | `kite_fetcher.py` returns raw OHLCV, never says "bullish" or "bearish" | `kite_fetcher.py` returning `{trend: "bullish"}` |
| **Signal engine never decides** | `detect_regime()` returns `{regime: "bull", confidence: 0.82}`, never says "buy more" | `detect_regime()` returning `{action: "increase_position_size"}` |
| **Agents never fetch data** | `scorer_agent` receives pre-computed signals, never calls Kite API directly | `scorer_agent` calling `kite_fetcher.get_eod_data()` |
| **Risk engine never executes** | `check_risk()` returns `{approved: true, max_shares: 32}`, never places orders | `check_risk()` calling `place_order()` |
| **Execution never analyzes** | `place_order()` takes parameters and executes, never decides what to buy | `place_order()` checking RSI before placing |
| **Dashboard never decides** | Streamlit shows data, approval buttons POST to API, never runs agents directly | Dashboard calling `research_agent.run()` directly |
| **Learning never affects live** | Trade review runs on closed trades only, never changes open position behavior | `lesson_agent` modifying active GTT stops |
| **Notifications never analyze** | `telegram_client.py` sends formatted messages, never generates content | `telegram_client.py` deciding what to alert about |

### What Breaks Without This

| Problem | Example | Consequence |
|---------|---------|-------------|
| **Tight coupling** | Agent calls Kite API directly | Can't mock for testing, can't switch data sources |
| **Mixed concerns** | Risk check inside order execution | Can't test risk independently, can't reuse across agents |
| **Hidden dependencies** | Dashboard runs analysis logic | Dashboard becomes slow, hard to cache, breaks when analysis changes |
| **No testability** | Everything intertwined | Can't unit test anything, must run full system to test one change |
| **Fragile changes** | Change in news API breaks scoring | One change cascades through entire system |

### Layer Communication Contracts

Each layer communicates through **typed interfaces** (Pydantic models). No layer knows about the internal implementation of another.

```
Layer 2 → Layer 3: RawData → ComputedSignals
  Example: OHLCV DataFrame → {ema_50: 22450, rsi_14: 62.5, volume_ratio: 1.8}

Layer 3 → Layer 4: ComputedSignals → AgentContext
  Example: {regime: "bull", sentiment: 0.7, pcr: 1.2, ema_200_cross: true}

Layer 4 → Layer 5: AgentDecision → RiskValidation
  Example: {ticker: "RELIANCE", action: "buy", score: 8.5, entry: 2850, stop: 2750}

Layer 5 → Layer 6: ValidatedDecision → ExecutionOrder
  Example: {approved: true, max_shares: 32, entry: 2850, stop: 2750, target: 3100}

Layer 6 → Layer 7: ExecutionResult → StateUpdate
  Example: {order_id: "240405001", status: "filled", fill_price: 2852, gtt_id: 12345}

Layer 7 → Layer 8: StateData → APIResponse
  Example: {positions: [...], cash: 150000, pnl: +2500}

Layer 8 → Layer 9: AlertPayload → Notification
  Example: {type: "entry_filled", message: "RELIANCE entry filled @ ₹2852"}

Layer 10 → Layer 4: LearningInsight → AgentInstruction
  Example: {lesson: "Breakouts in bear regime lose 73% — add regime filter"}
```

---

## Target Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Streamlit Dashboard (New)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Overview │ │ Research │ │Approvals │ │Positions │ │  Trades  │ │
│  │ P&L Chart│ │ Scan     │ │ YES/NO   │ │ Live     │ │ History  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│       │             │             │             │             │      │
│       └─────────────┴─────────────┴─────────────┴─────────────┘      │
│                              │                                       │
│                              ▼                                       │
├──────────────────────────────────────────────────────────────────────┤
│                        FastAPI Layer (New)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │ REST API │  │WebSocket │  │Background│  │  OpenAPI/Swagger │    │
│  │Endpoints │  │  Alerts  │  │  Tasks   │  │     Docs         │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────┘    │
│       │              │              │                                │
│       ▼              ▼              ▼                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              ADK Root Coordinator Agent                       │   │
│  │  (LlmAgent - Gemini via LiteLLM → NIM/Gemini/Claude)         │   │
│  └────────┬────────────────────────────────────┬────────────────┘   │
│           │                                    │                    │
│  ┌────────▼────────┐              ┌────────────▼──────────────┐    │
│  │ Research Agent  │              │  Execution Agent          │    │
│  │ (Sequential)    │              │  (LoopAgent)              │    │
│  │                 │              │                           │    │
│  │ ┌─────────────┐ │              │ ┌───────────────────────┐ │    │
│  │ │Regime Check │ │              │ │Position Monitor       │ │    │
│  │ ├─────────────┤ │              │ ├───────────────────────┤ │    │
│  │ │Market Data  │ │              │ │GTT Health Check       │ │    │
│  │ ├─────────────┤ │              │ ├───────────────────────┤ │    │
│  │ │Fundamentals │ │              │ │Stop Trailing          │ │    │
│  │ ├─────────────┤ │              │ ├───────────────────────┤ │    │
│  │ │Sentiment    │ │              │ │Corporate Actions      │ │    │
│  │ ├─────────────┤ │              │ └───────────────────────┘ │    │
│  │ │Options      │ │              │                           │    │
│  │ ├─────────────┤ │              │ ┌───────────────────────┐ │    │
│  │ │Scoring      │ │              │ │Order Agent            │ │    │
│  │ └─────────────┘ │              │ │(Human-in-Loop)        │ │    │
│  │                 │              │ └───────────────────────┘ │    │
│  │ ┌─────────────┐ │              │                           │    │
│  │ │Parallel Scan│ │              │ ┌───────────────────────┐ │    │
│  │ │(10 stocks)  │ │              │ │Learning Agent         │ │    │
│  │ └─────────────┘ │              │ │(Monthly Review)       │ │    │
│  └─────────────────┘              │ └───────────────────────┘ │    │
│                                   └───────────────────────────┘    │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                  ADK Tool Registry                          │   │
│  │                                                             │   │
│  │  get_eod_data    get_fundamentals    analyze_sentiment     │   │
│  │  place_order     place_gtt           check_risk            │   │
│  │  search_news     get_options_data    get_fii_dii           │   │
│  │  get_macro_data  check_correlation   check_entry_timing    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │              ADK Session State & Memory (File JSON)         │   │
│  │                                                             │   │
│  │  session.state['regime'] = 'bull'                          │   │
│  │  session.state['positions'] = [...]                        │   │
│  │  session.state['pending_approvals'] = [...]                │   │
│  │  session.state['market_data'] = {...}                      │   │
│  │  session.state['trade_observations'] = [...]               │   │
│  └────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### Directory Structure (Organized by Layer)

```
swingtradev3/
├── main.py                          # FastAPI app + ADK runner startup
├── config.py                        # Pydantic Settings (unchanged)
├── config.yaml                      # All tunable values (unchanged)
├── requirements.txt                 # Updated with new deps
├── .env                             # Secrets only (unchanged)
│
├── models.py                        # Shared Pydantic models (layer contracts)
├── paths.py                         # Path constants
├── storage.py                       # File I/O utilities
├── logging_config.py                # Logging setup
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 1: SCHEDULER
│ ═══════════════════════════════════════════════════════════════
├── api/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app definition
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py                # GET /health
│   │   ├── positions.py             # GET /positions, GET /positions/{id}
│   │   ├── trades.py                # GET /trades, POST /trades/{id}/close
│   │   ├── approvals.py             # POST /approvals/{id}/yes|no
│   │   ├── scan.py                  # POST /scan (trigger research scan)
│   │   ├── regime.py                # GET /regime (current market regime)
│   │   ├── stats.py                 # GET /stats (performance metrics)
│   │   └── ws.py                    # WebSocket /ws/alerts
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── position.py              # Pydantic models for positions
│   │   ├── trade.py                 # Pydantic models for trades
│   │   ├── approval.py              # Pydantic models for approvals
│   │   └── scan.py                  # Pydantic models for scan results
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                  # API key authentication
│   │   └── rate_limit.py            # Rate limiting
│   └── tasks/
│       ├── __init__.py
│       ├── scheduler.py             # 24-hour cycle orchestration
│       ├── overnight_monitor.py     # Phase 1: Overnight monitoring
│       ├── morning_briefing.py      # Phase 2: Pre-market prep
│       ├── market_hours.py          # Phase 3: Market hours execution
│       ├── post_market.py           # Phase 4: Post-market analysis
│       ├── research_task.py         # Phase 5: Evening research pipeline
│       └── wind_down.py             # Phase 6: Night wind-down
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 2: DATA SOURCES
│ ═══════════════════════════════════════════════════════════════
├── data/
│   ├── __init__.py
│   ├── kite_fetcher.py              # Kite API client (OHLCV, quotes, historical)
│   ├── nifty200_loader.py           # Universe constituent list
│   ├── nifty50_loader.py            # Nifty 50 list
│   ├── corporate_actions.py         # Dividends, splits, bonus
│   ├── earnings_calendar.py         # Upcoming earnings
│   ├── universe_updater.py          # Universe maintenance
│   ├── market_regime.py             # [NEW] Market regime detection
│   ├── institutional_flows.py       # [NEW] FII/DII/block deals
│   ├── news_aggregator.py           # [NEW] Multi-source news (Tavily, RSS, Reddit)
│   ├── earnings_analyzer.py         # [NEW] Earnings quality analysis
│   ├── events_calendar.py           # [NEW] RBI, budget, rebalancing dates
│   ├── options_analyzer.py          # [NEW] Options chain intelligence
│   ├── macro_indicators.py          # [NEW] Macro data layer (crude, USD/INR, yields)
│   ├── timesfm_forecaster.py        # [NEW] Google TimesFM 2.5 price/volume forecasting
│   └── indicators/                  # Technical indicators (pure computation)
│       ├── __init__.py
│       ├── momentum.py
│       ├── trend.py
│       ├── volatility.py
│       ├── volume.py                # Enhanced: VWAP, CMF, volume profile
│       ├── structure.py
│       ├── relative_strength.py     # Enhanced: multi-benchmark RS
│       └── patterns.py
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 3: SIGNAL ENGINE
│ ═══════════════════════════════════════════════════════════════
├── tools/
│   ├── __init__.py                  # TOOL_REGISTRY
│   ├── market/
│   │   ├── __init__.py
│   │   ├── market_data.py           # @tool def get_eod_data(ticker: str)
│   │   ├── fundamental_data.py      # @tool def get_fundamentals(ticker: str)
│   │   ├── news_search.py           # @tool def search_news(query: str)
│   │   ├── fii_dii_data.py          # @tool def get_fii_dii()
│   │   └── options_data.py          # @tool def get_options_data(ticker: str)
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── order_execution.py       # @tool def place_order(...)
│   │   ├── gtt_manager.py           # @tool def place_gtt(...)
│   │   ├── risk_check.py            # @tool def check_risk(...)
│   │   └── alerts.py                # @tool def send_alert(...)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── sentiment_analysis.py    # @tool def analyze_sentiment(ticker: str)
│   │   ├── regime_detection.py      # @tool def detect_regime()
│   │   ├── correlation_check.py     # @tool def check_correlation(positions: list)
│   │   └── entry_timing.py          # @tool def check_entry_timing(ticker: str)
│   │   └── timesfm_forecast.py      # @tool def forecast_timeseries(ticker, horizon)
│   └── macro/
│       ├── __init__.py
│       ├── macro_data.py            # @tool def get_macro_indicators()
│       └── events_calendar.py       # @tool def get_upcoming_events()
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 4: AGENTS
│ ═══════════════════════════════════════════════════════════════
├── agents/
│   ├── __init__.py
│   ├── root.py                      # Root coordinator LlmAgent
│   ├── research/
│   │   ├── __init__.py
│   │   ├── pipeline.py              # SequentialAgent: full research pipeline
│   │   ├── filter_agent.py          # [NEW] Multi-signal candidate selection funnel
│   │   ├── regime_agent.py           # LlmAgent: market regime detection
│   │   ├── market_data_agent.py     # LlmAgent: fetch + analyze OHLCV
│   │   ├── fundamentals_agent.py    # LlmAgent: fundamental analysis
│   │   ├── sentiment_agent.py       # LlmAgent: news + social sentiment
│   │   ├── options_agent.py         # LlmAgent: options chain analysis
│   │   ├── scorer_agent.py          # LlmAgent: final scoring + shortlisting
│   │   ├── timesfm_agent.py         # LlmAgent: TimesFM forecast integration
│   │   └── scanner.py               # BatchScannerAgent: dynamic parallel analysis
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── monitor.py               # LoopAgent: 30-min position polling
│   │   ├── order_agent.py           # LlmAgent: entry decisions + risk check
│   │   ├── gtt_agent.py             # LlmAgent: GTT lifecycle management
│   │   └── exit_agent.py            # LlmAgent: exit intelligence
│   ├── learning/
│   │   ├── __init__.py
│   │   ├── reviewer.py              # LlmAgent: trade review on close
│   │   ├── stats_agent.py           # LlmAgent: monthly stats calculation
│   │   └── lesson_agent.py          # LlmAgent: SKILL.md improvement proposals
│   └── macro/
│       ├── __init__.py
│       ├── regime_agent.py           # LlmAgent: macro regime detection
│       └── flow_agent.py             # LlmAgent: institutional flow tracking
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 5: RISK ENGINE
│ ═══════════════════════════════════════════════════════════════
├── risk/
│   ├── __init__.py
│   ├── engine.py                    # Core risk validation
│   ├── position_sizer.py            # Kelly + confidence-based sizing
│   ├── circuit_breakers.py          # Drawdown, weekly loss limits
│   ├── circuit_limit_checker.py     # Stock-level circuit monitoring
│   └── correlation_checker.py       # [NEW] Portfolio correlation + VaR
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 6: EXECUTION
│ ═══════════════════════════════════════════════════════════════
│  (Execution tools are in tools/execution/ — Layer 3 tools called by Layer 6)
│  Execution logic is invoked by agents (Layer 4) through tools
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 7: STATE & PERSISTENCE
│ ═══════════════════════════════════════════════════════════════
├── context/                         # [MANAGED by ADK session.state + file persistence]
│   # state.json → ADK session.state (persisted to JSON via callback)
│   # trades.json → ADK artifacts + FastAPI persistence
│   # stats.json → ADK session.state
│   # pending_approvals.json → ADK human-in-the-loop
│   # research/ → ADK artifacts
│   # fundamentals_cache.json → unchanged (data layer cache)
│   # news_cache.json → unchanged (data layer cache)
│   # nifty200.json → unchanged (data layer cache)
│   # auth/ → unchanged (auth layer)
│   # daily/ → ADK session snapshots
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 8: API & DASHBOARD
│ ═══════════════════════════════════════════════════════════════
├── dashboard/                       # Streamlit Trading Dashboard
│   ├── __init__.py
│   ├── app.py                       # Streamlit main app
│   ├── pages/
│   │   ├── 1_overview.py            # Portfolio overview, P&L chart
│   │   ├── 2_research.py            # Latest scan results, scores
│   │   ├── 3_approvals.py           # Pending setups with YES/NO
│   │   ├── 4_positions.py           # Live positions, GTT status
│   │   ├── 5_trades.py              # Trade history, per-trade P&L
│   │   ├── 6_learning.py            # SKILL.md evolution, monthly stats
│   │   └── 7_agent_trace.py         # ADK trace view for debugging
│   └── components/
│       ├── __init__.py
│       ├── charts.py                # Plotly chart components
│       ├── tables.py                # Data table components
│       └── widgets.py               # Reusable UI widgets
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 9: NOTIFICATIONS
│ ═══════════════════════════════════════════════════════════════
├── notifications/                   # [PARTIALLY REMOVED]
│   ├── __init__.py
│   └── telegram_client.py           # Kept for Telegram alerts (optional)
│   # telegram_handler.py → replaced by ADK human-in-the-loop + FastAPI
│   # telegram_commands.py → replaced by FastAPI routes
│   # formatter.py → replaced by FastAPI schemas
│
├── logs/                            # Logging (audit trail)
│   ├── research.log
│   ├── decisions.log
│   ├── trades.log
│   └── errors.log
│
│ ═══════════════════════════════════════════════════════════════
│  LAYER 10: LEARNING
│ ═══════════════════════════════════════════════════════════════
│  (Learning agents are in agents/learning/ — Layer 4 agents)
│  Learning stats engine persists to context/stats.json
│
│ ═══════════════════════════════════════════════════════════════
│  SUPPORTING MODULES (Cross-cutting)
│ ═══════════════════════════════════════════════════════════════
├── strategy/                        # Strategy Files (unchanged)
│   ├── SKILL.md
│   ├── SKILL.md.staging
│   ├── research_program.md
│   └── analyst_program.md
│
├── auth/                            # Authentication (unchanged)
│   ├── __init__.py
│   ├── token_manager.py
│   ├── totp_login.py
│   ├── kite/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── login.py
│   │   └── session_store.py
│   └── mcp/
│       ├── __init__.py
│       └── login.py
│
├── integrations/                    # External integrations (unchanged)
│   ├── __init__.py
│   └── kite/
│       ├── __init__.py
│       └── mcp_client.py
│
├── paper/                           # Simulation Layer (unchanged)
│   ├── __init__.py
│   ├── fill_engine.py
│   ├── gtt_simulator.py
│   └── slippage_model.py
│
├── backtest/                        # Backtest Engine (unchanged)
│   ├── __init__.py
│   ├── data_fetcher.py
│   ├── candle_replay.py
│   ├── walk_forward.py
│   ├── optimizer.py
│   ├── metrics.py
│   └── nse_bhav_fetcher.py
│
├── tests/                           # Tests (expanded)
│   ├── test_config.py
│   ├── test_indicators.py
│   ├── test_risk.py
│   ├── test_paper.py
│   ├── test_gtt_simulator.py
│   ├── test_mode_switching.py
│   ├── test_reconciler.py
│   ├── test_kite_auth.py
│   ├── test_market_tools.py
│   ├── test_tool_executor.py
│   ├── test_universe_updater.py
│   ├── test_live_data_endpoints.py
│   ├── test_live_integration.py
│   ├── test_research_agent.py       # [REWRITTEN for ADK]
│   ├── test_execution_agent.py      # [REWRITTEN for ADK]
│   ├── test_agents/                 # [NEW] ADK agent tests
│   │   ├── test_research_pipeline.py
│   │   ├── test_execution_monitor.py
│   │   └── test_learning_loop.py
│   ├── test_api/                    # [NEW] FastAPI endpoint tests
│   │   ├── test_positions.py
│   │   ├── test_trades.py
│   │   ├── test_approvals.py
│   │   └── test_scan.py
│   └── test_evaluation/             # [NEW] ADK evaluation tests
│       ├── test_agent_decisions.py
│       └── test_backtest_eval.py
│
└── reports/                         # Reports (unchanged)
```

---

## ADK Agent Design

### Root Coordinator Agent

```python
# agents/root.py
from google.adk.agents import LlmAgent

root_agent = LlmAgent(
    name="TradingCoordinator",
    model="litellm:nim/deepseek-ai/deepseek-v3-2",
    instruction="""
    You are the coordinator of an autonomous swing trading system for Indian equities.
    Your job is to orchestrate research, execution, and learning agents.

    When asked to scan: delegate to ResearchPipeline.
    When asked to monitor positions: delegate to ExecutionMonitor.
    When asked to review trades: delegate to LearningReviewer.
    When asked for status: return current state from session.state.

    Always enforce risk management rules. Never allow trades that exceed
    max_risk_pct_per_trade or max_drawdown_pct.
    """,
    description="Main coordinator of the swing trading system",
    sub_agents=[
        research_pipeline,
        execution_monitor,
        order_agent,
        learning_reviewer,
        lesson_agent,
    ],
)
```

### Research Pipeline (SequentialAgent)

```python
# agents/research/pipeline.py
from google.adk.agents import SequentialAgent

research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    sub_agents=[
        regime_agent,           # Step 1: What kind of market is this?
        filter_agent,           # Step 2: Multi-signal candidate selection funnel (200 → ~15-25)
        scanner,                # Step 3: Deep analysis of qualified stocks (dynamic parallel)
        scorer_agent,           # Step 4: Score and shortlist
    ],
    description="Complete research pipeline: regime → filter → scan → score → shortlist",
)
```

### Multi-Signal Candidate Selection Funnel

**Key principle: Never hardcode stock tickers. The system autonomously identifies candidates using a layered funnel that filters from 200 → ~15-25 qualified stocks before spending LLM tokens.**

```
┌──────────────────────────────────────────────────────────────┐
│                  LAYER 0: Broad Signal Sweep                  │
│                  (1-2 API calls, covers all 200)              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  A. News Sweep (1 Tavily call):                              │
│     "Indian stock market today Nifty 200 news"               │
│     → Extract mentioned tickers from results                 │
│     → Result: [RELIANCE, TCS, INFY, HDFCBANK, ...] (~15)    │
│                                                              │
│  B. FII/DII Flow Check (free, NSE):                          │
│     → Sectors with net buying today                          │
│     → Result: [Banking, IT, Auto]                            │
│                                                              │
│  C. Options Unusual Activity (free, Kite):                   │
│     → Stocks with PCR spike or OI surge                      │
│     → Result: [RELIANCE, ADANIENT, TATASTEEL]               │
│                                                              │
│  D. Block/Bulk Deals (free, NSE):                            │
│     → Institutional buys today                               │
│     → Result: [HDFCBANK, ICICIBANK]                          │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               LAYER 1: Union + Priority Scoring               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Combine all signals → every stock gets a priority score:    │
│                                                              │
│  Stock        │ News │ FII  │ Options │ Block │ Priority    │
│  RELIANCE     │  ✓   │  ✓   │   ✓     │   ✗   │ HIGH (3)    │
│  HDFCBANK     │  ✓   │  ✓   │   ✗     │   ✓   │ HIGH (3)    │
│  TCS          │  ✓   │  ✓   │   ✗     │   ✗   │ MEDIUM (2)  │
│  INFY         │  ✓   │  ✗   │   ✗     │   ✗   │ LOW (1)     │
│  SBIN         │  ✗   │  ✓   │   ✗     │   ✗   │ LOW (1)     │
│  ...190 more  │  ✗   │  ✗   │   ✗     │   ✗   │ ZERO (0)    │
│                                                              │
│  Rule: Only analyze stocks with priority ≥ 1                │
│  Result: ~30-40 stocks advance to Layer 2                   │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              LAYER 2: Python Fast Filters                     │
│              (Fast, free, no LLM)                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  For each of the ~30-40 priority stocks:                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ✓ Price > 200 EMA (trend filter)                    │    │
│  │ ✓ Volume > 20-day average (liquidity)               │    │
│  │ ✓ Not in F&O ban list                               │    │
│  │ ✓ Not within 3 days of earnings (avoid uncertainty) │    │
│  │ ✓ Pledging < 25% (governance filter)                │    │
│  │ ✓ Delivery % > 50% (genuine buying, not intraday)   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Result: ~15-25 stocks advance to Layer 3                   │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│           LAYER 3: Deep Analysis (LLM + Parallel)             │
│           (Expensive, only for qualified stocks)              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  For each of the ~15-25 qualified stocks:                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Full OHLCV + all technical indicators (Kite)     │    │
│  │ 2. Fundamentals: PE, EPS, debt, promoter, pledging  │    │
│  │ 3. Deep news sentiment (FinBERT + LLM reasoning)    │    │
│  │ 4. Options chain: PCR, IV, max pain, OI change      │    │
│  │ 5. RS vs Nifty 200, sector, peers                   │    │
│  │ 6. Volume-price analysis: VWAP, CMF, OBV            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Run in parallel batches of 10 via ADK ParallelAgent        │
│                                                              │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              LAYER 4: LLM Scoring + Shortlist                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ScorerAgent receives all deep analysis results:             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 1. Chain-of-thought reasoning per stock             │    │
│  │ 2. Bull case (3 reasons) + Bear case (3 reasons)    │    │
│  │ 3. Score 0-10 with confidence                       │    │
│  │ 4. Entry zone, stop loss, target                    │    │
│  │ 5. Setup type: breakout / pullback / earnings       │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Final output: Top 7 stocks with scores ≥ 7.0               │
│  → Sent to Telegram + Dashboard for approval                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Implementation: FilterAgent (Layer 0-1, Python, No LLM)

```python
# agents/research/filter_agent.py
from google.adk.agents import BaseAgent
from google.adk.events import Event

class FilterAgent(BaseAgent):
    """
    Multi-signal candidate selection funnel.
    Layer 0: Broad signal sweep (news, FII/DII, options, block deals)
    Layer 1: Union + priority scoring
    Layer 2: Python fast filters (technical, liquidity, governance)
    Output: ~15-25 qualified tickers for deep LLM analysis
    """

    async def _run_async_impl(self, ctx):
        # Layer 0A: News sweep (1 Tavily call for all 200)
        news_tickers = await sweep_news_for_tickers(
            query="Indian stock market today Nifty 200",
            universe=load_nifty200(),
        )

        # Layer 0B: FII/DII flow check (free, NSE)
        fii_sectors = await get_fii_sector_flows()  # e.g., ["Banking", "IT"]
        fii_tickers = get_stocks_in_sectors(fii_sectors, load_nifty200())

        # Layer 0C: Options unusual activity (free, Kite)
        options_tickers = await detect_unusual_options_activity(
            universe=load_nifty200(),
            pcr_threshold=1.2,
            oi_spike_pct=20,
        )

        # Layer 0D: Block/bulk deals (free, NSE)
        block_tickers = await get_block_deals_today()

        # Layer 1: Union + priority scoring
        signal_map = {}
        for t in news_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
        for t in fii_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
        for t in options_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1
        for t in block_tickers:
            signal_map[t] = signal_map.get(t, 0) + 1

        # Only stocks with ≥ 1 signal advance
        priority_stocks = [t for t, score in signal_map.items() if score >= 1]

        # Layer 2: Python fast filters
        qualified = []
        for ticker in priority_stocks:
            data = await quick_fetch(ticker)
            if (data.price > data.ema_200
                and data.volume > data.avg_volume_20d
                and not data.in_fno_ban
                and not data.earnings_within_days(3)
                and data.pledging < 25
                and data.delivery_pct > 50):
                qualified.append({
                    "ticker": ticker,
                    "priority": signal_map[ticker],
                    "signals": {
                        "news": ticker in news_tickers,
                        "fii": ticker in fii_tickers,
                        "options": ticker in options_tickers,
                        "block_deal": ticker in block_tickers,
                    },
                })

        ctx.session.state["qualified_stocks"] = qualified
        return Event(
            author=self.name,
            content={"qualified_count": len(qualified), "stocks": qualified},
        )
```

### Implementation: BatchScannerAgent (Layer 3, Dynamic ParallelAgent)

```python
# agents/research/scanner.py
from google.adk.agents import BaseAgent, ParallelAgent, SequentialAgent
from google.adk.events import Event

class BatchScannerAgent(BaseAgent):
    """
    Dynamically creates ParallelAgent for qualified stocks.
    Splits into batches of 10 (Kite rate limit) and runs each batch.
    """

    async def _run_async_impl(self, ctx):
        qualified = ctx.session.state["qualified_stocks"]
        batch_size = 10

        all_results = []
        for i in range(0, len(qualified), batch_size):
            batch = qualified[i:i+batch_size]
            sub_agents = [
                create_stock_analyzer(s["ticker"], s["priority"], s["signals"])
                for s in batch
            ]

            parallel_scanner = ParallelAgent(
                name=f"ScannerBatch_{i//batch_size}",
                sub_agents=sub_agents,
            )

            async for event in parallel_scanner.run_async(ctx):
                if event.is_final_response():
                    all_results.append(event.content)

        ctx.session.state["scan_results"] = all_results
        return Event(
            author=self.name,
            content={"stocks_analyzed": len(qualified)},
        )


def create_stock_analyzer(ticker: str, priority: int, signals: dict):
    """Create a SequentialAgent for deep analysis of one stock."""
    return SequentialAgent(
        name=f"Analyze_{ticker}",
        sub_agents=[
            market_data_agent,     # Full OHLCV + all indicators
            fundamentals_agent,    # PE, EPS, debt, promoter, pledging
            sentiment_agent,       # Deep news sentiment (FinBERT + LLM)
            options_agent,         # PCR, IV, max pain, OI change
        ],
        description=f"Deep analysis of {ticker} (priority: {priority}, signals: {signals})",
    )
```

### Why This Approach

| Aspect | Hardcoded (Wrong) | Multi-Signal Funnel (Correct) |
|--------|------------------|-------------------------------|
| **Flexibility** | Fixed 10 stocks | Adapts to market conditions (15-35 stocks) |
| **Maintenance** | Manual ticker updates | Auto-updates with Nifty 200 rebalancing |
| **Efficiency** | Wastes LLM calls on bad stocks | Filters out 85% before LLM analysis |
| **Cost** | 10 LLM calls regardless | 1 news sweep + ~15-25 LLM calls |
| **Catalyst awareness** | None | News sweep catches everything |
| **Institutional awareness** | None | FII/DII flows, block deals, options activity |
| **Intelligence** | Dumb — analyzes everything | Smart — multi-signal funnel, LLM only on qualified |

### Real-World Example

```
Monday Morning, 8:00 AM:

Layer 0 Sweep:
  News: "RIL gets environmental clearance for new refinery" → RELIANCE
  News: "TCS wins $2B deal from European bank" → TCS
  FII: Net buyers in Banking → HDFCBANK, ICICIBANK, SBIN
  Options: RELIANCE PCR jumped from 0.8 to 1.4 → unusual bullish positioning
  Block Deals: HDFCBANK — FII bought 2M shares

Layer 1 Priority:
  RELIANCE: News ✓ + Options ✓ = HIGH (2 signals)
  HDFCBANK: News ✓ + FII ✓ + Block Deal ✓ = HIGH (3 signals)
  TCS: News ✓ + FII ✓ = MEDIUM (2 signals)
  ICICIBANK: FII ✓ = LOW (1 signal)
  SBIN: FII ✓ = LOW (1 signal)

Layer 2 Filters:
  RELIANCE: Price > 200 EMA ✓, Volume OK ✓, No ban ✓ → PASS
  HDFCBANK: Price > 200 EMA ✓, Volume OK ✓, No ban ✓ → PASS
  TCS: Price > 200 EMA ✓, Volume OK ✓, No ban ✓ → PASS
  ICICIBANK: Price < 200 EMA ✗ → FILTERED OUT
  SBIN: Earnings tomorrow ✗ → FILTERED OUT (avoid uncertainty)

Layer 3 Deep Analysis:
  RELIANCE, HDFCBANK, TCS → Full analysis (indicators + fundamentals + sentiment + options)

Layer 4 Scoring:
  RELIANCE: 8.5/10 — "Strong: news catalyst + options positioning + above 200 EMA"
  HDFCBANK: 7.8/10 — "Good: institutional buying + sector tailwind"
  TCS: 7.2/10 — "Decent: deal win but near resistance"

Final Shortlist: RELIANCE (8.5), HDFCBANK (7.8), TCS (7.2)
```

### Execution Monitor (LoopAgent)

```python
# agents/execution/monitor.py
from google.adk.agents import LoopAgent

execution_monitor = LoopAgent(
    name="ExecutionMonitor",
    max_iterations=20,  # Poll 20 times (10 hours at 30-min intervals)
    sub_agents=[
        position_checker,
        gtt_health_checker,
        stop_trail_agent,
        corporate_action_checker,
        check_market_close,
    ],
    description="Monitor positions and GTTs during market hours",
)
```

### Human-in-the-Loop Approvals

ADK has built-in human-in-the-loop support. This replaces our custom Telegram handler:

```python
# agents/execution/order_agent.py
from google.adk.agents import LlmAgent

order_agent = LlmAgent(
    name="OrderAgent",
    model="litellm:nim/qwen/qwen3.5-122b-a10b",
    instruction="""
    When a trade setup is approved by the research pipeline:
    1. Run check_risk tool
    2. If risk check passes, request human approval
    3. On human YES: place_order → place_gtt(stop) → place_gtt(target)
    4. On human NO: log rejection, remove from pending
    """,
    tools=[check_risk, place_order, place_gtt, send_alert],
)
```

### Learning Loop

```python
# agents/learning/reviewer.py
learning_reviewer = LlmAgent(
    name="TradeReviewer",
    model="litellm:nim/deepseek-ai/deepseek-v3-2",
    instruction="""
    When a trade closes (via GTT trigger or manual exit):
    1. Compare actual outcome vs original thesis
    2. Was the entry well-timed?
    3. Did the stop-loss work correctly?
    4. Tag the trade with: setup_type, regime, sector, sentiment_at_entry
    5. Log observation to session.state['trade_observations']
    """,
    tools=[get_trade_details, get_original_research, log_observation],
)

lesson_agent = LlmAgent(
    name="LessonAgent",
    model="litellm:nim/deepseek-ai/deepseek-v3-2",
    instruction="""
    Monthly review of all closed trades:
    1. Load all trades from this month
    2. Find patterns in winners and losers
    3. Propose max 3 specific SKILL.md edits with evidence
    4. Output to session.state['skill_edits_proposed']
    5. Request human approval for each edit
    """,
    tools=[get_monthly_trades, get_trade_observations, propose_skill_edit],
)
```

---

## FastAPI Design

### API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/health` | Health check | None |
| GET | `/positions` | List all open positions | API Key |
| GET | `/positions/{id}` | Get position details | API Key |
| GET | `/trades` | List closed trades | API Key |
| GET | `/trades/{id}` | Get trade details | API Key |
| POST | `/trades/{id}/close` | Manually close a trade | API Key |
| GET | `/approvals` | List pending approvals | API Key |
| POST | `/approvals/{id}/yes` | Approve a trade setup | API Key |
| POST | `/approvals/{id}/no` | Reject a trade setup | API Key |
| POST | `/scan` | Trigger research scan | API Key |
| GET | `/scan/status` | Get scan progress | API Key |
| GET | `/regime` | Get current market regime | API Key |
| GET | `/stats` | Get performance metrics | API Key |
| GET | `/ws/alerts` | WebSocket for real-time alerts | API Key |

### FastAPI App Structure

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="swingtradev3 API",
    description="Autonomous Swing Trading System API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routes import health, positions, trades, approvals, scan, regime, stats, ws

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(positions.router, prefix="/positions", tags=["Positions"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
app.include_router(scan.router, prefix="/scan", tags=["Scan"])
app.include_router(regime.router, prefix="/regime", tags=["Regime"])
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
app.include_router(ws.router, tags=["WebSocket"])

@app.on_event("startup")
async def startup():
    """Start ADK runner and background scheduler."""
    await scheduler.start()

@app.on_event("shutdown")
async def shutdown():
    """Stop ADK runner and background scheduler."""
    await scheduler.stop()
```

### Approval Endpoint (Human-in-the-Loop)

```python
# api/routes/approvals.py
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/{approval_id}/yes")
async def approve_trade(approval_id: str):
    """Approve a trade setup. Triggers ADK agent to place order."""
    # 1. Update ADK session state with approval
    # 2. Trigger ADK agent to resume with approval
    # 3. Agent runs: risk_check → place_order → place_gtt
    # 4. Return result
    pass

@router.post("/{approval_id}/no")
async def reject_trade(approval_id: str):
    """Reject a trade setup. Removes from pending approvals."""
    pass
```

---

## Streamlit Dashboard Design

### Pages

| Page | Purpose | Key Components |
|------|---------|---------------|
| **Overview** | Portfolio snapshot | P&L equity curve, total capital, open positions count, cash balance, daily P&L bar chart |
| **Research** | Scan results | Stock scores table, shortlist, regime indicator, sentiment scores, RS rankings |
| **Approvals** | Trade approvals | Pending setups with details, YES/NO buttons, reason display |
| **Positions** | Live monitoring | Position table with entry/stop/target, GTT status, trailing stops, unrealized P&L |
| **Trades** | Trade history | Closed trades table, per-trade P&L, win rate, holding period, setup type breakdown |
| **Learning** | System evolution | SKILL.md version history, monthly stats (Sharpe, Kelly), lessons learned, proposed edits |
| **Agent Trace** | Debugging | ADK trace view, tool call history, LLM reasoning, errors |

### Dashboard Architecture

```
Streamlit (port 8501)
    │
    ├── Fetches data from FastAPI API (port 8000)
    ├── Displays Plotly charts for financial data
    ├── Renders approval buttons that POST to FastAPI
    ├── Auto-refreshes every 30 seconds for live data
    └── Runs as separate Docker service
```

### Why Streamlit

- **Pure Python** — no JS/Node.js needed
- **Excellent Plotly integration** — candlestick charts, equity curves, P&L distributions
- **Real-time updates** — `st.empty()` with auto-refresh
- **Interactive** — approval buttons, dropdowns, date pickers
- **Lightweight** — single `dashboard/app.py` file to start
- **Docker-friendly** — add as another service in docker-compose

---

## All LLM Models

| Model | Provider | Purpose | Cost | Status |
|-------|----------|---------|------|--------|
| `deepseek-ai/deepseek-v3-2` | NVIDIA NIM | Research analysis (primary) | Free tier | ✅ Configured |
| `qwen/qwen3.5-122b-a10b` | NVIDIA NIM | Execution decisions | Free tier | ✅ Configured |
| `meta/llama-3.1-70b-instruct` | NVIDIA NIM | Current working model | Free tier | ✅ Working |
| `stepfun-ai/step-3.5-flash` | NVIDIA NIM | Fallback LLM | Free tier | ❌ Not configured |
| `claude-sonnet-4-6` | Anthropic | Fallback LLM (black swan) | ~₹30/mo | ❌ No API key |
| `gemini-2.5-flash` | Google | ADK native, fast reasoning | Free tier (15 RPM) | 🔜 New |
| `gemini-2.5-pro` | Google | ADK native, deep reasoning | Free tier (2 RPM) | 🔜 New |
| `ProsusAI/finbert` | Hugging Face (local) | Financial sentiment analysis | Free (runs locally) | 🔜 New |
| `google/timesfm-2.5-200m-pytorch` | Google Research (local) | Time-series forecasting (price, volume) | Free (Apache 2.0, runs locally) | 🔜 New |

---

## All ADK Agent Tools (FunctionTools)

| Tool | Module | Input | Output | Purpose | Free/Paid |
|------|--------|-------|--------|---------|-----------|
| `get_eod_data` | `tools/market/market_data.py` | ticker: str | OHLCV + all indicators | Daily candles + technical analysis | ✅ Free (Kite paid) |
| `get_fundamentals` | `tools/market/fundamental_data.py` | ticker: str | PE, EPS, debt, promoter, pledging | 4-layer fundamental fetch | ✅ Free (yfinance) |
| `search_news` | `tools/market/news_search.py` | query: str | List of news articles | Tavily → DDGS fallback | ✅ Free (Tavily free tier) |
| `get_fii_dii` | `tools/market/fii_dii_data.py` | none | FII/DII net flows, sector flows | Institutional flow data | ✅ Free (NSE public) |
| `get_options_data` | `tools/market/options_data.py` | ticker: str | PCR, IV, max pain, OI | Options chain analysis | ✅ Free (Kite paid) |
| `place_order` | `tools/execution/order_execution.py` | ticker, side, qty, type, price | order_id, status, fill_price | Entry order placement | ✅ Free (Kite paid) |
| `place_gtt` | `tools/execution/gtt_manager.py` | ticker, trigger, limit, qty | gtt_id, status | GTT stop/target placement | ✅ Free (Kite paid) |
| `check_risk` | `tools/execution/risk_check.py` | ticker, score, entry, stop | approved/rejected, position_size | Risk gate before orders | ✅ Free |
| `send_alert` | `tools/execution/alerts.py` | message: str, type: str | success: bool | Telegram/FastAPI alerts | ✅ Free |
| `analyze_sentiment` | `tools/analysis/sentiment_analysis.py` | ticker: str | sentiment_score, label, catalyst | Multi-layer sentiment (FinBERT + LLM) | ✅ Free (local FinBERT) |
| `detect_regime` | `tools/analysis/regime_detection.py` | none | regime, confidence, volatility | Market regime classification | ✅ Free |
| `check_correlation` | `tools/analysis/correlation_check.py` | positions: list | correlation_matrix, portfolio_beta | Portfolio correlation check | ✅ Free |
| `check_entry_timing` | `tools/analysis/entry_timing.py` | ticker: str | optimal: bool, reason, wait_minutes | Smart entry timing | ✅ Free |
| `get_macro_indicators` | `tools/macro/macro_data.py` | none | crude, usd_inr, vix, gdp, cpi | Macro data layer | ✅ Free |
| `get_upcoming_events` | `tools/macro/events_calendar.py` | days: int | List of events | RBI, budget, earnings, rebalancing | ✅ Free |
| `forecast_timeseries` | `tools/analysis/timesfm_forecast.py` | ticker: str, horizon: int | point_forecast, quantile_forecast | TimesFM 2.5 price + volume prediction | ✅ Free (local, 200M params) |

---

## All Kite Connect v3 APIs Used

| Kite API | Method | Purpose | Rate Limit | Paid? |
|----------|--------|---------|-----------|-------|
| `/instruments` | GET | Full instrument master list (CSV) | Once/day recommended | ✅ ₹500/mo |
| `/quote` | GET | Full market data (up to 500 instruments) | 10 req/sec | ✅ ₹500/mo |
| `/quote/ohlc` | GET | OHLC snapshots (up to 1000 instruments) | 10 req/sec | ✅ ₹500/mo |
| `/quote/ltp` | GET | LTP only (up to 1000 instruments) | 10 req/sec | ✅ ₹500/mo |
| `/instruments/historical/{token}/{interval}` | GET | Historical candles (minute to daily, years back) | 3 req/sec | ✅ ₹500/mo |
| `/gtt/triggers` | POST/GET | Place/retrieve GTT orders | 10 req/sec | ✅ ₹500/mo |
| `/gtt/triggers/{id}` | GET/PUT/DELETE | Retrieve/modify/delete specific GTT | 10 req/sec | ✅ ₹500/mo |
| `/orders` | POST/GET | Place/retrieve orders | 10 req/sec | ✅ ₹500/mo |
| `/portfolio/positions` | GET | Live positions | 10 req/sec | ✅ ₹500/mo |
| `/portfolio/holdings` | GET | Holdings | 10 req/sec | ✅ ₹500/mo |
| `/user/profile` | GET | User profile verification | 10 req/sec | ✅ ₹500/mo |
| `/margins/equity` | GET | Margin calculation | 10 req/sec | ✅ ₹500/mo |
| WebSocket | WSS | Live tick-by-tick streaming | 3 connections | ✅ ₹500/mo |

---

## All Python Packages

| Package | Version | Purpose | Free/Paid | New? |
|---------|---------|---------|-----------|------|
| `kiteconnect` | >=4.1.0 | Zerodha Kite API client | ✅ Free (Kite sub ₹500/mo) | Existing |
| `google-adk` | >=1.0.0 | Multi-agent orchestration framework | ✅ Free | 🔜 New |
| `fastapi[standard]` | latest | REST API + WebSocket server | ✅ Free | 🔜 New |
| `uvicorn[standard]` | latest | ASGI server for FastAPI | ✅ Free | 🔜 New |
| `litellm` | latest | Unified LLM interface (NIM → ADK bridge) | ✅ Free | 🔜 New |
| `streamlit` | latest | Trading dashboard UI | ✅ Free | 🔜 New |
| `plotly` | >=5.20.0 | Interactive financial charts | ✅ Free | Existing |
| `openai` | >=1.30.0 | OpenAI-compatible SDK (NIM, Groq) | ✅ Free | Existing |
| `anthropic` | >=0.26.0 | Claude SDK (black swan fallback) | ✅ Free SDK, API costs ~₹30/mo | Existing |
| `transformers` | latest | Hugging Face models (FinBERT) | ✅ Free | 🔜 New |
| `tavily-python` | >=0.3.0 | AI-native news search | ✅ Free (1K/mo) | Existing |
| `duckduckgo-search` | >=5.0.0 | Free news fallback | ✅ Free | Existing |
| `feedparser` | latest | RSS feed parsing | ✅ Free | 🔜 New |
| `praw` | latest | Reddit API for social sentiment | ✅ Free | 🔜 New |
| `pytrends` | latest | Google Trends data | ✅ Free | 🔜 New |
| `scikit-learn` | latest | ML models for regime detection | ✅ Free | 🔜 New |
| `scipy` | latest | Statistical tests, correlation | ✅ Free | 🔜 New |
| `python-telegram-bot` | >=21.0 | Telegram alerts | ✅ Free | Existing |
| `pandas` | >=2.0.0 | Data manipulation | ✅ Free | Existing |
| `numpy` | >=1.26.0 | Numerical calculations | ✅ Free | Existing |
| `pandas-ta` | >=0.3.14b | Technical indicators | ✅ Free | Existing |
| `TA-Lib` | >=0.4.28 | Candlestick patterns | ✅ Free (C lib) | Existing |
| `timesfm[torch]` | >=2.5.0 | Google TimesFM 2.5 time-series forecasting (200M params, local) | ✅ Free (Apache 2.0) | 🔜 New |
| `vectorbt` | >=0.25.0 | Portfolio simulation | ✅ Free | Existing |
| `quantstats` | >=0.0.62 | HTML tearsheet | ✅ Free | Existing |
| `optuna` | >=3.6.0 | Bayesian parameter optimization | ✅ Free | Existing |
| `pyarrow` | >=15.0.0 | Parquet caching | ✅ Free | Existing |
| `numba` | >=0.59.0 | JIT compilation | ✅ Free | Existing |
| `tqdm` | >=4.66.0 | Progress bars | ✅ Free | Existing |
| `pyotp` | >=2.9.0 | TOTP for Kite auth | ✅ Free | Existing |
| `pydantic` | >=2.5.0 | Typed config validation | ✅ Free | Existing |
| `PyYAML` | >=6.0.0 | Load config.yaml | ✅ Free | Existing |
| `tenacity` | >=8.2.0 | Retry with backoff | ✅ Free | Existing |
| `aiohttp` | >=3.9.0 | Async HTTP | ✅ Free | Existing |
| `python-dotenv` | >=1.0.0 | Load .env | ✅ Free | Existing |
| `schedule` | >=1.2.0 | Cron-style scheduler | ✅ Free | Existing |
| `loguru` | >=0.7.0 | Structured logging | ✅ Free | Existing |
| `gitpython` | >=3.1.0 | SKILL.md version tagging | ✅ Free | Existing |
| `yfinance` | >=0.2.40 | Fundamentals layer 1 | ✅ Free | Existing |
| `nsepython` | >=2.9 | Fundamentals layer 2 | ✅ Free | Existing |
| `nsetools` | >=0.0.7 | Fundamentals layer 2 supplement | ✅ Free | Existing |
| `firecrawl-py` | >=1.0.0 | Fundamentals layer 3 (AI extraction) | Free tier 500 credits/mo | Existing |
| `beautifulsoup4` | >=4.12.0 | HTML parsing | ✅ Free | Existing |
| `requests` | >=2.31.0 | HTTP calls | ✅ Free | Existing |
| `pytest` | >=8.0.0 | Unit tests | ✅ Free | Existing |
| `pytest-asyncio` | >=0.23.0 | Async test support | ✅ Free | Existing |

---

## Total Monthly Cost

| Item | Cost |
|------|------|
| Zerodha Kite Connect API | ₹500/mo |
| NVIDIA NIM | Free |
| Tavily (1K searches/mo) | Free |
| Google Gemini (ADK) | Free (15 RPM) |
| FinBERT (local) | Free |
| TimesFM 2.5 (local, 200M params) | Free |
| Groq fallback | Free |
| Claude fallback | ~₹30/mo (optional) |
| Firecrawl | Free tier |
| All other packages | Free |
| **TOTAL** | **₹500-530/mo** |

---

## ADK Evaluation Strategy

### What ADK Eval CAN Do (Use It)

| Criterion | What It Measures | Our Use Case |
|-----------|-----------------|-------------|
| `tool_trajectory_avg_score` | Did agent call tools in right order? | Verify research pipeline: regime → data → fundamentals → sentiment → score |
| `rubric_based_tool_use_quality_v1` | LLM-judged tool usage quality | "Did agent check regime before scoring?" "Did agent check risk before ordering?" |
| `hallucinations_v1` | Is response grounded in context? | Detect if agent fabricated data or made unsupported claims |
| `final_response_match_v2` | LLM-judged semantic equivalence | Verify scoring output matches expected format and reasoning |

### What ADK Eval CANNOT Do (Use Existing Backtest Engine)

| Metric | Why ADK Can't Do It | Where It Lives |
|--------|-------------------|---------------|
| P&L calculation | ADK eval doesn't understand financial math | `backtest/metrics.py` (QuantStats) |
| Sharpe ratio | Requires time-series returns analysis | `backtest/metrics.py` |
| Win rate | Requires trade outcome comparison | `backtest/walk_forward.py` |
| Max drawdown | Requires equity curve analysis | `backtest/metrics.py` |
| Profit factor | Requires gross profit/loss calculation | `backtest/metrics.py` |
| Kelly criterion | Requires win rate + avg win/loss | `learning/stats_engine.py` |

**Decision:** Keep existing backtest engine for ALL financial metrics. Use ADK eval ONLY for agent reasoning quality validation.

---

## What Changes vs What Stays

### What Stays Unchanged

| Module | Reason |
|--------|--------|
| `data/kite_fetcher.py` | Kite API client — no change needed |
| `data/indicators/` | Technical indicators — pure computation |
| `data/nifty200_loader.py` | Universe loading — no change needed |
| `data/corporate_actions.py` | Corporate action tracking — no change needed |
| `data/earnings_calendar.py` | Earnings calendar — no change needed |
| `risk/engine.py` | Risk engine — pure computation |
| `risk/position_sizer.py` | Position sizing — pure computation |
| `risk/circuit_breakers.py` | Circuit breakers — pure computation |
| `paper/fill_engine.py` | Paper fill simulation — no change needed |
| `paper/gtt_simulator.py` | GTT simulation — no change needed |
| `paper/slippage_model.py` | Slippage model — no change needed |
| `backtest/` | Entire backtest engine — no change needed |
| `strategy/` | SKILL.md, research_program.md — no change needed |
| `auth/` | Kite authentication — no change needed |
| `integrations/` | Kite MCP client — no change needed |
| `config.py` | Pydantic config loader — minor additions only |
| `config.yaml` | Tunable values — additions only |

### What Gets Replaced

| Old | New | Reason |
|-----|-----|--------|
| `agents/research_agent.py` | ADK SequentialAgent pipeline | Proper orchestration, evaluation |
| `agents/execution_agent.py` | ADK LoopAgent + LlmAgents | Human-in-the-loop, state management |
| `agents/reconciler.py` | ADK position checker agent | Integrated into execution monitor |
| `llm/nim_client.py` | ADK LlmAgent + LiteLLM | Model-agnostic, better tool handling |
| `llm/router.py` | ADK model config + LiteLLM | Built-in fallback support |
| `llm/tool_executor.py` | ADK tool-call loop | ADK handles tool execution natively |
| `llm/prompt_builder.py` | ADK instruction parameter | ADK handles prompt assembly |
| `notifications/telegram_handler.py` | ADK human-in-the-loop + FastAPI | Proper approval flow |
| `notifications/telegram_commands.py` | FastAPI routes | REST API for all commands |
| `notifications/formatter.py` | FastAPI Pydantic schemas | Structured API responses |
| `learning/` (4 files) | ADK learning agents | Proper agent-based learning |
| `context/state.json` | ADK session.state + file callback | Built-in state management |
| `context/pending_approvals.json` | ADK human-in-the-loop | Proper approval flow |

### What Gets Enhanced

| Module | Enhancement |
|--------|-------------|
| `data/indicators/volume.py` | Add VWAP, CMF, volume profile |
| `data/indicators/relative_strength.py` | Add multi-benchmark RS, RS rank |
| `tools/market_data.py` | Add multi-timeframe support |
| `tools/fundamental_data.py` | Add earnings quality analysis |
| `risk/engine.py` | Add regime-adjusted sizing |

---

## Migration Plan: Phased Approach

### Phase 1: Foundation (Week 1-2)

**Goal:** Add FastAPI layer + ADK scaffolding without breaking existing code.

| Task | Files | Effort |
|------|-------|--------|
| Add FastAPI app + basic routes | `api/` module | 2 days |
| Add ADK dependency + root agent | `agents/root.py` | 1 day |
| Migrate config for ADK | `config.py`, `config.yaml` | 0.5 day |
| Add LiteLLM integration | `agents/models.py` | 1 day |
| Test FastAPI endpoints | `tests/test_api/` | 2 days |
| WebSocket for alerts | `api/routes/ws.py` | 1 day |
| Background task scheduler | `api/tasks.py` | 1 day |
| Streamlit dashboard skeleton | `dashboard/` | 2 days |

**Deliverable:** Running FastAPI server + Streamlit dashboard with existing agents triggered via API endpoints.

### Phase 2: Research Pipeline Migration (Week 3-4)

**Goal:** Replace `research_agent.py` with ADK SequentialAgent pipeline.

| Task | Files | Effort |
|------|-------|--------|
| Create multi-signal filter agent | `agents/research/filter_agent.py` | 2 days |
| Implement TimesFM forecaster | `data/timesfm_forecaster.py` | 1 day |
| Implement TimesFM forecast tool | `tools/analysis/timesfm_forecast.py` | 1 day |
| Implement TimesFM agent | `agents/research/timesfm_agent.py` | 1 day |
| Create regime detection agent | `agents/research/regime_agent.py` | 1 day |
| Create market data agent | `agents/research/market_data_agent.py` | 1 day |
| Create fundamentals agent | `agents/research/fundamentals_agent.py` | 1 day |
| Create sentiment agent | `agents/research/sentiment_agent.py` | 2 days |
| Create options agent | `agents/research/options_agent.py` | 1 day |
| Create scorer agent | `agents/research/scorer_agent.py` | 1 day |
| Create dynamic batch scanner | `agents/research/scanner.py` | 1 day |
| Wire SequentialAgent pipeline | `agents/research/pipeline.py` | 1 day |
| Add sentiment analysis tool | `tools/analysis/sentiment_analysis.py` | 2 days |
| Add regime detection tool | `tools/analysis/regime_detection.py` | 1 day |
| Test research pipeline | `tests/test_agents/test_research_pipeline.py` | 2 days |

**Deliverable:** ADK-based research pipeline with regime detection, multi-signal funnel, sentiment analysis, TimesFM forecasting, and parallel scanning.

### Phase 3: Execution + Learning Migration (Week 5-6)

**Goal:** Replace `execution_agent.py` + learning modules with ADK agents.

| Task | Files | Effort |
|------|-------|--------|
| Create execution monitor (LoopAgent) | `agents/execution/monitor.py` | 2 days |
| Create order agent with human-in-loop | `agents/execution/order_agent.py` | 2 days |
| Create GTT agent | `agents/execution/gtt_agent.py` | 1 day |
| Create exit intelligence agent | `agents/execution/exit_agent.py` | 1 day |
| Create trade reviewer agent | `agents/learning/reviewer.py` | 1 day |
| Create stats agent | `agents/learning/stats_agent.py` | 1 day |
| Create lesson agent | `agents/learning/lesson_agent.py` | 1 day |
| Wire ADK human-in-the-loop | `api/routes/approvals.py` | 2 days |
| Add correlation checker tool | `tools/analysis/correlation_check.py` | 1 day |
| Add entry timing tool | `tools/analysis/entry_timing.py` | 1 day |
| Test execution + learning | `tests/test_agents/` | 2 days |

**Deliverable:** Complete ADK-based system with execution monitoring, human-in-the-loop approvals, and learning loop.

### Phase 4: Evaluation + Polish (Week 7-8)

**Goal:** ADK evaluation framework + production readiness.

| Task | Files | Effort |
|------|-------|--------|
| Set up ADK evaluation framework | `tests/test_evaluation/` | 2 days |
| Create agent decision tests | `tests/test_evaluation/test_agent_decisions.py` | 2 days |
| Create backtest evaluation | `tests/test_evaluation/test_backtest_eval.py` | 2 days |
| Add API authentication | `api/middleware/auth.py` | 1 day |
| Add rate limiting | `api/middleware/rate_limit.py` | 0.5 day |
| Docker updates | `Dockerfile`, `docker-compose.yml` | 1 day |
| Streamlit dashboard full implementation | `dashboard/` | 2 days |
| Documentation | `docs/` | 1 day |
| End-to-end testing | Manual + automated | 2 days |

**Deliverable:** Production-ready system with evaluation framework, security, documentation, and full dashboard.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| ADK v1.0 breaking changes | Medium | High | Pin version, test thoroughly, keep fallback |
| LiteLLM + NIM compatibility | Low | Medium | Test all model calls before deployment |
| Migration complexity | High | High | Phased approach, keep old code until new works |
| Performance regression | Low | Medium | Benchmark ADK vs current, optimize hot paths |
| Team learning curve | Medium | Medium | ADK docs are good, start with simple agents |
| FastAPI deployment | Low | Low | FastAPI is well-documented, standard patterns |
| Streamlit performance | Low | Low | Streamlit is lightweight for single-user dashboards |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| All existing tests pass | 100% |
| Research pipeline produces same/better scores | ≥ current baseline |
| API response time < 500ms for all endpoints | P95 < 500ms |
| Dashboard load time < 2s | P95 < 2s |
| Agent decision evaluation score | ≥ 0.7 accuracy |
| Zero data loss during migration | 100% state preserved |
| Backtest results unchanged | Same trades, same P&L |

---

## Rollback Plan

If any phase fails:

1. **Phase 1 failure:** Remove `api/` and `dashboard/` modules, keep existing code unchanged
2. **Phase 2 failure:** Keep old `research_agent.py`, remove ADK research agents
3. **Phase 3 failure:** Keep old `execution_agent.py`, remove ADK execution agents
4. **Phase 4 failure:** Skip evaluation, deploy without it

Each phase is independently deployable and rollbackable.

---

## Open Questions

1. **ADK session persistence format:** Should we use a single `session.json` file or split by session type (research, execution, learning)?
2. **WebSocket alert format:** Should alerts be JSON objects with typed payloads or simple text strings?
3. **Dashboard auth:** Should the Streamlit dashboard require authentication or trust local network access?
4. **ADK model routing:** Should we use LiteLLM for all models or keep direct NIM calls for the research agent (proven path)?

---

*Created: April 4, 2026*
*Version: 2.0 — Complete with separation of concerns, 24-hour cycle, multi-signal funnel*
*Status: Approved — ready for phased implementation*
