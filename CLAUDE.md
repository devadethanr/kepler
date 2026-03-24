# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**swingtradev3** is an autonomous swing trading system for Indian equities (Nifty 200) using:
- **Zerodha Kite** for execution and GTT (Good Till Triggered) orders
- **NVIDIA NIM** (DeepSeek/Qwen models) for AI-driven stock analysis
- **Human-in-the-loop** approval for all entries via Telegram

The system follows a **two-agent architecture**:
1. **research_agent.py** - Evening scanner (15:45), morning briefing (08:45), monthly analyst loop
2. **execution_agent.py** - 30-min polling during market hours (09:15-15:30), handles approvals, GTT lifecycle

## Architecture Principles

### Mode-Driven Design (No Mocks)
The same codebase runs in three modes controlled by `config.yaml`:
- `backtest` - Historical replay with paper fill engine
- `paper` - Live data, simulated fills
- `live` - Real money via Zerodha

**Critical:** No mock classes, no test doubles. The `trading.mode` flag determines data source and order destination. All modules read this flag at runtime.

### Intelligence in Markdown, Execution in Python
- `strategy/SKILL.md` - Trading philosophy (the "editable asset")
- `strategy/research_program.md` - Research procedure
- `strategy/analyst_program.md` - Monthly review procedure
- Python code only executes; strategy lives in markdown

### Config-Driven
All tunable values live in `config.yaml` (committed to git). Secrets only in `.env` (never committed). No magic numbers in Python.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run backtest (fast mode - no LLM calls)
python main.py --mode backtest

# Run backtest with full NIM fidelity (slow)
# Set backtest.use_llm: true in config.yaml first
python main.py --mode backtest

# Start paper trading
# Set trading.mode: paper in config.yaml
python main.py

# Start live trading
# Set trading.mode: live in config.yaml
python main.py

# Run tests
pytest tests/

# Run specific test file
pytest tests/test_risk.py
pytest tests/test_indicators.py
pytest tests/test_mode_switching.py

