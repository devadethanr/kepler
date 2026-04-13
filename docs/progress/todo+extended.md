# swingtradev3 — Extended TODOs (Phases 4-5)

> Continuation of [todos.md](file:///home/devadethanr/projects/kepler/docs/progress/todos.md)
> Based on deep code audit + institutional grade assessment + feasibility review
> Last Updated: April 13, 2026

---

## Phase 4: Remaining Items — Polish

- [ ] Update `docs/README.md` with v2 architecture
- [ ] Create `docs/api.md` — API reference
- [ ] Final E2E Backtest vs Baseline validation

---

## Phase 5A: Critical Bug Fixes (Day 1) ✅

**Goal:** Fix all 8 bugs from the deep code audit. Zero new features.

### 5A.1 Runtime Crash Fix
- [x] `health_manager.py` — Add `Any` to imports (line 1)
- [x] Verify: import module without error

### 5A.2 LLM Bridge Fixes
- [x] `llm_bridge.py` — Fix retry decorator to catch NIM exceptions (`httpx.HTTPStatusError`) alongside `ServerError`
- [x] `llm_bridge.py` — Fix provider detection: use provider chain membership instead of `"meta" in model_str`
- [x] Verify: fallback chain works when NIM is down

### 5A.3 Scan Pipeline Fixes
- [x] `scan.py` — Use unique session IDs: `f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`
- [x] `scan.py` — Persist `scan_status_store` to `context/scan_status.json`
- [x] `scan.py` — Add `asyncio.Lock` concurrency guard
- [x] Verify: two concurrent scan requests don't corrupt state

### 5A.4 Security Hardening
- [x] `api/main.py` — Restrict CORS origins to dashboard URL
- [x] `api/main.py` — Remove `str(exc)` from global exception handler
- [x] Verify: CORS blocks random origins

### 5A.5 Morning Briefing
- [x] `morning_briefing.py` — Wire `TelegramClient.send_message()` with ngrok link
- [x] Verify: Telegram receives morning briefing message

### 5A.6 Run Tests
- [x] Run `make test` — All existing 57 tests still pass
- [x] No regressions from bug fixes

---

## Phase 5B: Knowledge Graph Engine (Days 2-4) ✅

**Goal:** Karpathy-style markdown knowledge graph. The "brain" of the professional trader.

### 5B.1 Infrastructure Updates
- [x] Update `paths.py` — Add `KNOWLEDGE_DIR = CONTEXT_DIR / "knowledge"`
- [x] Update `ensure_runtime_dirs()` — Create all knowledge subdirectories on startup

### 5B.2 Directory Structure
- [x] Create `context/knowledge/wiki/stocks/`
- [x] Create `context/knowledge/wiki/sectors/`
- [x] Create `context/knowledge/wiki/themes/`
- [x] Create `context/knowledge/wiki/trade_journal/`
- [x] Create `context/knowledge/raw/scans/`
- [x] Create `context/knowledge/raw/news/`
- [x] Create `context/knowledge/_index.json` — Empty initial index `{}`
- [x] Create `context/knowledge/_graph.json` — Empty initial graph `{"nodes":[],"edges":[]}`

### 5B.3 Models
- [x] Create `knowledge/__init__.py`
- [x] Create `knowledge/knowledge_models.py`
  - [x] `StockFrontmatter` — Pydantic model for YAML frontmatter
  - [x] `ScanHistoryEntry` — date, score, shortlisted, setup type
  - [x] `TradeJournalEntry` — entry, exit, P&L, reasoning, lessons
  - [x] `StockContext` — context model for LLM injection
  - [x] `GraphNode`, `GraphEdge` — for dashboard visualization

### 5B.4 Wiki Renderer
- [x] Create `knowledge/wiki_renderer.py`
  - [x] `read_note(filepath) → (frontmatter, body)` — Parse YAML frontmatter + markdown body
  - [x] `write_note(filepath, frontmatter, body)` — Render back to markdown
  - [x] `upsert_stock_note(ticker, scan_result)` — Create/update with scan history table
  - [x] `build_scan_history_table()` — Markdown table from scan entries
  - [x] `update_index()` / `update_graph()` — Maintain JSON indexes

### 5B.5 Knowledge Graph Agent
- [x] Create `agents/research/knowledge_graph_agent.py`
  - [x] `KnowledgeGraphAgent(BaseAgent)` with `_run_async_impl`
  - [x] Reads scan results from context, calls `upsert_stock_note()` for each
  - [x] `get_stock_context(ticker) → StockContext` — Historical context for LLM
  - [x] `format_context_for_llm(ticker) → str` — Formatted string for system prompt

### 5B.6 Pipeline Integration (CORRECTED ORDER)
> ScorerAgent calls `get_stock_context()` **inline** before scoring.
> KnowledgeGraphAgent runs **after** ResultsSaverAgent to WRITE new data.

- [x] `scorer_agent.py` — Injects historical context into system instruction
- [x] `pipeline.py` — KnowledgeGraphAgent as 6th sub-agent (6 total)
- [x] Verify: 19/19 targeted tests pass in 3.9s

### 5B.7 Tests
- [x] Create `tests/test_knowledge_graph.py` — 16 tests
  - [x] StockFrontmatter defaults, ScanHistoryEntry, GraphNode models
  - [x] Write/read notes, parse scan history, build tables
  - [x] Upsert creates new, upsert updates existing
  - [x] Get stock context (no history / with history)
  - [x] Format context for LLM
  - [x] Index and graph updated on upsert
  - [x] Trade journal creation
- [x] Run `make test` — All tests pass ✅

---

## Phase 5C: 24-Hour Scheduler + Event Bus (Days 4-6) ✅

**Goal:** Complete autonomous cycle. System operates 24/7 with reactive capabilities.

### 5C.1 Docker Timezone Fix
- [x] Use `ZoneInfo("Asia/Kolkata")` in scheduler (handled in code, no Docker env needed)
- [x] Add `TZ=Asia/Kolkata` to `docker-compose.dev.yml` environment for `app` service
- [ ] Add `TZ=Asia/Kolkata` to `docker-compose.dev.yml` environment for `dashboard` service
- [x] Verify: `datetime.now()` inside Docker returns IST times

### 5C.2 Agent Activity Manager
- [x] Create `api/tasks/activity_manager.py`
  - [x] `AgentActivityManager` singleton class
  - [x] `start(agent_name, description)` — Register agent start
  - [x] `complete(agent_name, result, status)` — Register completion
  - [x] `get_all() → List[AgentStatus]` — Current agent statuses
  - [x] `get_history(limit) → List[AgentRun]` — Recent run history
  - [x] Persist to `context/agent_activity.json`
- [x] Wire into existing agents: ScorerAgent, FilterAgent, ExecutionMonitor, TradeReviewer
- [x] Verify: `context/agent_activity.json` updates on agent runs

### 5C.3 Event Bus with Recovery
- [x] Create `api/tasks/event_bus.py`
  - [x] `TradingEvent` — Base event model with type, timestamp, data
  - [x] `EventBus` class with async pub/sub
  - [x] `emit(event)` — Push event
  - [x] `subscribe(event_type, handler)` — Register handler
  - [x] `get_recent()` — Event history query
  - [x] Persistent JSONL event log for crash recovery
  - [x] `load_history()` — Restore from disk on startup
- [x] **Failed Event Recovery:**
  - [x] On handler failure: persist event to `context/failed_events.json` with error message
  - [x] On startup: load `context/failed_events.json`, show count in dashboard + send Telegram alert
  - [x] Auto-retry logic: retry failed events up to 3 times with exponential backoff
  - [x] If all retries fail: mark as `permanently_failed`, alert user via Telegram with details
  - [x] Dashboard page shows failed events with manual "Retry" button
  - [x] Telegram alert format: `"⚠️ {count} event(s) failed to process. View: {dashboard_link}/agent-activity"`
- [x] Event handlers:
  - [x] `handle_gtt_triggered` — Log trade, update state, send Telegram
  - [x] `handle_vix_spike` — Tighten stops 20%, pause new entries
  - [x] `handle_position_news` — Alert on Telegram
  - [x] `handle_stop_hit` — Log observation, update knowledge graph
  - [x] `handle_target_hit` — Log success, update knowledge graph
  - [x] `handle_auth_expiring` — Alert user on Telegram
  - [x] `handle_regime_change` — Adjust config via RegimeAdapter
- [x] Wire event bus startup in `api/main.py` lifespan
- [x] Wire failed event recovery check on startup
- [x] Verify: emit event → handler executes
- [x] Verify: handler failure → event persisted → Telegram alert sent → dashboard shows it

### 5C.4 Regime Adapter
- [x] Create `regime_adapter.py`
  - [x] `RegimeAdaptiveConfig` — Overlay that adjusts config based on regime
  - [x] Bull: 100% size, 7.0 min score, normal stops
  - [x] Neutral: 75% size, 7.5 min score, +10% tighter stops
  - [x] Bear: 50% size, 8.0 min score, +20% tighter stops
  - [x] Choppy: 0% size (paused), 9.0 min score, +30% tighter stops
- [ ] Wire into research pipeline (use adapted config for scoring threshold)
- [ ] Wire into execution agent (use adapted config for position sizing)
- [x] Verify: changing regime changes effective config values

### 5C.5 Extend Scheduler (Keep `schedule` library)
> **Decision:** Keep the existing `schedule` library (proven to work with asyncio.create_task).
> Do NOT switch to APScheduler (thread issues with FastAPI event loop).

- [x] Extend `scheduler.py` — Rewrite with full `TradingScheduler` class (6 phases)
- [x] Phase 1 (Overnight 10PM-6AM):
  - [x] News sweep for held positions
  - [x] GIFT Nifty, global markets monitoring
- [x] Phase 2 (Pre-Market 6AM-9:15AM):
  - [x] Morning briefing generation → Telegram (already exists)
  - [x] Regime check
  - [x] `schedule.every().day.at("06:30").do(self._fii_dii_check)` — FII/DII data
  - [x] Review pending approvals status
- [x] Phase 3 (Market Hours 9:15AM-3:30PM):
  - [x] `schedule.every(15).minutes.do(self._position_monitor)` — Position monitor
  - [x] Add market hours guard: skip if outside 9:15-3:30 IST
  - [x] Trailing stop adjustment
  - [x] VIX monitoring (emit VIX_SPIKE event if VIX > 20)
  - [x] Position news sweep (for held tickers)
- [x] Phase 4 (Post-Market 3:30PM-6PM):
  - [x] EOD data collection
  - [x] Final FII/DII numbers
  - [x] P&L calculation
  - [x] Position reconciliation
- [x] Phase 5 (Evening 6PM-9PM):
  - [x] Full research pipeline trigger
  - [x] Knowledge graph update (Phase 5B)
- [x] Phase 6 (Wind-Down 9PM-10PM):
  - [x] State persistence / snapshot
  - [x] Daily summary → Telegram
  - [x] Log rotation
  - [x] Next-day prep
- [x] Wire `ExecutionMonitor` for 15-min intraday polling
- [x] Verify: scheduler logs show all 6 phases registered

### 5C.5b Dashboard API Routes (added during build)
- [x] Create `api/routes/dashboard.py`
  - [x] `GET /dashboard/knowledge/index` — Full KG index
  - [x] `GET /dashboard/knowledge/graph` — KG nodes + edges
  - [x] `GET /dashboard/knowledge/stock/{ticker}` — Stock context
  - [x] `GET /dashboard/activity` — Agent activity snapshot
  - [x] `GET /dashboard/events` — Recent event bus events
  - [x] `GET /dashboard/scheduler` — Scheduler phase + job count
- [x] Register routes in `api/main.py`

### 5C.6 Monitor Agent Update
- [x] `monitor.py` — Add GTT trigger detection (poll Kite orders)
- [x] `monitor.py` — Emit events (STOP_HIT, TARGET_HIT) to event bus
- [x] `monitor.py` — Register with AgentActivityManager
- [x] `monitor.py` — Add market hours guard: skip monitoring outside 9:15-3:30 IST
- [x] Verify: GTT fill detected → event emitted → handler runs

### 5C.7 Tests
- [x] Create `tests/test_scheduler_eventbus.py` — 15 tests
  - [x] Event pub/sub, multiple handlers, error isolation
  - [x] Unsubscribe, get_recent, event types enum
  - [x] Activity start/complete/error/progress/phase
  - [x] Scheduler phase detection (all 7 IST boundaries)
  - [x] Scheduler init state, schedule info
- [x] Run tests — 31/31 pass in 0.76s ✅
- [x] Create `tests/test_5c_completion.py`
  - [x] Test failed event persistence to JSON
  - [x] Test auto-retry with exponential backoff
  - [x] Test permanent failure after 3 retries
  - [x] Test startup recovery of failed events
- [x] Create regime adapter tests (in same file)
  - [x] All 4 regime overlays
  - [x] Alias resolution
  - [x] Stop tightening math
  - [x] Position sizing

---

## Phase 5D: Reflex Dashboard (Days 6-10)

**Goal:** Professional, mobile-responsive dashboard as separate Docker service.

### 5D.1 Docker Infrastructure
- [ ] Create `Dockerfile.dashboard` — Python 3.12 + Node.js 20 + Reflex
  - [ ] Install Node.js 20.x via nodesource
  - [ ] Install Reflex via pip
  - [ ] Pre-compile Reflex on build (`reflex init`)
  - [ ] Expose port 3000 (Reflex frontend)
- [ ] Update `docker-compose.dev.yml`:
  - [ ] Remove Streamlit from `app` service command (FastAPI only)
  - [x] Add `dashboard` service using `Dockerfile.dashboard`
  - [x] Port mapping: `8502:3000` (Reflex frontend → host)
  - [x] Environment: `FASTAPI_URL=http://app:8000`, `TZ=Asia/Kolkata`
  - [x] `depends_on: [app]`
  - [x] Volume mount for hot reload: `./swingtradev3/dashboard_v2:/app/dashboard_v2`
- [x] Update `Makefile` — Add `make dashboard` command
- [ ] Verify: `docker-compose up` starts both containers, dashboard at `localhost:8502`

### 5D.2 Reflex Project Setup
- [x] Initialize Reflex project: `swingtradev3/dashboard/`
- [x] Configure `rxconfig.py` — API port 3000, production settings
- [x] Create `dashboard/requirements.txt` — Reflex, plotly, httpx
- [x] Verify: `reflex run` works inside Docker

### 5D.3 Theme & Design System
- [x] Create `dashboard/styles.py` — Dark theme, colors, typography
  - [x] Color palette: pure black, deep purple, emerald green, golden yellow
  - [x] Typography: Inter/Outfit from Google Fonts
  - [x] Component variants: cards, badges, gauges
- [x] Create `dashboard/state.py` — Global app state
  - [x] API client wrapper (`httpx` calls to FastAPI at `FASTAPI_URL`)
  - [x] API key header injection
  - [x] Agent status state via SSE
  - [x] Portfolio state
  - [x] Knowledge graph state
  - [x] Auto-refresh polling (via SSE event handlers)

### 5D.4 Reusable Components
- [x] Create `components/sidebar.py` — Navigation + system health indicators
- [x] Create `components/metric_card.py` — KPI display (P&L, win rate, etc.)
- [x] Create `components/agent_badge.py` — Agent status (✅ idle / 🔄 running / ❌ error)
- [ ] Create `components/stock_card.py` — Research result card with score gauge
- [ ] Create `components/trade_card.py` — Trade detail expandable card
- [x] Create `components/pipeline_flow.py` — Agent sequence visualization

### 5D.5 Pages
- [x] **🏠 Command Center** (`command_center.py`)
  - [x] System pipeline visualizer
  - [x] Component grid mapping
  - [x] Agent status grid
  - [x] Today's P&L summary
  - [ ] Open positions count
  - [ ] Next scheduled task countdown
  - [ ] Recent activity timeline (24hr)
  - [ ] Failed events alert banner (if any)
- [ ] **📊 Portfolio** (`portfolio.py`)
  - [ ] Active positions table with P&L
  - [ ] Position cards (mobile-friendly)
  - [ ] Sector exposure donut chart (Plotly)
  - [ ] Risk utilization gauge
- [ ] **🔍 Research** (`research.py`)
  - [ ] Latest scan results in card grid
  - [ ] Score gauge, bull/bear summary
  - [ ] Historical score trend from knowledge graph
  - [ ] Filter by score, sector, setup type
  - [ ] Drill-down to stock knowledge note
- [ ] **⚙️ Approvals** (`approvals.py`)
  - [ ] Pending trades with approve/reject buttons
  - [ ] Risk context: "This uses X% of remaining risk budget"
  - [ ] Knowledge context: "Traded 2x before, 100% win rate"
  - [ ] Mobile tap-to-approve
- [ ] **📈 Trade Journal** (`trade_journal.py`)
  - [ ] Equity curve chart (Plotly, from real data)
  - [ ] All trades table
  - [ ] Stats: win rate, avg win/loss, Sharpe, max DD
  - [ ] Expandable trade details
- [ ] **🧠 Knowledge Graph** (`knowledge_graph.py`)
  - [ ] Interactive force-directed graph
  - [ ] Nodes: Stocks, Sectors, Themes, Trades
  - [ ] Click node → sidebar with full note
  - [ ] Search bar
  - [ ] Filter by entity type
- [ ] **🤖 Agent Activity** (`agent_activity.py`)
  - [ ] Pipeline flowchart with step highlighting
  - [ ] Currently running agents
  - [ ] Run history table
  - [ ] Error log viewer
  - [ ] Failed events list with manual "Retry" button
- [ ] **📖 Learning** (`learning.py`)
  - [ ] Trade observations list
  - [ ] Performance stats
  - [ ] SKILL.md content + staging diff
  - [ ] Learning timeline

### 5D.6 API Routes for Dashboard
- [ ] Create/update API routes to serve:
  - [ ] `GET /api/agent-activity` — Current agent statuses + history
  - [ ] `GET /api/knowledge-graph` — Graph data (nodes + edges)
  - [ ] `GET /api/knowledge/stock/{ticker}` — Individual stock note (markdown rendered)
  - [ ] `GET /api/portfolio/summary` — Real-time P&L + positions
  - [ ] `GET /api/stats` — Performance metrics
  - [ ] `GET /api/failed-events` — Failed events list
  - [ ] `POST /api/failed-events/{id}/retry` — Manual retry of a failed event
- [ ] Verify: all endpoints return correct data

### 5D.7 ngrok Integration
- [ ] Create `ngrok.yml` config
- [ ] Add `make tunnel` and `make tunnel-bg` to Makefile
- [ ] Add ngrok URL auto-capture script: `ngrok http 8502 --log=stdout | grep url`
- [ ] Store ngrok URL in `context/ngrok_url.txt` for Telegram links
- [ ] Verify: dashboard accessible from phone via ngrok URL

### 5D.8 Mobile Responsiveness
- [ ] Test all pages on mobile viewport (375px)
- [ ] Verify: cards stack vertically, charts resize, navigation works
- [ ] Verify: approvals page usable on phone

---

## Phase 5E: Telegram Notifications Only (Days 10-11)

**Goal:** One-way Telegram alerts with ngrok dashboard links. Approvals via dashboard only.

### 5E.1 Client Simplification
- [ ] `telegram_client.py` — Remove:
  - [ ] `send_approval_request()` (approvals now via dashboard)
  - [ ] `send_text_with_keyboard()` (no more inline buttons)
  - [ ] `get_updates()` (no polling for callbacks)
  - [ ] `answer_callback_query()` (no callback handling)
  - [ ] `edit_message_text()` (no message editing)
- [ ] Keep:
  - [ ] `send_text()` — Core notification method
  - [ ] `send_entry_alert()` — Trade executed alert
  - [ ] `send_profit_alert()` — Target/stop hit alert
  - [ ] `send_briefing()` — Morning briefing
  - [ ] `send_daily_summary()` — EOD summary
  - [ ] `send_system_status()` — System warnings
  - [ ] `send_no_setup()` — No setup found alert
- [ ] Add new methods:
  - [ ] `send_failed_event_alert(count, details)` — Failed events notification
  - [ ] `send_vix_alert(vix_level, action_taken)` — VIX spike alert
  - [ ] `send_regime_change(old_regime, new_regime)` — Regime change alert
  - [ ] `send_auth_expiry_warning(hours_remaining)` — Auth token expiring
- [ ] All messages include ngrok dashboard link at bottom

### 5E.2 Formatter Update
- [ ] `formatter.py` — Add formatting for new alert types
- [ ] All messages end with: `"\n📊 Dashboard: {ngrok_url}"`
- [ ] Include deep links to specific dashboard pages where relevant
- [ ] Verify: messages render correctly in Telegram

### 5E.3 Wire All Alert Sources
- [ ] Morning briefing → Telegram
- [ ] Event bus handlers → Telegram (all event types)
- [ ] Scheduler end-of-day → Telegram
- [ ] Failed event recovery → Telegram alert with count + dashboard link
- [ ] Verify: all 10 alert types actually send

---

## Phase 5F: Comprehensive Tests (Days 11-14)

**Goal:** Full test coverage for all new components.

### 5F.1 New Test Files
- [ ] `tests/test_agents/test_knowledge_graph.py` — Note CRUD, index, graph, context
- [ ] `tests/test_agents/test_wiki_renderer.py` — Frontmatter parsing, rendering, wikilink extraction
- [ ] `tests/test_event_bus.py` — Event emission, handlers, failure recovery, retry logic
- [ ] `tests/test_scheduler.py` — All 6 phases, market hours guard
- [ ] `tests/test_regime_adapter.py` — Regime → config overlay, sizing, entry pause
- [ ] `tests/test_agents/test_order_agent.py` — Order placement, risk, approvals
- [ ] `tests/test_integration/test_full_pipeline.py` — End-to-end scan → KG → dashboard data

### 5F.2 Integration Testing
- [ ] Full pipeline: Scan → Filter → Scanner → Scorer(+KG context) → Saver → KG update → Dashboard data
- [ ] Event flow: GTT trigger → Event bus → Handler → Telegram + State update
- [ ] Event recovery: Handler failure → Persist → Startup retry → Dashboard alert
- [ ] Scheduler: Verify all phases trigger at correct times (mocked clock, IST timezone)

### 5F.3 Final Validation
- [ ] Run `make test` — ALL tests pass (target: 85+ tests)
- [ ] Run `make dev` — Both containers start without errors
- [ ] Open dashboard at `localhost:8502` → verify all 8 pages functional
- [ ] Trigger scan → watch Agent Activity page update
- [ ] Check Knowledge Graph page → verify nodes/edges
- [ ] `make tunnel` → open on phone → verify mobile layout
- [ ] Check Telegram → verify all notification types received (no approval buttons)
- [ ] Simulate failed event → verify dashboard shows it + Telegram alert
- [ ] Run for 24 hours → verify scheduler completes full cycle

---

## Summary Timeline

| Phase | Status | Days | Deliverable |
|-------|--------|------|-------------|
| **Phase 0** | ✅ 100% | — | Dev environment, Docker, API keys |
| **Phase 1** | ✅ 100% | — | FastAPI + ADK + Dashboard skeleton |
| **Phase 2** | ✅ 100% | — | Research pipeline + TimesFM |
| **Phase 3** | ✅ 100% | — | Execution + Learning agents |
| **Phase 4** | 🔄 95% | — | Evaluation + Production hardening |
| **Phase 5A** | ✅ 100% | 1 | Bug fixes (8 critical) — All 57 tests pass |
| **Phase 5B** | ✅ 100% | 3 | Knowledge Graph Engine — 16 KG tests pass |
| **Phase 5C** | 🔄 60% | 3 | Scheduler V2 (6-phase) + Event Bus — core built, handlers/adapter/monitor pending |
| **Phase 5D** | ⬜ 0% | 5 | Reflex Dashboard (separate Docker + Dockerfile.dashboard) |
| **Phase 5E** | ⬜ 0% | 1 | Telegram notifications only (no approvals) |
| **Phase 5F** | ⬜ 0% | 3 | Comprehensive tests (85+ target) |
