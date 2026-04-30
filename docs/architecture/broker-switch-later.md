# Broker Switch Later: Kite To Upstox Assessment

> Last Updated: May 1, 2026
> Status: planning note only. No broker switch has been implemented.

This document captures the current findings on whether `swingtradev3` can move away
from Zerodha Kite, with Upstox as the primary replacement candidate.

The immediate cause for this research was the current Zerodha Kite app showing as
cancelled/expired on April 28, 2026. Renewing Zerodha data access costs about
INR 500/month. The question is whether the project can avoid that by switching
brokers without losing required live-trading capabilities.

## Short Answer

Upstox appears capable of covering the current Kite surface:

- OAuth login and daily token lifecycle
- order placement, order book, trades, order history
- holdings, positions, funds, margins
- LTP, OHLC, full market quotes
- historical and intraday candles
- GTT/conditional orders
- market-data WebSocket
- portfolio/order update stream and webhooks
- instrument master/search

However, this is not a simple `.env` swap. The codebase is still structurally
Kite-shaped. The switch is medium-high impact because auth, instruments, streaming,
GTT payloads, postbacks, and tests all assume Kite semantics.

Recommended decision:

1. If live trading must work immediately, renew Zerodha and keep the current Kite
   path stable.
2. If avoiding Zerodha long term is the goal, build a provider-neutral broker
   adapter layer first, keep Kite working, then add Upstox behind the same
   contract.
3. Do not remove Kite until Upstox has completed a full paper/sandbox/live-small
   lifecycle: login, reconciliation, entry, fill, GTT armed, GTT modified, exit,
   and clean reconciliation.

## Current Zerodha/Kite Usage

The app currently uses direct `kiteconnect` APIs as the primary live path. The
`kite-mcp` sidecar exists as fallback/diagnostic tooling, mainly for historical
data, LTP, and GTT operations when no direct Kite session exists.

### Auth And Session

Code paths:

- `swingtradev3/auth/kite/login.py`
- `swingtradev3/auth/kite/session_store.py`
- `swingtradev3/auth/kite/client.py`
- `swingtradev3/auth/token_manager.py`
- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/execution/auth_preflight.py`
- `swingtradev3/ops/phase0_check.py`
- `swingtradev3/ops/phase3_check.py`

Current flow:

1. Build Kite login URL with `KITE_API_KEY`.
2. User logs in through browser.
3. Browser redirects with `request_token`.
4. App exchanges `request_token + KITE_API_SECRET` for `access_token`.
5. App verifies `profile()`.
6. Session is saved to `context/auth/kite_session.json`.
7. Local code treats the session as expired around next-day 06:00 IST.

Current assumptions:

- `KITE_API_KEY`, `KITE_API_SECRET`, `KITE_ACCESS_TOKEN`
- one saved session called `kite`
- Kite-style daily token expiry
- live execution blocks with `KITE_SESSION_REQUIRED` if no valid session exists

### REST Trading APIs

Code paths:

- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/tools/execution/order_execution.py`
- `swingtradev3/broker/reducer.py`
- `swingtradev3/execution/reconciler.py`

Current direct Kite calls:

- `profile()`
- `positions()`
- `holdings()`
- `margins()`
- `orders()`
- `order_history(order_id)`
- `trades()`
- `order_trades(order_id)`
- `order_margins(orders)`
- `place_order(...)`

Current execution behavior:

- live entries use `LIMIT`, `CNC`, `regular`
- live exits/flattening use `SELL MARKET`
- order tags are generated locally and capped for Kite tag limits
- broker order updates are reduced into Postgres execution state

### Market Data And Historical Data

Code paths:

- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/data/kite_fetcher.py`
- `swingtradev3/execution/quote_cache.py`
- `swingtradev3/execution/trailing_engine.py`
- `swingtradev3/tools/market/market_data.py`
- `swingtradev3/backtest/data_fetcher.py`
- `swingtradev3/risk/correlation_checker.py`

Current Kite calls:

- `ltp("NSE:TICKER")`
- `instruments(exchange)`
- `historical_data(instrument_token, from_date, to_date, interval)`

Current assumptions:

- exchange + tradingsymbol identifies a symbol for REST quote calls
- integer `instrument_token` is needed for historical and WebSocket paths
- cached parquet files can avoid live broker data calls

### WebSocket

Code paths:

- `swingtradev3/broker/kite_stream.py`
- `swingtradev3/auth/kite/websocket.py`
- `swingtradev3/execution/bootstrap.py`
- `swingtradev3/execution/runtime_context.py`
- `swingtradev3/execution/reconciler.py`

Current Kite behavior:

- `KiteTicker` is created from API key/access token
- callbacks are assigned directly:
  - `on_ticks`
  - `on_order_update`
  - `on_connect`
  - `on_close`
  - `on_error`
  - `on_reconnect`
  - `on_noreconnect`
- stream uses `MODE_FULL`
- ticks contain `instrument_token`
- app maps `instrument_token -> ticker`

### GTT / Protective Orders

Code paths:

- `swingtradev3/broker/kite_rest.py`
- `swingtradev3/tools/execution/gtt_manager.py`
- `swingtradev3/execution/protection_manager.py`
- `swingtradev3/execution/trailing_engine.py`
- `swingtradev3/broker/types.py`
- `swingtradev3/broker/reducer.py`
- `swingtradev3/execution/reconciler.py`

Current Kite calls:

- `get_gtts()`
- `get_gtt(trigger_id)`
- `place_gtt(...)`
- `modify_gtt(...)`
- `delete_gtt(trigger_id)`

Current assumptions:

- every protected live position has one OCO GTT id
- `trigger_values[0]` is stop-loss
- `trigger_values[1]` is target
- triggered leg index `0` means stop
- triggered leg index `1` means target
- Kite nested order result payload can expose exit order id/status

This is one of the highest-risk migration areas.

### Postbacks / Webhooks

Code paths:

- `swingtradev3/api/routes/postbacks.py`
- `swingtradev3/broker/postbacks.py`
- `swingtradev3/broker/reducer.py`
- `swingtradev3/api/middleware/auth.py`

Current endpoint:

- `POST /broker/postbacks/kite`

Current verification:

- Kite checksum = SHA256 of `order_id + order_timestamp + KITE_API_SECRET`

The reducer can stay broker-neutral, but the route, signature verification, and
payload normalizer need provider-specific implementations.

### Kite MCP

Code paths:

- `Dockerfile.kite-mcp`
- `docker-compose.yml`
- `docker-compose.dev.yml`
- `swingtradev3/integrations/kite/mcp_client.py`
- `swingtradev3/data/kite_fetcher.py`
- `swingtradev3/tools/execution/gtt_manager.py`
- `docs/runbooks/kite-mcp-setup.md`

Current MCP tools used by app code:

- `get_historical_data`
- `get_ltp`
- `place_gtt_order`
- `modify_gtt_order`
- `delete_gtt_order`

Architecture note:

- Direct Kite SDK calls are the primary live path.
- `kite-mcp` is operationally present in compose, but architecturally optional.
- For Upstox, do not make MCP part of critical execution. Use direct REST/SDK for
  orders, GTT, and state reconciliation. Optional MCP can remain assistant/operator
  tooling only.

## Kite Vs Upstox Capability Comparison

| Capability | Current Kite Usage | Upstox Equivalent | Assessment |
| --- | --- | --- | --- |
| API pricing | Data APIs require paid Kite Connect/data access; current renewal is about INR 500/month | Upstox official pages advertise free API subscription and free trading/data APIs | Upstox likely cheaper for API access |
| Auth | Browser login, `request_token`, `generate_session`, daily access token | OAuth-style login and token exchange; token expires around next trading session boundary | Same capability, different implementation |
| Order placement | Entry limit CNC, exit market CNC, tags | Place/modify/cancel orders; delivery product mapping needed | Same, validate market-order behavior |
| Order book/trades | Orders, order history, trades, order trades | Order book, order history, trades/order trades | Same |
| Holdings/positions | Holdings and net/day positions | Holdings and positions | Same |
| Funds/margins | Account margins and order margin estimate | Funds/margin and margin details APIs | Same, response mapping needed |
| LTP/quotes | LTP by exchange:tradingsymbol | LTP, OHLC, full market quote | Same |
| Historical candles | Historical by instrument token | Historical/intraday candles by instrument key | Same, likely free |
| Instrument master | Kite instrument dump/token lookup | Upstox BOD instruments/search and `instrument_key` | Same capability, different identity model |
| Quote WebSocket | `KiteTicker`, full-mode ticks, instrument tokens | Market Data Feed V3, protobuf/instrument keys | Same capability, harder integration |
| Order updates | Kite WebSocket order updates, optional postbacks | Portfolio stream and webhooks | Same or better event channels |
| GTT/OCO | Kite GTT OCO trigger with two legs | Upstox GTT/conditional orders | Same on paper, highest semantic risk |
| Static IP / SEBI rules | Static IP/compliance constraints apply for API orders | Static IP required for order APIs from Apr 1, 2026 | Same operational burden |
| MCP | Zerodha MCP sidecar available and self-hosted | Upstox MCP exists, but should be treated as non-critical tooling | Not a direct execution replacement |

## Upstox Advantages

- API subscription/data access appears free from official Upstox material.
- Covers the same broad broker surface needed by this stack.
- Official webhook support for order and GTT events is useful for reconciliation.
- Clearer current documentation around static IP and algo-order constraints.
- Read-only long-lived token options may help non-execution data workflows, if
  the account/app qualifies.

## Upstox Risks And Unknowns

- Market-data stream uses a different model from Kite callbacks and may require
  protobuf decoding.
- Upstox instrument identity uses `instrument_key`, not Kite integer
  `instrument_token`.
- Upstox GTT payload/status/trigger-leg semantics must be mapped and tested
  carefully before any live protective-order use.
- Current code has many names and errors hardcoded as Kite-specific, for example
  `has_kite_session`, `KITE_SESSION_REQUIRED`, `KiteBrokerStream`, and
  `normalize_kite_*`.
- Upstox WebSocket subscription scale should be confirmed against current V3 docs
  and real account behavior before large-universe streaming.
- API subscription may be free, but normal brokerage, statutory charges, DP
  charges, and any account-specific charges still apply.
- Any expired promotional brokerage wording should not be treated as current
  pricing without confirmation from Upstox.

## Why The Switch Is Not Easy

The internal database model is reasonably broker-neutral:

- `broker_order_id`
- `broker_tag`
- `broker_orders`
- `broker_fills`
- `positions`
- `protective_triggers`
- `execution_events`
- `reconciliation_runs`

But the runtime code is not yet broker-neutral. It imports Kite directly in auth,
execution, reconciliation, streaming, GTT, data, tests, postbacks, and ops checks.

The hardest gaps are below.

### 1. GTT Protection

The current protection engine assumes Kite OCO GTT shape:

- one trigger id per protected position
- two trigger values
- stop/target ordering by array index
- nested Kite order results after trigger

Upstox may support the same business behavior, but the event shape will differ.
The adapter must prove these mappings:

- active protection
- stop leg triggered
- target leg triggered
- exit order id produced
- exit order filled/rejected/cancelled
- GTT expired/cancelled/rejected
- trailing-stop modification accepted/rejected

Incorrect mapping here can make the system believe a position is protected when
it is not, or misclassify a stop-loss exit as a target exit.

### 2. Auth / Session

Kite auth is request-token based. Upstox is OAuth-style. The project needs:

- provider-neutral session storage
- new env vars
- new login helper
- new token exchange
- new expiry rules
- replacement for `has_kite_session()`
- replacement for `KITE_SESSION_REQUIRED`
- preflight checks that say "broker session" instead of "Kite session"

### 3. WebSocket

Kite gives direct Python callbacks through `KiteTicker`. The current stream class
depends on that callback model and on `instrument_token`.

Upstox needs a separate stream adapter that:

- authenticates to Upstox stream endpoints
- subscribes by `instrument_key`
- decodes V3 market-data messages
- normalizes quote ticks into the app's quote cache shape
- consumes portfolio/order stream updates or webhooks
- emits broker-order events into the existing reducer
- exposes the same connection health fields used by kill switches

## Proposed Broker Interface

Before adding Upstox, introduce a provider-neutral boundary.

Suggested modules:

```text
swingtradev3/broker/interface.py
swingtradev3/broker/providers/kite/
swingtradev3/broker/providers/upstox/
```

Suggested interface surface:

- `has_session()`
- `fetch_profile()`
- `fetch_positions()`
- `fetch_holdings()`
- `fetch_margins()`
- `calculate_order_margins(orders)`
- `fetch_orders()`
- `fetch_order_history(order_id)`
- `fetch_trades()`
- `fetch_order_trades(order_id)`
- `fetch_ltp(exchange, ticker)`
- `fetch_historical_data(ticker, exchange, interval, lookback_days)`
- `place_order(...)`
- `fetch_protective_orders()`
- `fetch_protective_order(trigger_id)`
- `place_protective_oco(...)`
- `modify_protective_oco(...)`
- `delete_protective_order(trigger_id)`
- `resolve_instrument(ticker, exchange)`
- `build_stream()`
- `verify_webhook(payload, headers)`
- `normalize_order_event(payload)`
- `normalize_position_snapshots(...)`
- `normalize_protective_trigger(payload)`

The goal is not to make every broker identical. The goal is to make the rest of
the execution system depend on one internal contract.

## Migration Plan

### Phase 1: Broker Boundary, No Behavior Change

- Add broker interfaces and provider selection.
- Move current Kite implementation behind `broker/providers/kite`.
- Keep existing function names as compatibility wrappers temporarily.
- Run full tests to prove no behavior changed.

### Phase 2: Neutral Naming

- Replace app-facing `has_kite_session()` with `has_broker_session()`.
- Replace `KITE_SESSION_REQUIRED` with `BROKER_SESSION_REQUIRED`.
- Replace health label `kite_api` with `broker_api`.
- Keep Kite-specific names only inside the Kite provider.

### Phase 3: Upstox REST Adapter

- Add Upstox auth/session storage.
- Add instrument lookup and ticker/instrument-key mapping.
- Add quotes, candles, holdings, positions, funds/margins.
- Add order placement, order book, trades, order history.
- Add contract tests with mocked Upstox payloads.

### Phase 4: Upstox GTT And Webhooks

- Implement Upstox GTT create/modify/delete/list/detail.
- Add Upstox GTT normalizer fixtures for active, triggered, rejected, cancelled,
  expired, and modified cases.
- Add Upstox webhook route and verification.
- Keep live protective-order placement disabled until sandbox/paper behavior is
  verified.

### Phase 5: Upstox Streaming

- Implement Upstox market-data stream.
- Implement portfolio/order stream or webhook ingestion.
- Normalize stream ticks to the existing quote cache.
- Normalize order updates to `BrokerOrderEvent`.
- Verify stream freshness and kill-switch behavior.

### Phase 6: Runtime And Docs

- Make `kite-mcp` optional instead of required for a non-Kite provider.
- Add `.env.example` entries for selected broker provider.
- Update Makefile login target to provider-aware login.
- Update phase checks and runbooks.

### Phase 7: Soak

- Run full tests.
- Run backtest/paper using Upstox historical data.
- Run sandbox or smallest possible live checks.
- Run live with `NEW_ENTRIES_ENABLED=false` first.
- Validate startup reconciliation, stream connection, quote freshness, order
  book sync, holdings sync, and GTT sync.

### Phase 8: Controlled Live Rollout

- Enable live exits first.
- Enable one-symbol/small-quantity entries.
- Confirm a complete lifecycle:
  - entry submitted
  - fill confirmed
  - GTT armed
  - GTT modified/trailing
  - exit filled
  - reconciliation clean
- Only then consider normal sizing.

## Tests To Add Or Generalize

Generalize existing Kite tests:

- `tests/test_execution/test_phase3_hardening.py`
- `tests/test_execution/test_phase0_preflight.py`
- `tests/test_execution/test_phase0_guardrails.py`
- `tests/test_execution/test_broker_reducer.py`
- `tests/test_execution/test_phase6_reconciliation.py`
- `tests/test_api/test_postbacks.py`
- `tests/test_phase2_timesfm.py`

Add new tests:

- broker interface contract tests
- Upstox auth/session expiry tests
- Upstox order placement payload tests
- Upstox order update normalizer tests
- Upstox trade/fill normalizer tests
- Upstox position/holding normalizer tests
- Upstox GTT active/triggered/rejected/cancelled fixtures
- Upstox webhook verification tests
- Upstox stream decoding tests
- reconciliation tests using Upstox snapshots

## Decision Matrix

| Option | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| Renew Zerodha now | Lowest engineering risk; current code already works with Kite | INR 500/month data cost; still tied to Kite | Best if live trading is needed immediately |
| Switch directly to Upstox now | Potentially removes API/data subscription cost | Medium-high migration risk; dangerous around GTT/stream/auth | Do not do as a direct replacement |
| Build broker adapter, then add Upstox | Preserves Kite fallback; lowers long-term provider lock-in | More engineering work up front | Best long-term path |
| Remove broker APIs and use only MCP | Simpler assistant tooling | Not appropriate for critical live execution | Do not use for execution core |

## Source Links

Zerodha:

- https://zerodha.com/products/api/
- https://kite.trade/docs/connect/v3/
- https://kite.trade/docs/connect/v3/user/
- https://kite.trade/docs/connect/v3/orders/
- https://kite.trade/docs/connect/v3/gtt/
- https://kite.trade/docs/connect/v3/portfolio/
- https://kite.trade/docs/connect/v3/market-data-and-instruments/
- https://kite.trade/docs/connect/v3/websocket/
- https://kite.trade/docs/connect/v3/historical/
- https://kite.trade/docs/connect/v3/postbacks/
- https://zerodha.com/z-connect/updates/nses-new-algo-trading-circular

Upstox:

- https://upstox.com/trading-api/
- https://upstox.com/developer/api-documentation/open-api/
- https://upstox.com/developer/api-documentation/authentication/
- https://upstox.com/developer/api-documentation/get-token/
- https://upstox.com/developer/api-documentation/orders/
- https://upstox.com/developer/api-documentation/gtt-orders/
- https://upstox.com/developer/api-documentation/market-quote/
- https://upstox.com/developer/api-documentation/historical-data/
- https://upstox.com/developer/api-documentation/instruments/
- https://upstox.com/developer/api-documentation/websocket/
- https://upstox.com/developer/api-documentation/webhook/
- https://upstox.com/developer/api-documentation/rate-limiting/
- https://upstox.com/developer/api-documentation/announcements/algo-trading-circular/
- https://upstox.com/developer/api-documentation/mcp-integration/
