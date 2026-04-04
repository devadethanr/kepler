# swingtradev3 v2 — Implementation TODOs

> Based on `docs/architecture/v2_adk_fastapi_design.md`
> Last Updated: April 4, 2026

---

## Phase 0: Environment & Foundation (Days 1-3)

**Goal:** Get the dev environment running with hot reload, collect all API keys, set up config properly, create directory structure.

### 0.1 API Key Collection
- [x] **Zerodha Kite** — Already have (`m0q3d9nvg75ug0zg`)
- [x] **NVIDIA NIM** — Already have (`nvapi-dZsJ...`)
- [x] **Tavily** — Already have (`tvly-dev-...`)
- [ ] **Firecrawl** — Get API key from firecrawl.dev (free tier: 500 credits/mo)
- [ ] **Groq** — Get API key from console.groq.com (free tier)
- [ ] **Gemini** — Get API key from aistudio.google.com (free tier: 15 RPM)
- [x] **Telegram Bot Token** — Already have via BotFather
- [x] **Telegram Chat ID** — Already have (your user ID)
- [ ] **API Key for FastAPI** — Generate a random string for API auth
- [ ] **Action:** Edit `swingtradev3/.env` with all keys

### 0.2 Config.yaml Audit
- [x] Copied old config.yaml with all existing magic numbers
- [x] Added new config sections:
  - [x] `scheduler` — 24-hour cycle timings, frequencies
  - [x] `research.filter` — filter thresholds, batch sizes
  - [x] `api` — FastAPI host, port, CORS, auth key
  - [x] `dashboard` — Streamlit port, refresh interval
  - [x] `llm.adk` — ADK model routing
  - [x] `data` — Kite rate limits, cache TTLs
- [ ] Config.py Pydantic model update for v2 fields
- [ ] Add validation for critical thresholds

### 0.3 Docker Setup with Hot Reload
- [x] Created `Dockerfile.dev` — Dev mode with `uvicorn --reload` + Streamlit in same container
- [x] Created `Dockerfile` — Production mode (both services)
- [x] Created `docker-compose.dev.yml` — 2 services: app (8000 + 8501) + kite-mcp (3000)
- [x] Kite MCP Dockerfile exists at project root (`Dockerfile.kite-mcp`) — builds from zerodha/kite-mcp-server repo
- [x] Created `.dockerignore` to exclude `context/`, `logs/`, `__pycache__`, `.git`, `old/`
- [ ] Test: `docker compose -f docker-compose.dev.yml up` — both services start
- [ ] Test hot reload: Change a FastAPI route → auto-reloads within 2s
- [ ] Test hot reload: Change a Streamlit page → auto-reloads within 2s
- [ ] Test: FastAPI `/health` endpoint returns 200
- [ ] Test: Streamlit dashboard loads at `localhost:8501`
- [ ] Test: Kite MCP sidecar responds to health check

### 0.4 Project Structure Setup
- [x] Created `api/` directory structure (empty `__init__.py` files)
- [x] Created `dashboard/` directory structure
- [x] Created `agents/research/`, `agents/execution/`, `agents/learning/`, `agents/macro/`
- [x] Created `tools/analysis/`, `tools/macro/`
- [x] Created `api/routes/`, `api/schemas/`, `api/middleware/`, `api/tasks/`
- [x] Created `dashboard/pages/`, `dashboard/components/`
- [x] Created `tests/test_agents/`, `tests/test_api/`, `tests/test_evaluation/`
- [ ] Create `models.py` for shared Pydantic models (layer contracts)

### 0.5 Dev Tooling
- [x] Created `Makefile` with commands: dev, test, lint, logs, stop, clean, shell, health
- [x] Created `.env` with all API key placeholders (skip Claude)
- [x] Created `.env.example` template
- [x] Created `requirements.txt` with all new packages
- [ ] Create `pyproject.toml` with dev dependencies

---

## Phase 1: Foundation — FastAPI + ADK Scaffolding (Days 4-10)

**Goal:** FastAPI server running with basic routes, ADK root agent wired, Streamlit skeleton, existing agents triggered via API.

