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

## Phase 5A: Critical Bug Fixes (Day 1)

**Goal:** Fix all 8 bugs from the deep code audit. Zero new features.

### 5A.1 Runtime Crash Fix
- [ ] `health_manager.py` — Add `Any` to imports (line 1)
- [ ] Verify: import module without error

### 5A.2 LLM Bridge Fixes
- [ ] `llm_bridge.py` — Fix retry decorator to catch NIM exceptions (`httpx.HTTPStatusError`) alongside `ServerError`
- [ ] `llm_bridge.py` — Fix provider detection: use provider chain membership instead of `"meta" in model_str`
- [ ] Verify: fallback chain works when NIM is down

### 5A.3 Scan Pipeline Fixes
- [ ] `scan.py` — Use unique session IDs: `f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"`
- [ ] `scan.py` — Persist `scan_status_store` to `context/scan_status.json`
- [ ] `scan.py` — Add `asyncio.Lock` concurrency guard
- [ ] Verify: two concurrent scan requests don't corrupt state

### 5A.4 Security Hardening
- [ ] `api/main.py` — Restrict CORS origins to dashboard URL
- [ ] `api/main.py` — Remove `str(exc)` from global exception handler
- [ ] Verify: CORS blocks random origins

### 5A.5 Morning Briefing
- [ ] `morning_briefing.py` — Wire `TelegramClient.send_message()` with ngrok link
- [ ] Verify: Telegram receives morning briefing message

### 5A.6 Run Tests
- [ ] Run `make test` — All existing 57 tests still pass
- [ ] No regressions from bug fixes

---

## Phase 5B: Knowledge Graph Engine (Days 2-4)

**Goal:** Karpathy-style markdown knowledge graph. The "brain" of the professional trader.

### 5B.1 Infrastructure Updates
- [ ] Update `paths.py` — Add `KNOWLEDGE_DIR = CONTEXT_DIR / "knowledge"`
- [ ] Update `ensure_runtime_dirs()` — Create all knowledge subdirectories on startup

### 5B.2 Directory Structure
- [ ] Create `context/knowledge/wiki/stocks/`
- [ ] Create `context/knowledge/wiki/sectors/`
- [ ] Create `context/knowledge/wiki/themes/`
- [ ] Create `context/knowledge/wiki/trade_journal/`
- [ ] Create `context/knowledge/raw/scans/`
- [ ] Create `context/knowledge/raw/news/`
- [ ] Create `context/knowledge/_index.json` — Empty initial index `{}`
- [ ] Create `context/knowledge/_graph.json` — Empty initial graph `{"nodes":[],"edges":[]}`

### 5B.3 Models
- [ ] Create `agents/knowledge/__init__.py`
- [ ] Create `agents/knowledge/knowledge_models.py`
  - [ ] `StockNote` — Pydantic model for YAML frontmatter
  - [ ] `ScanHistoryEntry` — date, score, shortlisted, setup type
  - [ ] `TradeJournalEntry` — entry, exit, P&L, reasoning, lessons
  - [ ] `KnowledgeIndex` — master index model (ticker → metadata)
  - [ ] `GraphNode`, `GraphEdge` — for dashboard visualization

### 5B.4 Wiki Renderer
- [ ] Create `agents/knowledge/wiki_renderer.py`
  - [ ] `parse_note(filepath) → StockNote` — Parse YAML frontmatter + markdown body
  - [ ] `render_note(StockNote) → str` — Render Pydantic model back to markdown
  - [ ] `extract_wikilinks(content) → List[str]` — Parse `[[links]]`
  - [ ] `build_graph_from_directory() → GraphData` — Walk all notes, extract nodes/edges

### 5B.5 Knowledge Graph Agent
- [ ] Create `agents/knowledge/knowledge_graph.py`
  - [ ] `KnowledgeGraphAgent(BaseAgent)` with `_run_async_impl`
  - [ ] `update_stock_note(ticker, scan_result)` — Create/update stock markdown
  - [ ] `create_trade_journal(trade)` — Create post-mortem with `[[wikilinks]]`
  - [ ] `get_stock_context(ticker) → str` — Return historical context for LLM (reads EXISTING notes from previous scans)
  - [ ] `update_index()` — Maintain `_index.json`
  - [ ] `update_graph()` — Maintain `_graph.json`
  - [ ] `update_sector_notes()` — Aggregate stock notes by sector

