# swingtradev3 Current Backlog

> Last Updated: April 16, 2026
> This file tracks the backlog against the code that exists today, not against older design drafts.

## Shipped Foundation

The following are present in code and should not be treated as open work:

- FastAPI API with authenticated routes, SSE, dashboard routes, and background startup lifecycle
- Google ADK research pipeline and ADK-backed execution/learning agents
- 24-hour scheduler with IST-aware phases
- event bus, failed-event persistence, and agent activity tracking
- markdown knowledge graph with dashboard endpoints
- Reflex dashboard shell running as a separate Docker service

## Highest Priority

### 1. Dashboard Completion

- Replace placeholder Approvals UI with live pending approvals, approval/reject actions, and execution feedback
- Add Trade Journal page backed by `context/trades.json` and trade-review outputs
- Add Learning page backed by the learning agents and monthly review artifacts
- Fill out missing reusable UI pieces where needed instead of relying on static placeholder panels

### 2. Validation And Test Drift

- Fix `tests/test_agents/test_execution_monitor.py` so it reflects the market-hours guard in `agents/execution/monitor.py`
- Re-run the full Dockerized suite through `make test` after the failing test is corrected
- Add targeted Dockerized tests for the current approvals -> order agent -> state update path

## Medium Priority

### Execution / Operations

- Complete the failed-event manual retry path in the API and dashboard
- Audit any remaining Streamlit-era naming in config comments, docs, and developer notes
- Confirm the live execution flow during market hours with the current direct-Kite session handling

### Documentation

- Add `docs/api.md` for the current REST and SSE surface
- Keep current docs aligned with the implemented Reflex stack and the Makefile-based Docker workflow

## Lower Priority

- Document optional remote-access workflow for the dashboard
- Add resource limits and other final Docker hardening after functionality is stable
- Expand end-to-end evaluation beyond targeted subsystem tests

## Known Reality Checks

- Command Center already exists and is no longer an open item
- Knowledge graph modules already exist and have dedicated tests
- The active UI stack is Reflex, not Streamlit
- Telegram should be documented as notifications-first; the dashboard/API are the primary control paths