### 1.1 FastAPI Core
- [ ] Implement `api/main.py` — FastAPI app with CORS, startup/shutdown events
- [ ] Implement `api/routes/health.py` — `GET /health` returns service status
- [ ] Implement `api/routes/positions.py` — `GET /positions`, `GET /positions/{id}`
- [ ] Implement `api/routes/trades.py` — `GET /trades`, `GET /trades/{id}`, `POST /trades/{id}/close`
- [ ] Implement `api/routes/approvals.py` — `GET /approvals`, `POST /approvals/{id}/yes`, `POST /approvals/{id}/no`
- [ ] Implement `api/routes/scan.py` — `POST /scan`, `GET /scan/status`
- [ ] Implement `api/routes/regime.py` — `GET /regime`
- [ ] Implement `api/routes/stats.py` — `GET /stats`
- [ ] Implement `api/routes/ws.py` — `WebSocket /ws/alerts`
- [ ] Implement `api/schemas/` — Pydantic models for all request/response types
- [ ] Implement `api/middleware/auth.py` — API key authentication
- [ ] Implement `api/middleware/rate_limit.py` — Rate limiting

### 1.2 ADK Integration
- [ ] Install `google-adk` + `litellm`
- [ ] Implement `agents/root.py` — Root coordinator LlmAgent
- [ ] Implement `agents/models.py` — LiteLLM model config for NIM routing
- [ ] Wire ADK session state to file-based JSON persistence
- [ ] Create ADK callback hooks for state persistence
- [ ] Test: Root agent responds to basic queries via FastAPI

### 1.3 Background Task Scheduler
- [ ] Implement `api/tasks/scheduler.py` — 24-hour cycle orchestration
- [ ] Implement `api/tasks/research_task.py` — Evening scan trigger
- [ ] Wire existing `old/research_agent.py` to FastAPI `/scan` endpoint
- [ ] Wire existing `old/execution_agent.py` to scheduler (unchanged for now)

### 1.4 Streamlit Dashboard Skeleton
- [ ] Implement `dashboard/app.py` — Main Streamlit app
- [ ] Implement `dashboard/pages/1_overview.py` — Portfolio overview placeholder
- [ ] Implement `dashboard/pages/2_research.py` — Research results placeholder
- [ ] Implement `dashboard/pages/3_approvals.py` — Approvals placeholder
- [ ] Implement `dashboard/pages/4_positions.py` — Positions placeholder
- [ ] Implement `dashboard/pages/5_trades.py` — Trades placeholder
- [ ] Implement `dashboard/pages/6_learning.py` — Learning placeholder
- [ ] Implement `dashboard/pages/7_agent_trace.py` — Agent trace placeholder
- [ ] Implement `dashboard/components/charts.py` — Plotly chart utilities
- [ ] Implement `dashboard/components/tables.py` — Data table utilities
- [ ] Implement `dashboard/components/widgets.py` — Reusable UI widgets
- [ ] Wire dashboard to FastAPI API endpoints
- [ ] Test: Dashboard loads and fetches data from FastAPI

### 1.5 Testing
- [ ] Implement `tests/test_api/test_positions.py`
- [ ] Implement `tests/test_api/test_trades.py`
- [ ] Implement `tests/test_api/test_approvals.py`
- [ ] Implement `tests/test_api/test_scan.py`
- [ ] Run all existing tests from `old/tests/` — must still pass (61 passed)

**Deliverable:** Running FastAPI server + Streamlit dashboard + ADK root agent + existing agents triggered via API.

---

## Phase 2: Research Pipeline Migration (Days 11-24)

**Goal:** Replace `research_agent.py` with ADK SequentialAgent pipeline with multi-signal funnel.