### 5B.6 Pipeline Integration (CORRECTED ORDER)
> **Key fix:** ScorerAgent calls `get_stock_context()` **inline** before scoring each stock.
> KnowledgeGraphAgent runs **after** ResultsSaverAgent to WRITE new data.
> This works because `get_stock_context()` reads from PREVIOUS scans' markdown files.

Pipeline order:
```
RegimeAgent → FilterAgent → BatchScannerAgent → ScorerAgent(+inline KG read) → ResultsSaverAgent → KnowledgeGraphAgent(writes)
```

- [ ] `scorer_agent.py` — Call `KnowledgeGraphAgent.get_stock_context(ticker)` **inline** before scoring each stock
  - First scan: empty context (fine, no previous data)
  - Subsequent scans: reads history from previous scan's markdown files
- [ ] `pipeline.py` — Add `KnowledgeGraphAgent` as 6th sub-agent after `ResultsSaverAgent` (WRITES only)
- [ ] `reviewer.py` — Call `create_trade_journal()` after reviewing a trade
- [ ] Verify: scan produces stock markdown notes
- [ ] Verify: `_index.json` and `_graph.json` populated after scan
- [ ] Verify: second scan shows historical context in ScorerAgent logs

### 5B.7 Tests
- [ ] Create `tests/test_agents/test_knowledge_graph.py`
  - [ ] Test stock note creation from scratch
  - [ ] Test stock note update (append new scan)
  - [ ] Test trade journal creation with wikilinks
  - [ ] Test index maintenance
  - [ ] Test graph data generation (nodes + edges correct)
  - [ ] Test historical context retrieval
- [ ] Create `tests/test_agents/test_wiki_renderer.py`
  - [ ] Test YAML frontmatter parsing
  - [ ] Test markdown body rendering
  - [ ] Test wikilink extraction
  - [ ] Test graph building from directory
- [ ] Run `make test` — All tests pass

---

## Phase 5C: 24-Hour Scheduler + Event Bus (Days 4-6)

**Goal:** Complete autonomous cycle. System operates 24/7 with reactive capabilities.

### 5C.1 Docker Timezone Fix
- [ ] Add `TZ=Asia/Kolkata` to `docker-compose.dev.yml` environment for `app` service
- [ ] Add `TZ=Asia/Kolkata` to `docker-compose.dev.yml` environment for `dashboard` service
- [ ] Verify: `datetime.now()` inside Docker returns IST times

### 5C.2 Agent Activity Manager
- [ ] Create `agent_activity.py`
  - [ ] `AgentActivityManager` singleton class
  - [ ] `start(agent_name, description)` — Register agent start
  - [ ] `complete(agent_name, result, status)` — Register completion
  - [ ] `get_all() → List[AgentStatus]` — Current agent statuses
  - [ ] `get_history(limit) → List[AgentRun]` — Recent run history
  - [ ] Persist to `context/agent_activity.json`
- [ ] Wire into existing agents: ScorerAgent, FilterAgent, ExecutionMonitor, TradeReviewer
- [ ] Verify: `context/agent_activity.json` updates on agent runs

### 5C.3 Event Bus with Recovery
- [ ] Create `event_bus.py`
  - [ ] `TradingEvent` — Base event model with type, timestamp, data, retry_count
  - [ ] `EventBus` class with `asyncio.Queue`
  - [ ] `emit(event)` — Push event to queue
  - [ ] `subscribe(event_type, handler)` — Register handler
  - [ ] `start_loop()` — Background consumer coroutine
