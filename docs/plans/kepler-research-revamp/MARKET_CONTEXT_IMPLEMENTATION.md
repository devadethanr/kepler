# Next phase: integrity fixes and GIFT/Singapore context

2 November 2026. Start from `feat-generic-broker@34a3f40` and the subsequent review-doc commit. Read [FRESH_SOURCE_REVIEW.md](FRESH_SOURCE_REVIEW.md). Keep the installed personal Codex room, active participant instructions, inactive prompt candidates, model pair and serving configuration.

## Result to deliver

Research Desk can display and agents can read a verified market-context snapshot for **GIFT Nifty** and **Singapore/STI**, with explicit instrument identity, source, timestamps, session, delay and quality. Missing entitlement or a stale/delayed source produces an honest state, not an invented quote. A bounded research discussion explains known observations and limits. It does not claim Singapore causes Indian moves or predict an opening gap from a futures spread.

Use parallel file ownership: A fixes stream/snapshot integrity; B qualifies and implements read-only market data; C extends the existing desk/tool integration. Provider discovery and offline data work can proceed independently. Complete A before model-dependent verification of the new tools. No generic framework-selection or commercial-product gate is added.

## A — fix the three reproduced integrity issues

1. **Terminal streams:** the bridge must observe a recognized backend finish reason before reporting completed output or releasing an actionable function call. EOF, `[DONE]` without a terminal reason, malformed/unknown terminal state and interrupted streams must remain explicit failures/incomplete results. Valid JSON is not evidence generation finished. Preserve usage/unknown accounting, IDs, cancellation, legitimate stop/tool endings and text-length truncation; do not dispatch a length-truncated tool.
2. **Historical read context:** preserve the earliest applicable cutoff when a retrieved successor registers its predecessor. A later search must not silently widen an earlier A read. If explicit retrieval handles are used, bind version + cutoff and make context selection visible. Keep the room maximum and frozen allowlist rules, superseded labels and immutable version bodies.
3. **Undated omissions:** report service-level undated cap/omission/count correctly and provide bounded pagination or an explicit no-continuation reason. Handle 3–6 unknown-date matches, larger sets, and later dated pages. Counts are exact only within scanned candidates; if the 1,000-candidate scan is truncated, label totals unknown or lower-bound rather than inventing an exhaustive omission count. Unknown date remains outside known publication-window matches.

Use [cloud probe source/results](evidence/cloud-review-34a3f40/README.md) as historical reproducers, not future tests that must preserve bugs. Add meaningful regressions with corrected expectations. Use controlled local HTTP fixtures and actual temporary SQLite/verified disposable Postgres; no GPU is needed for these corrections. Check stream output-item completion as well as response terminal status so no downstream event looks complete before validity is known.

## B — discover and qualify market data without placing orders

Inspect the existing rate-limited broker/market-data clients, `data/macro_indicators.py`, config and the placeholder scheduler before adding code. Reuse current authentication and read paths; do not create another execution client or bypass shared rate limits. No account values, tokens, cookies or credentials belong in output, fixtures or model context.

Build a small capability table and record observed evidence:

| Input | Verify locally | If unavailable |
|---|---|---|
| GIFT Nifty | Current official instrument/contract master; actual broker/provider mapping; quote, historical and streaming availability separately; account/API entitlement and delayed/live status | Retain typed unavailable/unsupported status and exact non-secret cause. Evaluate a documented permitted delayed source if useful; no broker migration or unannounced paid fallback. |
| Singapore/STI | Exact cash-index identity versus futures/ETF proxy, provider/source rights, timestamp/delay and session/holiday coverage | Display unavailable or the explicitly named proxy/delayed observation. Never silently call an ETF/future STI cash. |
| Nifty reference | Source, instrument, last completed session/close and adjustment/basis needed for any comparison | Omit derived comparison and explain the missing reference. |