### 2.1 Data Layer Enhancements
- [ ] Implement `data/market_regime.py` — Market regime detection
- [ ] Implement `data/institutional_flows.py` — FII/DII/block deals tracking
- [ ] Implement `data/news_aggregator.py` — Multi-source news (Tavily + RSS + Reddit)
- [ ] Implement `data/earnings_analyzer.py` — Earnings quality analysis
- [ ] Implement `data/events_calendar.py` — RBI, budget, rebalancing dates
- [ ] Implement `data/options_analyzer.py` — Options chain intelligence
- [ ] Implement `data/macro_indicators.py` — Macro data layer
- [ ] Implement `data/timesfm_forecaster.py` — Google TimesFM 2.5 price/volume forecasting (200M params, local, free)
- [ ] Enhance `data/indicators/volume.py` — Add VWAP, CMF, volume profile
- [ ] Enhance `data/indicators/relative_strength.py` — Add multi-benchmark RS, RS rank

### 2.2 Signal Engine Tools
- [ ] Implement `tools/analysis/sentiment_analysis.py` — FinBERT + LLM sentiment
- [ ] Implement `tools/analysis/regime_detection.py` — Market regime classification
- [ ] Implement `tools/analysis/correlation_check.py` — Portfolio correlation check
- [ ] Implement `tools/analysis/entry_timing.py` — Smart entry timing
- [ ] Implement `tools/analysis/timesfm_forecast.py` — @tool def forecast_timeseries(ticker, horizon) → point + quantile forecasts
- [ ] Enhance `tools/market/market_data.py` — Multi-timeframe support
- [ ] Enhance `tools/market/fundamental_data.py` — Earnings quality analysis

### 2.3 ADK Research Agents
- [ ] Implement `agents/research/filter_agent.py` — Multi-signal candidate selection funnel (Layer 0-2)
- [ ] Implement `agents/research/regime_agent.py` — Market regime detection agent
- [ ] Implement `agents/research/market_data_agent.py` — OHLCV + indicators agent
- [ ] Implement `agents/research/fundamentals_agent.py` — Fundamental analysis agent
- [ ] Implement `agents/research/sentiment_agent.py` — News + social sentiment agent
- [ ] Implement `agents/research/options_agent.py` — Options chain analysis agent
- [ ] Implement `agents/research/timesfm_agent.py` — TimesFM forecast integration agent
- [ ] Implement `agents/research/scorer_agent.py` — Final scoring + shortlisting agent
- [ ] Implement `agents/research/scanner.py` — BatchScannerAgent (dynamic parallel)
- [ ] Wire `agents/research/pipeline.py` — SequentialAgent: regime → filter → scan → score

### 2.4 Risk Enhancement
- [ ] Implement `risk/correlation_checker.py` — Portfolio correlation + VaR
- [ ] Enhance `risk/engine.py` — Regime-adjusted sizing

### 2.5 Testing
- [ ] Implement `tests/test_agents/test_research_pipeline.py`
- [ ] Test multi-signal funnel: 200 stocks → ~15-25 qualified
- [ ] Test parallel scanner: batches of 10, concurrent analysis
- [ ] Test scorer agent: chain-of-thought, bull/bear cases, scoring
- [ ] Verify research pipeline produces same/better scores vs old baseline

**Deliverable:** ADK-based research pipeline with regime detection, multi-signal funnel, sentiment analysis, and parallel scanning.

---

## Phase 3: Execution + Learning Migration (Days 25-38)

**Goal:** Replace `execution_agent.py` + learning modules with ADK agents.

### 3.1 ADK Execution Agents
- [ ] Implement `agents/execution/monitor.py` — LoopAgent: 30-min position polling
- [ ] Implement `agents/execution/order_agent.py` — LlmAgent: entry decisions + human-in-loop
- [ ] Implement `agents/execution/gtt_agent.py` — LlmAgent: GTT lifecycle management
- [ ] Implement `agents/execution/exit_agent.py` — LlmAgent: exit intelligence
- [ ] Wire ADK human-in-the-loop to FastAPI `/approvals` endpoints

### 3.2 ADK Learning Agents
- [ ] Implement `agents/learning/reviewer.py` — LlmAgent: trade review on close
- [ ] Implement `agents/learning/stats_agent.py` — LlmAgent: monthly stats calculation
- [ ] Implement `agents/learning/lesson_agent.py` — LlmAgent: SKILL.md improvement proposals