# Pause execution agent (faster than Telegram)
touch PAUSE
rm PAUSE  # Resume
```

## Key File Locations

### Configuration
- `config.yaml` - All tunable parameters (modes, thresholds, indicators, LLM settings)
- `config.py` - Pydantic Settings loader, exposes `cfg` singleton
- `.env` - Secrets only (API keys, tokens) - never commit this
- `.env.example` - Template for secrets

### Agents
- `agents/research_agent.py` - Nightly scan, NIM analysis, shortlisting
- `agents/execution_agent.py` - Approval handling, order execution, GTT management
- `agents/reconciler.py` - Startup state validation vs live Kite

### Strategy (The Intelligence Layer)
- `strategy/SKILL.md` - Trading philosophy (v1.0), read by NIM for every analysis
- `strategy/SKILL.md.staging` - Monthly proposed edits awaiting approval
- `strategy/research_program.md` - Step-by-step research procedure
- `strategy/analyst_program.md` - Monthly review procedure

### Tools (NIM Tool Registry)
- `tools/market_data.py` - `get_eod_data()` - OHLCV + indicators
- `tools/fundamental_data.py` - `get_fundamentals()` - 4-layer fetch (yfinance → nsepython → Firecrawl → cache)
- `tools/news_search.py` - `search_news()` - Tavily → DDGS fallback
- `tools/order_execution.py` - `place_order()` - Entry only, mode-aware
- `tools/gtt_manager.py` - `place_gtt/modify_gtt/cancel_gtt` - Mode-aware
- `tools/risk_check.py` - `check_risk()` - Hard gate before orders

### LLM Infrastructure
- `llm/nim_client.py` - OpenAI-compatible SDK for NIM
- `llm/router.py` - Fallback chain: NIM (5s) → Groq → Gemini → Claude
- `llm/tool_executor.py` - Tool-call loop, dispatches to TOOL_REGISTRY
- `llm/prompt_builder.py` - Assembles system prompt from SKILL.md + context
- `llm/schemas/*.json` - JSON schemas for each tool

### Data & Indicators
- `data/kite_fetcher.py` - Rate-limited Kite API (0.4s between calls)
- `data/nifty200_loader.py` - Universe constituent list
- `data/corporate_actions.py` - Dividends, splits, bonus tracking
- `data/indicators/` - 7 modules: momentum, trend, volatility, volume, structure, relative_strength, patterns

### Paper/Backtest Simulation
- `paper/fill_engine.py` - Simulates fills at next-open + slippage
- `paper/gtt_simulator.py` - In-memory GTT tracking for non-live modes
- `paper/slippage_model.py` - LTP × 0.001 per side + ₹20 brokerage

### Context (Runtime State)
- `context/state.json` - Live positions, cash, P&L, drawdown
- `context/trades.json` - All closed trades (includes skill_version hash)
- `context/pending_approvals.json` - Shortlisted setups awaiting YES/NO
- `context/stats.json` - Monthly metrics (Sharpe, win rate, Kelly)
- `context/research/YYYY-MM-DD/{ticker}.json` - Per-stock analysis outputs

## Critical Implementation Rules

### 1. Never Hardcode Model Names
```python
# WRONG:
model = "deepseek-ai/deepseek-v3-2"

# CORRECT:
model = cfg.llm.research_model.model  # From config.yaml
```

### 2. Always Respect trading.mode Flag
```python
# In order_execution.py, gtt_manager.py, kite_fetcher.py:
if cfg.trading.mode in ["paper", "backtest"]:
    return paper_fill_engine.fill(...)
else:
    return kite.place_order(...)
```

### 3. Sector Concentration Limit
Max 2 positions per sector (configurable via `research.max_same_sector_positions`). Enforced in `research_agent.py` after scoring, before shortlisting.

### 4. Entry Validity Window
Approvals auto-expire if price moves >3% above entry zone top (`execution.max_entry_deviation_pct`). Checked in `execution_agent.py` before placing orders.

### 5. Async Scan Pattern
Use `asyncio.Semaphore(3)` for Kite rate limit (3 req/sec). NIM calls are unbounded and can run in parallel.

```python
semaphore = asyncio.Semaphore(3)
async with semaphore:
    data = await get_eod_data(ticker)  # Kite call - rate limited
fundamentals = await get_fundamentals(ticker)  # May use yfinance/nsepython
return await nim_score(...)  # NIM call - parallel OK
```

### 6. Fundamentals 4-Layer Fallback
Never error on fundamentals fetch. Always return something with `is_stale` flag:
1. yfinance (primary) - PE, EPS, debt/equity, sector
2. nsepython/nsetools (best-effort) - Promoter holding, pledging
3. Firecrawl (fallback) - AI extraction from Screener.in
4. Cache (last resort) - Stale data with timestamp

### 7. GTT Corporate Action Handling
- **Dividends**: Auto-adjust stop price (current_stop - dividend_amount). Alert 5 days before, auto-apply after 12h if no reply.
- **Bonus/Split**: Pause entries, alert immediately. Manual re-entry required after Zerodha cancels GTT.
- **Rights**: Informational alert only.

### 8. SKILL.md Version Tagging
Every trade records `skill_version` (git commit hash of SKILL.md at analysis time). Enables performance attribution across strategy versions.

```python
import git
repo = git.Repo(".")
skill_hash = repo.head.commit.hexsha[:7]  # "a3f2c1d"
```

## Testing Conventions

- Write tests alongside modules, not after
- `test_mode_switching.py` - Verifies flag routing without mocks
- `test_paper.py` - Tests fill engine against known candle data
- `test_gtt_simulator.py` - Validates GTT trigger logic
- Use `pytest-asyncio` for async test support

## Risk Management Checks

All enforced in `risk/engine.py` and `tools/risk_check.py`:
- Max 1.5% risk per trade (`risk.max_risk_pct_per_trade`)
- Max 4% weekly loss (`risk.max_weekly_loss_pct`)
- Max 10% drawdown (`risk.max_drawdown_pct`)
- Min 2:1 risk:reward before entering (`risk.min_rr_ratio`)
- Confidence-based sizing: High (8.0+) = 40%, Medium (7.0-8.0) = 25%
- Circuit limit monitoring for held positions

## Monthly Analyst Loop

First Sunday of each month (if ≥8 closed trades):
1. `learning/stats_engine.py` - Recalculate Sharpe, win rate, Kelly
2. `learning/lesson_generator.py` - NIM reviews trades, proposes SKILL.md edits
3. `learning/skill_updater.py` - Telegram YES/NO approval, git commit on approval

## API Rate Limits

- **Kite**: 3 requests/sec (enforced via `asyncio.Semaphore(3)`)
- **NIM**: No explicit limit, but 5s timeout with fallback chain
- **Tavily**: 1,000 requests/month (free tier)

## Dependencies to Never Remove

- `kiteconnect` - Zerodha API
- `openai` - NIM/Groq SDK (OpenAI-compatible)
- `pandas-ta` + `TA-Lib` - Indicator calculations
- `vectorbt` + `quantstats` - Backtest metrics
- `gitpython` - SKILL.md version tagging
- `pyotp` - Kite TOTP automation

## Custom Agent Available

This project has a `quant-systems-architect` agent configured in `.claude/agents/quant-systems-architect.md`. Use it for:
- Trading system architecture decisions
- Risk management framework validation
- Position sizing logic review
- Backtest engine validation
- Multi-agent trading system design

## Important Notes

- **Never** auto-close positions without human approval (except GTT triggers)
- **Never** auto-replace GTTs that disappear (alert immediately, require acknowledgment)
- **Always** check `PAUSE` file before any order operation
- **Always** validate state.json vs live Kite on startup via reconciler.py
- **Never** commit `.env` or `.backtest_cache/` (already in `.gitignore`)
- **Always** run backtest with `use_llm: false` first (fast), then `use_llm: true` for final validation

## Documentation Reference

See `docs/reference/project_design.md` for complete 44-page system specification including:
- Full config.yaml reference
- Complete directory structure
- All tool I/O specifications
- Launch checklist
- v6 design additions (fundamentals layering, GTT corporate actions, etc.)