- [ ] **Failed Event Recovery:**
  - [ ] On handler failure: persist event to `context/failed_events.json` with error message
  - [ ] On startup: load `context/failed_events.json`, show count in dashboard + send Telegram alert
  - [ ] Auto-retry logic: retry failed events up to 3 times with exponential backoff
  - [ ] If all retries fail: mark as `permanently_failed`, alert user via Telegram with details
  - [ ] Dashboard page shows failed events with manual "Retry" button
  - [ ] Telegram alert format: `"⚠️ {count} event(s) failed to process. View: {dashboard_link}/agent-activity"`
- [ ] Event handlers:
  - [ ] `handle_gtt_triggered` — Log trade, update state, send Telegram
  - [ ] `handle_vix_spike` — Tighten stops 20%, pause new entries
  - [ ] `handle_position_news` — Alert on Telegram
  - [ ] `handle_stop_hit` — Log observation, update knowledge graph
  - [ ] `handle_target_hit` — Log success, update knowledge graph
  - [ ] `handle_auth_expiring` — Alert user on Telegram
  - [ ] `handle_regime_change` — Adjust config via RegimeAdapter
- [ ] Wire event bus startup in `api/main.py` lifespan
- [ ] Wire failed event recovery check on startup
- [ ] Verify: emit event → handler executes
- [ ] Verify: handler failure → event persisted → Telegram alert sent → dashboard shows it

### 5C.4 Regime Adapter
- [ ] Create `regime_adapter.py`
  - [ ] `RegimeAdaptiveConfig` — Overlay that adjusts config based on regime
  - [ ] Bull: 100% size, 7.0 min score, normal stops
  - [ ] Neutral: 75% size, 7.5 min score, +10% tighter stops
  - [ ] Bear: 50% size, 8.0 min score, +20% tighter stops
  - [ ] Choppy: 0% size (paused), 9.0 min score, +30% tighter stops
- [ ] Wire into research pipeline (use adapted config for scoring threshold)
- [ ] Wire into execution agent (use adapted config for position sizing)
- [ ] Verify: changing regime changes effective config values

### 5C.5 Extend Scheduler (Keep `schedule` library)
> **Decision:** Keep the existing `schedule` library (proven to work with asyncio.create_task).
> Do NOT switch to APScheduler (thread issues with FastAPI event loop).

- [ ] Extend `scheduler.py` — Add all missing phase jobs using `schedule` library
- [ ] Phase 1 (Overnight 10PM-6AM):
  - [ ] `schedule.every(2).hours.do(self._overnight_check)` — GIFT Nifty, global markets
  - [ ] Overnight position check
- [ ] Phase 2 (Pre-Market 6AM-9:15AM):
  - [ ] Morning briefing generation → Telegram (already exists)
  - [ ] `schedule.every().day.at("06:30").do(self._fii_dii_check)` — FII/DII data
  - [ ] Review pending approvals status
- [ ] Phase 3 (Market Hours 9:15AM-3:30PM):
  - [ ] `schedule.every(15).minutes.do(self._market_hours_monitor)` — Position monitor
  - [ ] Add market hours guard: skip if outside 9:15-3:30 IST
  - [ ] Trailing stop adjustment
  - [ ] VIX monitoring (emit VIX_SPIKE event if VIX > 20)
  - [ ] Position news sweep (for held tickers)
- [ ] Phase 4 (Post-Market 3:30PM-6PM):
  - [ ] `schedule.every().day.at("15:35").do(self._post_market)` — EOD data collection
  - [ ] Final FII/DII numbers
  - [ ] P&L calculation
  - [ ] Position reconciliation
- [ ] Phase 5 (Evening 6PM-9PM):
  - [ ] Full research pipeline (already exists)
  - [ ] Knowledge graph update (Phase 5B)
- [ ] Phase 6 (Wind-Down 9PM-10PM):
  - [ ] `schedule.every().day.at("21:00").do(self._wind_down)` — State persistence
  - [ ] Daily summary → Telegram
  - [ ] Log rotation
  - [ ] Next-day prep
- [ ] Wire `ExecutionMonitor` for 15-min intraday polling
- [ ] Verify: scheduler logs show all 6 phases registered