### 3.3 24-Hour Scheduler Integration
- [ ] Implement `api/tasks/overnight_monitor.py` — Phase 1: Global markets, news, macro
- [ ] Implement `api/tasks/morning_briefing.py` — Phase 2: Pre-market prep
- [ ] Implement `api/tasks/market_hours.py` — Phase 3: Market hours execution
- [ ] Implement `api/tasks/post_market.py` — Phase 4: Post-market analysis
- [ ] Implement `api/tasks/wind_down.py` — Phase 6: Night wind-down

### 3.4 Dashboard Enhancement
- [ ] Implement `dashboard/pages/1_overview.py` — Full P&L equity curve, portfolio snapshot
- [ ] Implement `dashboard/pages/2_research.py` — Scan results with scores, signals, shortlist
- [ ] Implement `dashboard/pages/3_approvals.py` — YES/NO buttons with setup details
- [ ] Implement `dashboard/pages/4_positions.py` — Live positions with GTT status, trailing
- [ ] Implement `dashboard/pages/5_trades.py` — Trade history with per-trade P&L
- [ ] Implement `dashboard/pages/6_learning.py` — SKILL.md evolution, monthly stats
- [ ] Implement `dashboard/pages/7_agent_trace.py` — ADK trace view for debugging
- [ ] Add auto-refresh (30s) for live data
- [ ] Add WebSocket integration for real-time alerts

### 3.5 Testing
- [ ] Implement `tests/test_agents/test_execution_monitor.py`
- [ ] Implement `tests/test_agents/test_learning_loop.py`
- [ ] Test human-in-the-loop: YES → order placed, NO → rejected
- [ ] Test LoopAgent: position monitoring, GTT health checks
- [ ] Test 24-hour scheduler: all 6 phases trigger correctly

**Deliverable:** Complete ADK-based system with execution monitoring, human-in-the-loop approvals, learning loop, and full dashboard.

---

## Phase 4: Evaluation + Polish (Days 39-52)

**Goal:** ADK evaluation framework, production readiness, Docker finalization.

### 4.1 ADK Evaluation
- [ ] Implement `tests/test_evaluation/test_agent_decisions.py` — Agent reasoning quality tests
- [ ] Implement `tests/test_evaluation/test_backtest_eval.py` — Backtest + ADK eval integration
- [ ] Set up `tool_trajectory_avg_score` criteria for research pipeline
- [ ] Set up `rubric_based_tool_use_quality_v1` for risk checks
- [ ] Set up `hallucinations_v1` for agent response grounding
- [ ] Create eval dataset from historical research runs

### 4.2 Security & Production
- [ ] Implement `api/middleware/auth.py` — Full API key authentication
- [ ] Implement `api/middleware/rate_limit.py` — Rate limiting per endpoint
- [ ] Add request logging with correlation IDs
- [ ] Add error handling with structured error responses
- [ ] Add health check endpoints for Docker healthchecks

### 4.3 Docker Finalization
- [ ] Update `Dockerfile` for production (no `--reload`, optimized layers)
- [ ] Update `docker-compose.yml` for production (2 services: app + kite-mcp)
- [ ] Add Docker healthchecks for all services
- [ ] Add restart policies (`unless-stopped`)
- [ ] Add resource limits (CPU, memory)
- [ ] Test: Full E2E paper mode in Docker
- [ ] Test: Full E2E live mode (dry run) in Docker

### 4.4 Documentation
- [ ] Update `docs/README.md` with new architecture
- [ ] Create `docs/quickstart.md` — Setup guide for new users
- [ ] Create `docs/api.md` — API reference (auto-generated from OpenAPI)
- [ ] Create `docs/deployment.md` — Docker deployment guide
- [ ] Create `docs/troubleshooting.md` — Common issues and fixes

### 4.5 Final Testing
- [ ] Run all tests — must pass 100%
- [ ] Run backtest — same trades, same P&L as baseline
- [ ] Run research pipeline — scores match or exceed baseline
- [ ] Test API response times — P95 < 500ms
- [ ] Test dashboard load time — P95 < 2s
- [ ] Test hot reload in dev mode — changes reflect within 2s

