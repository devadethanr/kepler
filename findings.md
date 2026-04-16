# Live Trading Findings

## Scope

This audit reviews the current `swingtradev3` implementation against four goals:

1. Unattended live execution
2. Autonomous intraday monitoring and trailing
3. Reliable live stop/target event handling
4. "Set it and forget it" trading with real money

Code was treated as the source of truth on 2026-04-16. External broker constraints were cross-checked against official Kite Connect docs.

## Short Verdict

The project is a strong personal research and orchestration system, but the live execution layer is not yet reliable enough for unattended real-money trading. The current implementation is closer to "research + partially wired execution" than a closed-loop autonomous trading system.

## Validation Run

Reviewed the live path in:

- `swingtradev3/api/routes/approvals.py`
- `swingtradev3/agents/execution/order_agent.py`
- `swingtradev3/tools/execution/order_execution.py`
- `swingtradev3/tools/execution/gtt_manager.py`
- `swingtradev3/agents/execution/monitor.py`
- `swingtradev3/api/tasks/scheduler.py`
- `swingtradev3/api/tasks/event_handlers.py`
- `swingtradev3/auth/kite/client.py`
- `swingtradev3/auth/token_manager.py`
- `swingtradev3/storage.py`

Dockerized checks run through `swingtradev3/Makefile`:

```bash
cd swingtradev3
make test-file file=tests/test_api/test_approvals.py
make test-file file=tests/test_scheduler_eventbus.py
make test-file file=tests/test_5c_completion.py
make test-file file=tests/test_agents/test_execution_monitor.py
make lint
```

Results:

- `tests/test_api/test_approvals.py`: passed
- `tests/test_scheduler_eventbus.py`: passed
- `tests/test_5c_completion.py`: passed
- `tests/test_agents/test_execution_monitor.py`: failed
- `make lint`: failed with 177 Ruff issues, including an `EventBus.retry_failed_event` redefinition

## Critical Findings

### 1. Approval-to-order execution is not reliable

Code refs:

- `swingtradev3/api/routes/approvals.py:21-68`
- `swingtradev3/agents/execution/order_agent.py:56-113`
- `swingtradev3/tools/execution/order_execution.py:80-153`

Findings:

- Approval is written to `pending_approvals.json` before execution starts.
- The background ADK run uses a fixed `session_id="order_session"`, which is unsafe for retries or concurrent approvals.
- `OrderExecutionAgent` calls `place_order_async(..., quantity=adjusted_qty)`, but `OrderExecutionTool.place_order_async()` does not accept a `quantity` parameter.
- The live path returns `status: "filled"` immediately after `place_order()`, assumes `average_price == requested price`, and never waits for broker confirmation.
- The MCP fallback invents a local `order_id` if direct placement fails and does not persist the real broker order id returned by the tool call.
- No successful execution path appends a new open position to `state.json`, updates `cash_inr`, or emits `ORDER_PLACED` / `ORDER_FILLED`.
- `ORDER_PLACED`, `ORDER_FILLED`, `POSITION_CLOSED`, `APPROVAL_REQUESTED`, and `APPROVAL_RECEIVED` exist as event types, but the live path does not publish them.

Impact:

- Approved trades can fail before reaching the broker.
- Live orders can exist at the broker while local state still shows no position.
- Duplicate clicks, retries, or restarts can create duplicate order attempts.

### 2. Intraday monitoring is mostly stubbed

Code refs:

- `swingtradev3/api/tasks/scheduler.py:337-354`
- `swingtradev3/api/tasks/scheduler.py:423-425`
- `swingtradev3/agents/execution/monitor.py:23-217`

Findings:

- `_position_monitor()` only logs a tick and never runs `execution_monitor`.
- `_gtt_health_check()` only logs a tick.
- `_position_reconciliation()` exists but is never scheduled.
- `StopTrailAgent` depends on `pos.current_price`, but there is no live quote refresh path writing current prices into `state.json`.
- There is no broker WebSocket or postback ingestion path in the application code.

Impact:

- Trailing stops do not run autonomously in production.
- Missing or cancelled GTTs are not actively repaired.
- Restart recovery cannot rebuild real intraday state from the broker.

### 3. Stop/target handling is broker-incorrect

Code refs:

- `swingtradev3/models.py:44-64`
- `swingtradev3/models.py:159-165`
- `swingtradev3/tools/execution/order_execution.py:145-153`
- `swingtradev3/tools/execution/gtt_manager.py:179-205`
- `swingtradev3/agents/execution/monitor.py:57-99`
- `swingtradev3/api/tasks/event_handlers.py:22-179`

Findings:

- The position model stores `stop_gtt_id` and `target_gtt_id` as if they are separate live orders.
- Live OCO GTT placement returns one trigger id, and the code stores that same id into both `stop_gtt_id` and `target_gtt_id`.
- `PositionChecker` checks both ids separately.
- `GTTManager.get_gtt_async()` maps a triggered live GTT to `triggered_target`, but `PositionChecker` only checks for the literal string `"triggered"`.
- GTT statuses like `rejected` are not mapped.
- Event handlers for `STOP_HIT`, `TARGET_HIT`, and `GTT_ALERT` log observations and send alerts, but they do not close the local position, append a `TradeRecord`, or reconcile with broker orders.

Impact:

- Stop or target triggers can be missed or misclassified.
- A real exit can happen at the broker while the local portfolio still shows the position as open.
- PnL, trade history, and learning loop inputs can all become incorrect.

### 4. The live portfolio has no broker-authoritative state

Code refs:

- `swingtradev3/auth/kite/client.py:81-93`
- `swingtradev3/api/tasks/scheduler.py:400-417`
- `swingtradev3/api/routes/trades.py:27-30`
- `swingtradev3/storage.py:14-25`

Findings:

- Broker portfolio APIs exist (`fetch_positions()`, `fetch_holdings()`) but are not used by the live runtime.
- There is no startup hydration of local positions from broker positions.
- Daily PnL is computed from local `current_price` fields, not broker positions or fresh market data.
- Manual close via API is explicitly not implemented.
- `write_json()` writes directly to the target file with no temp-file swap, no lock, and no transaction boundary.

Impact:

- Live state can drift after restarts, manual broker actions, or partial failures.
- Concurrent writes can corrupt runtime files.
- The system has no durable execution ledger for postmortem or recovery.

### 5. Authentication is not unattended

Code refs:

- `swingtradev3/auth/token_manager.py:13-23`
- `swingtradev3/auth/kite/session_store.py:12-38`
- `swingtradev3/auth/kite/client.py:46-73`

Findings:

- `TokenManager.refresh()` only reloads an already-issued token from env or the saved session file.
- There is no live token renewal workflow, expiry detection gate, or fail-closed behavior before market open.
- The stored session payload keeps raw session data, but the runtime never uses a refresh flow.

Impact:

- The system cannot sustain unattended live trading across trading days.
- A stale or expired session will break live execution at runtime instead of blocking it safely ahead of time.

### 6. Safety controls are configured but not enforced

Code refs:

- `swingtradev3/config.yaml:43-56`
- `swingtradev3/config.py:118-127`
- `swingtradev3/api/routes/trades.py:27-30`

Findings:

- `max_entry_deviation_pct`, `approval_timeout_hours`, `avoid_fno_expiry_days`, and corporate action handling settings are present in config but not enforced in the live path.
- Corporate-action models exist, but there is no actual live adjustment or pause flow.
- No order tagging is used for idempotent correlation.
- No market-protection or pre-trade margin calculation is used.
- No emergency flatten, kill switch, or repeated-failure circuit is implemented.

Impact:

- The code cannot safely handle slippage, stale approvals, broker-side modifications, or operational drift.

### 7. Test coverage misses the real live path

Code refs:

- `swingtradev3/tests/test_api/test_approvals.py:17-28`
- `swingtradev3/tests/test_agents/test_execution_monitor.py:15-68`
- `swingtradev3/tests/test_5c_completion.py:286-355`

Findings:

- Approval tests only cover the "not found" path.
- The execution monitor test currently fails because the agent now has a market-hours guard while the test still expects trailing behavior without forcing market hours.
- Event-handler tests mainly verify that handlers do not raise and can log observations.
- There is no end-to-end test for: approval -> broker order placed -> fill confirmed -> GTT armed -> exit triggered -> position closed -> trade recorded -> recovery after restart.
- The codebase is not using static type checks, which is one reason the `quantity` call-signature mismatch slipped through.

Impact:

- The parts that matter most for real money are the least protected by tests.

## Broker Constraints Confirmed From Official Kite Docs

These points matter because the code should be shaped around the broker's actual contract, not around local assumptions.

- GTT OCO uses a single trigger id, not separate stop and target ids. Official docs also describe multiple possible statuses, including `active`, `triggered`, `disabled`, `expired`, `rejected`, `cancelled`, and `deleted`.  
  Source: https://kite.trade/docs/connect/v3/gtt/

- Triggered GTT responses include the trigger condition and the resulting order objects. The implementation should use that broker result to determine which exit leg fired and whether the exit order was actually placed/completed.  
  Source: https://kite.trade/docs/connect/v3/gtt/

- Kite provides order updates through postbacks and WebSocket postbacks. A live system should not assume a placed order is instantly filled.  
  Source: https://kite.trade/docs/connect/v3/postbacks/

- Order placement supports an order `tag` and `market_protection`, and the API offers a margins calculation endpoint. Those are useful for correlation, safety checks, and pre-trade validation.  
  Source: https://kite.trade/docs/connect/v3/orders/

- Portfolio endpoints expose holdings and net/day positions and should be used for reconciliation after restart or suspected drift.  
  Source: https://kite.trade/docs/connect/v3/portfolio/

- Kite access tokens expire at 6 AM the next day. Long-running live automation must explicitly account for that.  
  Source: https://kite.trade/docs/connect/v3/user/

## What Must Exist Before Real-Money Autonomy Is Credible

### 1. An explicit execution state machine

Add a durable lifecycle like:

`approval_created -> approved -> entry_submit_started -> entry_open -> entry_filled -> gtt_armed -> position_open -> exit_triggered -> exit_filled -> position_closed`

Requirements:

- Every transition must be persisted before and after broker calls.
- Every approval needs a unique `approval_id` and `order_intent_id`.
- Broker `order_id`, `exchange_order_id`, `tag`, and `gtt_trigger_id` must be stored.
- Replays must be idempotent.

### 2. Broker truth ingestion

Build a dedicated live-execution worker that consumes broker truth:

- Order postbacks
- Broker WebSocket order updates
- Periodic portfolio and GTT reconciliation
- Fresh LTP or quote feed for trailing logic

Broker truth should override local assumptions.

### 3. A correct live position model

Replace split stop/target ids with a broker-faithful model:

- `entry_order_id`
- `entry_fill_price`
- `oco_gtt_id`
- `exit_order_id`
- `exit_reason`
- `broker_status`
- `last_reconciled_at`

Only mark a trade closed after confirmed broker exit fill.

### 4. Safe persistence

Move live execution state out of loose JSON files and into SQLite or Postgres.

Minimum requirements:

- Atomic writes
- Unique constraints on approval and broker ids
- Append-only order/trade ledger
- Recovery logic on process restart

### 5. Hard safety rails

Implement and enforce:

- Max entry deviation from approved entry zone
- Approval expiry
- Pre-trade margin check
- Order tagging
- Market protection
- Kill switch after repeated broker/API failures
- Panic close / flatten action
- Reconciliation drift alerts

### 6. Real integration tests

Before calling this unattended, add tests for:

- duplicate approval click
- broker order rejection
- partial fill
- fill-confirmed entry before GTT placement
- missing or disabled GTT
- stop trigger and target trigger
- restart after entry but before GTT arm
- restart after GTT trigger but before local close
- expired auth before market open
- manual broker-side modification of orders or positions

## Priority Order

If the goal is to reach unattended live trading with the least wasted effort, the work order should be:

1. Fix the approval-to-order path and persist entry state correctly.
2. Add broker order-update ingestion and reconciliation.
3. Replace the current GTT model with a single OCO trigger model.
4. Persist positions and trades in a transactional store.
5. Wire the scheduler to a real monitoring worker with live prices.
6. Add auth gating, kill switches, and manual emergency controls.
7. Only then improve trailing logic and "fully autonomous" behavior.

## Bottom Line

This codebase can become a serious autonomous trading system, but it is not there yet. The biggest gap is not research quality; it is the lack of a broker-driven, idempotent, restart-safe execution state machine. Until that exists, the project should be treated as supervised or paper/live-assisted, not as a true "set it and forget it" real-money agent.
