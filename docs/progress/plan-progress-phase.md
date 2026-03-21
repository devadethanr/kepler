# Plan Progress By Phase

This file tracks the implementation phases for `swingtradev3` based on `swingtradev3_design_v6.pdf`.

## Phase List

1. Phase 1: live broker integration
2. Phase 2: LLM-driven research pipeline
3. Phase 3: execution operations, approvals, reconciliation, and safety loops
4. Phase 4: backtest engine and metrics
5. Phase 5: Telegram integration and learning loop
6. Phase 6: end-to-end Docker validation

## Phase 1: Live Broker Integration

### Completed

- Official Kite login flow implemented with code-based `request_token -> session` exchange.
- Persisted Kite session storage implemented at `swingtradev3/context/auth/kite_session.json`.
- Direct Kite client layer added in `swingtradev3/auth/kite/client.py`.
- Token manager updated to load persisted Kite session into runtime.
- Live adapters now prefer direct Kite session, with MCP fallback where useful:
  - `swingtradev3/data/kite_fetcher.py`
  - `swingtradev3/tools/order_execution.py`
  - `swingtradev3/tools/gtt_manager.py`
  - `swingtradev3/agents/reconciler.py`
- Live GTT path corrected to use `stop_gtt_id` for stop updates instead of incorrectly keying off `entry_order_id`.
- GTT quantity propagation fixed so order sizing is preserved in both paper and live paths.
- Self-hosted Kite MCP setup and auth workflow documented in `docs/runbooks/kite-mcp-setup.md`.
- Targeted live integration tests added:
  - `swingtradev3/tests/test_kite_auth.py`
  - `swingtradev3/tests/test_live_integration.py`
  - `swingtradev3/tests/test_reconciler.py`
- Docker verification completed:
  - targeted auth + live integration tests passed inside container
  - direct read-only Kite smoke check succeeded for `profile`, `positions`, and `holdings`

### Validated Without Paid Plan

- Docker stack health verified:
  - `app` healthy
  - `kite-mcp` healthy
- In-container Phase 1 validation suite passed:
  - `test_kite_auth.py`
  - `test_live_integration.py`
  - `test_reconciler.py`
  - `test_mode_switching.py`
  - `test_paper.py`
  - result: `8 passed`
- Persisted Kite session load verified inside container:
  - session file present
  - `user_id=RDK847`
  - `user_name=Devadethan R`
- Direct Kite read-only account endpoints verified:
  - `profile()`
  - `positions()`
  - `holdings()`
- Direct Kite GTT listing verified:
  - `get_gtts()` succeeded
  - current result returned zero GTTs, which is valid for the current account state
- MCP fallback connectivity verified:
  - `search_instruments("INFY")` succeeded from the app container
  - MCP response content was present and readable

### Validated But Limited By Current Free Plan

- Direct auth and account APIs are working.
- Direct data APIs are not fully usable under the current plan:
  - `ltp`
  - `historical_data`
- This matches the current free/personal Kite plan behavior.
- The code paths remain implemented and are ready for validation once the paid app is provided.

### Still To Complete

- Validate direct live order placement against real broker responses in a paid-key environment.
- Validate direct GTT placement, modification, and deletion against real broker responses in a paid-key environment.
- Validate direct quote and historical market-data paths with the paid Kite Connect app.
- Tighten MCP response normalization for market-data fallback payloads.
- Add more live adapter tests around fallback behavior and real-response parsing.

### Current Constraint

- The current free/personal Kite developer profile allows:
  - auth
  - profile
  - positions
  - holdings
- It does not allow direct quote and historical data endpoints.
- Because of that:
  - direct data-path validation is incomplete
  - code support remains in place
  - MCP/fallback behavior is preserved until the paid app is provided

## Phase 2: LLM-Driven Research Pipeline

### To Complete

- Complete tool layer for research:
  - market data
  - fundamentals
  - news
  - FII/DII
  - options
- Complete structured LLM research output contract.
- Complete async stock scan flow.
- Complete shortlist generation flow.
- Enforce sector caps, earnings checks, corporate-action guards, and score thresholds.
- Tighten tool execution loop and provider fallback behavior.

## Phase 3: Execution Operations, Approvals, Reconciliation, And Safety Loops

### To Complete

- Complete approval lifecycle.
- Complete reconciliation loops.
- Complete missing-GTT recovery handling.
- Complete dividend adjustment flow.
- Complete `PAUSE` handling and other operational safety behavior.
- Complete circuit-breaker and expiry handling.

## Phase 4: Backtest Engine And Metrics

### To Complete

- Complete historical replay engine.
- Reuse shared research/risk/execution logic in backtest mode.
- Complete metrics and reporting output.
- Complete validation thresholds and walk-forward path.

## Phase 5: Telegram Integration And Learning Loop

### To Complete

- Complete inbound Telegram approval flow.
- Complete outbound alerts and daily briefing flow.
- Complete trade review flow.
- Complete stats engine flow.
- Complete lesson generation flow.
- Complete controlled SKILL update workflow.

## Phase 6: End-To-End Docker Validation

### To Complete

- Expand Docker-based test coverage.
- Add end-to-end paper-mode validation.
- Add live-mode dry-path validation.
- Add fallback and reconciliation end-to-end checks.
- Run full integration verification after paid Kite app is available.