**Deliverable:** Production-ready system with evaluation framework, security, documentation, and full dashboard.

---

## Summary Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| **Phase 0** | Days 1-3 | Dev environment, Docker hot reload, API keys, config audit |
| **Phase 1** | Days 4-10 | FastAPI + ADK scaffolding + Streamlit skeleton |
| **Phase 2** | Days 11-24 | Research pipeline with multi-signal funnel |
| **Phase 3** | Days 25-38 | Execution + Learning + 24-hour scheduler + full dashboard |
| **Phase 4** | Days 39-52 | Evaluation + production readiness + Docker finalization |

**Total: ~8 weeks (52 days)**

---

## Current Progress

> **Phase 0: Environment & Foundation — ✅ 100% COMPLETE**

### What's Done
- [x] Moved current code to `old/` directory (fallback preserved)
- [x] Created new directory structure with all `__init__.py` files
- [x] Created `.env` with all API keys filled (NIM, Tavily, Firecrawl, Groq, Gemini, FastAPI)
- [x] Created `.env.example` template
- [x] Updated `config.yaml` with new v2 sections (api, dashboard, scheduler, data, research.filter, llm.adk)
- [x] Created `config.py` — all v1 + v2 Pydantic models in one file, properly structured and commented
- [x] Created `Dockerfile.dev` — single container: FastAPI (8000) + Streamlit (8501), hot reload
- [x] Created `Dockerfile.app` — production mode, both services
- [x] Created `docker-compose.dev.yml` — 2 services: app + kite-mcp (at project root)
- [x] Created `requirements.txt` with all new packages
- [x] Created `pyproject.toml` for editable install
- [x] Created `Makefile` — dev, test, lint, logs, stop, clean, shell, health, **login**
- [x] Created `.dockerignore`
- [x] Created `models.py` — shared Pydantic models (layer contracts + v2 models)
- [x] Created `paths.py` — path constants
- [x] Created `api/main.py` — FastAPI app with health + ws routes
- [x] Created `api/routes/health.py` — GET /health endpoint
- [x] Created `api/routes/ws.py` — WebSocket /ws/alerts with broadcast utility
- [x] Created `api/schemas/health.py` — Health response schema
- [x] Created `dashboard/app.py` — Streamlit dashboard skeleton with 4 metrics cards
- [x] Created `auth/kite/login.py` — Kite login helper (browser → request_token → access_token → session save)
- [x] Kite login working via `make login` — session saved to `context/auth/kite_session.json`
- [x] Authenticated user: Devadethan R (RDK847), ZERODHA

### Verified Working
- [x] FastAPI `/health` returns 200: `{"status":"ok","mode":"paper","services":{"app":"running","kite-mcp":"unknown"}}`
- [x] Streamlit dashboard loads at `localhost:8502` (HTTP 200)
- [x] Docker build succeeds, hot reload active
- [x] `make login` — interactive Kite auth with datetime serialization fix
- [x] Ports: FastAPI → 8001, Streamlit → 8502, Kite-MCP → 8081 (8000/8501/3000 occupied locally)

### Phase 1: Foundation
- [ ] Not started

### Phase 2: Research Pipeline
- [ ] Not started

### Phase 3: Execution + Learning
- [ ] Not started

### Phase 4: Evaluation + Polish
- [ ] Not started

---

## Notes

- **Claude API skipped** — Not needed, fallback chain is NIM → Groq → Gemini
- **Old code preserved** — All existing code in `swingtradev3/old/` as fallback
- **Config-driven** — All magic numbers in `config.yaml`, not in Python
- **Hot reload** — Dev mode uses `uvicorn --reload` + volume mounts
- **File-based persistence** — No database, JSON files in `context/`
- **Single container** — FastAPI + Streamlit run in same Docker container (ports 8000 + 8501)
- **Kite auth** — Direct session via `make login`, MCP sidecar available as fallback
- **TimesFM** — Commented out in requirements (v2.5 not on PyPI yet, only 1.0.0 available)