Start from the official [NSE IX](https://www.nseix.com/) and [SGX](https://www.sgx.com/) product/session sources and selected provider documentation. Existing Kite capabilities have separate [quote](https://kite.trade/docs/connect/v3/market-quotes/), [history](https://kite.trade/docs/connect/v3/historical/) and [streaming](https://kite.trade/docs/connect/v3/websocket/) interfaces; those API docs do not establish GIFT entitlement. Pin the observed source/spec date; do not copy old times or numerical instrument tokens from earlier chats. Earlier presence in a master does not establish current quote entitlement. Probe quote/history/socket read capabilities separately, and stop owned subscriptions after testing.

Use normal existing login workflow if authentication needs the user's interaction; report a dependent auth blocker without asking for secret values or clearing broker controls. Continue independent public-source/calendar/UI work. Public delayed values may be useful when explicitly identified; HTTP 200 and a recently fetched page do not prove a recent exchange quote.

## C — implement a typed snapshot service

A small starting contract:

```text
snapshot_id, provider/source, instrument_id, symbol and underlying,
instrument_kind [cash_index|future|proxy], exchange, contract/expiry if applicable,
quote_value, quote_unit, settlement_currency if applicable,
exchange_asof, provider_asof, received_at, first_seen_at,
market_date, session_id, market_state [open|closed|break|unknown],
delay_seconds_or_unknown, status [ok|partial|stale|unavailable|invalid],
quality_reasons[], reference_value/reference_asof/basis,
source/config/calendar versions and raw observation hash
```

Field spelling can follow existing conventions. Keep market state separate from data quality. A valid last close during a closed session differs from a stale quote during an open session. Missing timestamps/delay remain unknown; receipt time is not exchange time. Preserve source-reported versus locally derived fields distinctly.

Requirements:

- Verify GIFT contract expiry/roll and quote units; index points and settlement currency are different concepts. Never confuse near/next-month futures, a continuous series and the cash Nifty index.
- Use exchange-aware calendars and aware UTC storage with IST/Singapore display. Verify actual sessions, holidays, breaks, midnight crossings and business-date assignment from official current sources. The existing overnight print window and unused start setting are not a calendar.
- Compute returns/spreads only from valid compatible references with stated timestamps/basis. Futures basis includes contract effects; a GIFT/cash spread is not an asserted next opening gap. Missing or mismatched input yields no derived number.
- Enforce deadlines, shared provider rate limits, bounded refresh, connection ownership, stale/out-of-order/error handling and cancellation. Preserve broker execution/protection priority. Start with bounded polling if streaming is unavailable or unnecessary.
- Reuse suitable storage and provenance patterns for immutable observations. Do not put quotes into `news_articles` merely to reuse its schema. Use an appropriate existing market snapshot contract or an explicit additive change, preserving existing data.
- Historical/as-of reads require recorded availability by that cutoff; a current quote or later-revised historical series cannot silently answer an older room. If unsupported, say so.
- Qualify any free/public source against its documented delay and access/retention terms; do not relabel an unofficial mirror as exchange data or guess missing values.

The existing macro cache can remain for its current callers. Its float-only Yahoo helper/four-hour TTL must not become a live-feed label or lose provenance in the new service.

## D — expose context through the existing tools and UI

Add a bounded read-only `market_context` operation, respecting room cutoff and selected scope. It may return a deterministic snapshot/summary; models do not calculate authoritative prices, calendars or risk limits. Keep existing graph/news/file/browser tools and current Codex runtime.

In Research Desk show GIFT and Singapore observations with status, actual instrument/contract, source, exchange/receive time, delay, session, reference basis and explicit unavailable reasons. Preserve live discussion and saved snapshot provenance so reload explains the same run. Keep raw credentials and hidden reasoning out of the UI.

Add a narrow collector refresh hook only after data semantics are verified. `_gift_nifty_check` is presently a log-only placeholder; connecting a read-only refresh is distinct from enabling unattended model research or order decisions. Broad scheduled rooms remain later work. No SLM inference is awaited inside broker order/protection handling.

Singapore context is a descriptive input and an incremental-usefulness hypothesis. It does not establish that STI moves cause Nifty moves. Any future lead/lag or trading-use claim needs separate point-in-time evaluation with calendars, common drivers and realistic costs; it is not a prerequisite for showing correctly labeled observations.

## E — verify once and hand back

Offline tests first: missing stream terminal/tool dispatch, earliest-cutoff preservation, undated omission, source identity, unit/currency/expiry/basis, session/day boundaries, stale/closed/unknown timestamps, errors and saved-cutoff replay. Use synthetic market fixtures only in isolated test stores. Additive migrations use disposable tests/backups as in the current runbook.

On the PC verify real read-only capabilities and one actual snapshot per usable source, plus stale/unavailable behavior. Never synthesize a “live” success when a market/source is closed or entitlement is absent. Report quote/history/socket and session coverage separately. If GIFT is blocked, finish the typed service/UI, demonstrate the real unavailable state and working independent inputs, and give the exact follow-up needed; do not claim live GIFT support complete.

Use the existing source cases as regression evidence, not untouched new research. Inspect repeated questions in prior room history, then check one useful public summary of known source facts/limits and one market-context task. A specific abstention or disagreement is acceptable; it should state what is known and which field/source is missing. Do not force consensus, manufacture a model message, increase budgets blindly or make another model a truth judge.

Suggested fresh inference ceiling: **60 model admissions total**, at most 12 development and 48 integrated checks, including model continuations/retries/cancellation/UI smoke work. Separately cap/count tool admissions at 60 and provider HTTP/subscription activity with its own limits. Plan a feasible small number of rooms; data/calendar/protocol checks require no model generation. Keep the installed participant instructions and inactive candidates. No new model/engine downloads, training or TimesFM authority.

Run focused backend tests and relevant protected disposable checks, frontend tests/typecheck/build, changed-file lint, actual LAN/localhost display, cancellation, reload and API restart. Use a fresh declared run ID/immutable allocation; do not reopen the completed 93/88 source run. Stop at ceilings and report incomplete verification.

Write `MARKET_CONTEXT_FINDINGS.md` with fixes, provider capability matrix, versioned observation evidence, tests/skips, actual model/tool/provider counts, useful room outputs and remaining source/quality limits. Commit/push source and sanitized docs on this branch, preserving the five changing runtime files, original source histories and private backups. Activate only necessary research/API/collector changes; keep broker controls, manual entry approval and existing trading/protection services intact.

Proceed with normal reversible implementation and independent work; no new Codex-selection approval is needed. The required Pixel Agents-style workspace is the next UI milestone after this data-context slice; see [UI_MILESTONE_PLAN.md](UI_MILESTONE_PLAN.md). TimesFM/advisory integration, broader scheduled rooms and Harness² follow in the documented order. Keep the current phase scope/budget unchanged.