### 5C.6 Monitor Agent Update
- [ ] `monitor.py` — Add GTT trigger detection (poll Kite orders)
- [ ] `monitor.py` — Emit events (STOP_HIT, TARGET_HIT) to event bus
- [ ] `monitor.py` — Register with AgentActivityManager
- [ ] `monitor.py` — Add market hours guard: skip monitoring outside 9:15-3:30 IST
- [ ] Verify: GTT fill detected → event emitted → handler runs

### 5C.7 Tests
- [ ] Create `tests/test_event_bus.py`
  - [ ] Test event emission and handler invocation
  - [ ] Test failed event persistence to JSON
  - [ ] Test auto-retry with exponential backoff
  - [ ] Test permanent failure after 3 retries
  - [ ] Test startup recovery of failed events
- [ ] Create `tests/test_scheduler.py`
  - [ ] Test all 6 phases registered
  - [ ] Test market hours guard (skip outside 9:15-3:30)
- [ ] Create `tests/test_regime_adapter.py`
- [ ] Run `make test` — All tests pass

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
  - [ ] Add `dashboard` service using `Dockerfile.dashboard`
  - [ ] Port mapping: `8502:3000` (Reflex frontend → host)
  - [ ] Environment: `FASTAPI_URL=http://app:8000`, `TZ=Asia/Kolkata`
  - [ ] `depends_on: [app]`
  - [ ] Volume mount for hot reload: `./swingtradev3/dashboard_v2:/app/dashboard_v2`
- [ ] Update `Makefile` — Add `make dashboard` command
- [ ] Verify: `docker-compose up` starts both containers, dashboard at `localhost:8502`

### 5D.2 Reflex Project Setup
- [ ] Initialize Reflex project: `swingtradev3/dashboard_v2/`
- [ ] Configure `rxconfig.py` — API port 3000, production settings
- [ ] Create `dashboard_v2/requirements.txt` — Reflex, plotly, httpx
- [ ] Verify: `reflex run` works inside Docker

### 5D.3 Theme & Design System
- [ ] Create `dashboard_v2/styles.py` — Dark theme, colors, typography
  - [ ] Color palette: dark backgrounds (#0d1117), accent green (#00d26a), accent red (#ff4444)
  - [ ] Typography: Inter/Outfit from Google Fonts
  - [ ] Component variants: cards, badges, gauges
- [ ] Create `dashboard_v2/state.py` — Global app state
  - [ ] API client wrapper (`httpx` calls to FastAPI at `FASTAPI_URL`)
  - [ ] API key header injection
  - [ ] Agent status state
  - [ ] Portfolio state
  - [ ] Knowledge graph state
  - [ ] Auto-refresh polling (every 30s)

### 5D.4 Reusable Components
- [ ] Create `components/sidebar.py` — Navigation + system health indicators
- [ ] Create `components/metric_card.py` — KPI display (P&L, win rate, etc.)
- [ ] Create `components/agent_badge.py` — Agent status (✅ idle / 🔄 running / ❌ error)
- [ ] Create `components/stock_card.py` — Research result card with score gauge
- [ ] Create `components/trade_card.py` — Trade detail expandable card
- [ ] Create `components/graph_view.py` — Knowledge graph force-directed layout

### 5D.5 Pages
- [ ] **🏠 Command Center** (`command_center.py`)
  - [ ] System health badges (API, Kite, LLM)
  - [ ] Market regime indicator with color
  - [ ] Agent status grid — all agents with status
  - [ ] Today's P&L summary
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
| **Phase 5A** | ⬜ 0% | 1 | Bug fixes (8 critical) |
| **Phase 5B** | ⬜ 0% | 3 | Knowledge Graph Engine (corrected pipeline order) |
| **Phase 5C** | ⬜ 0% | 3 | Scheduler (`schedule` lib) + Event Bus (with recovery) |
| **Phase 5D** | ⬜ 0% | 5 | Reflex Dashboard (separate Docker + Dockerfile.dashboard) |
| **Phase 5E** | ⬜ 0% | 1 | Telegram notifications only (no approvals) |
| **Phase 5F** | ⬜ 0% | 3 | Comprehensive tests (85+ target) |
