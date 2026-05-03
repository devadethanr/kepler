# Phase 9 Analysis

Date: 2026-05-04

## Scope

Phase 9 in `docs/architecture/live_trading_one_shot_plan.md` is the live-trading
verification and staged enablement phase. It is not a feature-build phase by itself;
it is the point where Phases 0-8 must prove that execution, reconciliation,
operator controls, and the dashboard can survive realistic broker and process
failure modes before live automation is expanded.

This analysis uses the current implementation after the Phase 8 dashboard work and
the latest execution/protection changes. The relevant Phase 9 target areas are:

- state-machine and execution coordinator tests
- broker reducer tests
- GTT watchdog and reconciliation tests
- operator controls tests
- entry-to-exit lifecycle tests
- restart recovery tests
- staged enablement from paper soak to supervised and then unattended live use

## External Assumptions Checked

Primary references checked during this pass:

- [Kite Connect GTT API](https://kite.trade/docs/connect/v3/gtt/) documents
  GTT states including `active`, `triggered`, `disabled`, and `rejected`.
  This supports treating disabled/rejected protection as explicit recovery
  conditions rather than normal active protection.
- [Kite Connect Orders API](https://kite.trade/docs/connect/v3/orders/) states
  that successful order placement does not guarantee exchange execution and that
  order status must be confirmed through order history/current details or
  asynchronous postbacks. This supports the Phase 9 emphasis on submitted-but-not
  filled, reconnect fills, retry, and reconciliation tests.
- [NSE market timings](https://www.nseindia.com/market-data/market-timings)
  confirms the IST-based equity session boundaries used by the system: pre-open,
  normal market, closing/post-market, and T+0 timing distinctions. Because NSE
  can update these timings, the dashboard/session classifier should keep using
  config-backed IST clocks and not hard-coded UI-only labels.

## What Is Covered Now

The implementation already has a broad test floor around the execution path:

- duplicate approval handling is idempotent
- submitted-but-unfilled live orders stay submitted until broker fill confirmation
- partial fills are reduced from broker trades
- stale auth blocks or escalates before live action
- broker disconnects move the system into explicit degraded states
- manual broker-side closes are reconciled through acknowledgement flows
- restart reconstruction covers active order and trigger state
- Phase 8 dashboard API and SSE flows are covered by backend and frontend tests

This pass added the remaining focused Phase 9 regressions and harness hardening:

- `tests/test_execution/test_state_machine.py`
  covers broker-status to order-intent state transitions.
- `tests/test_execution/test_reconciliation.py::test_submission_timeout_reconciles_later_fill_by_broker_tag`
  covers the safe HTTP-timeout path: a timed-out live order is kept in
  `submitting` with a broker tag and later reconciles from broker truth.
- `tests/test_execution/test_gtt_watchdog.py::test_rejected_gtt_arm_blocks_entries_and_requires_operator_intervention`
  covers raw GTT arm rejection and proves the system blocks new entries and moves
  the position to operator intervention instead of calling it protected.
- `tests/test_execution/test_operator_controls.py`
  covers independent block reasons so clearing one safety block cannot
  accidentally clear another.
- `tests/test_execution/test_phase4_execution.py::test_reconcile_protection_pending_intent_arms_gtt_after_restart`
  covers restart after an entry fill where protection was still pending and proves
  reconciliation arms the missing GTT instead of leaving the open position
  unprotected.
- `tests/test_execution/test_phase5_protection.py::test_watchdog_recovers_disabled_protection_after_corporate_action`
  covers a disabled broker-side GTT, the likely corporate-action failure mode, and
  proves the watchdog recreates protection.
- `tests/test_execution/test_phase5_protection.py::test_watchdog_routes_target_exit_rejection_to_operator_intervention`
  covers a target trigger followed by exit-order rejection and proves the current
  recovery path is critical operator intervention rather than silent continuation.
- `tests/test_integration/test_entry_to_exit_lifecycle.py`
  covers entry fill -> protection arm -> stop trigger -> exit order open ->
  confirmed exit fill.
- `tests/test_integration/test_restart_recovery.py::test_restart_after_gtt_trigger_before_exit_fill_persists_close`
  covers restart after a GTT-triggered exit order where the fill had not yet been
  persisted locally.

## Phase 9 Scenario Matrix

| Scenario from Phase 9 | Current status | Notes |
| --- | --- | --- |
| Duplicate approval click | Covered | Existing approval route tests prove queued executions are idempotent. |
| Retry after HTTP timeout | Covered | Timeout now becomes `submission_uncertain`/`submitting` with broker-tag reconciliation. |
| Entry order submitted but unfilled | Covered | Live order remains submitted and does not create a filled position prematurely. |
| Partial fill | Covered | Broker reducer uses order trades to derive partial quantities. |
| Fill confirmed after reconnect | Covered | Submitting-by-tag reconciliation and restart recovery cover broker-truth fill recovery. |
| GTT rejected | Covered | Raw GTT arm rejection blocks entries and requires operator intervention. |
| GTT disabled after corporate action | Covered | Added watchdog recovery test. |
| Stop trigger -> exit open -> exit fill | Covered | Added full entry-to-exit lifecycle integration test. |
| Target trigger -> exit rejected -> recovery path | Covered | Added operator-intervention recovery test. |
| Restart after entry fill before GTT arm | Covered | Added reconciliation/protection-pending restart test. |
| Restart after GTT trigger before exit fill persisted | Covered | Added restart recovery integration test. |
| Stale auth before market open | Covered | Existing reconciler/session/preflight coverage handles stale auth escalation. |
| Broker disconnect during open position | Covered | Existing protection and degraded-state tests cover disconnect behavior. |
| Manual broker-side close | Covered | Existing reconciliation acknowledgement tests cover operator-confirmed closes. |

## Dashboard And Operator Surface

The Phase 8 dashboard is relevant to Phase 9 because it is the operator surface for
the staged live rollout. Current backend and frontend tests cover the DB-backed
dashboard summary, audit/feed APIs, SSE parsing, and frontend API client behavior.

The dashboard is useful for observing the live system, but Phase 9 should not treat
the dashboard as the source of truth. Execution state must continue to come from
database-backed order intents, broker reconciliation, protection state, audit
events, and run state. The dashboard should only render that state and provide
operator controls through audited API calls.

## Test Harness Finding

`make test` and `make test-file` now isolate pytest from the live worker. If the
worker is running, the Makefile stops it before pytest starts and restores it
after the run. This prevents the worker from consuming shared queue/state during
tests while preserving the normal dev stack after verification.

`tests/test_evaluation/test_eval_live.py` is now opt-in behind
`RUN_LIVE_EVAL=true`. It performs real market/news/LLM calls and is useful as a
manual live evaluation, but it is not a deterministic Docker test gate.

## Verification Run

Commands were run from `swingtradev3/` using the Makefile and Docker stack:

- `make test-file file='tests/test_execution/test_phase0_guardrails.py tests/test_execution/test_state_machine.py tests/test_execution/test_reconciliation.py tests/test_execution/test_gtt_watchdog.py tests/test_execution/test_operator_controls.py tests/test_execution/test_phase4_execution.py tests/test_execution/test_phase5_protection.py tests/test_integration/test_entry_to_exit_lifecycle.py tests/test_integration/test_restart_recovery.py'`
  - Result: 33 passed.
- `make test`
  - Result: 281 passed, 3 skipped, 41 warnings.
- `docker compose -f ../docker-compose.dev.yml --env-file .env exec -T dashboard npm test`
  - Result: 8 passed.
- Changed-file Ruff check for the Python files touched in Phase 9
  - Result: all checks passed.
- Worker status after test isolation
  - Result: worker restored and reported `Up`.

## Completion Judgment

Phase 9 is complete as a code and deterministic verification phase. The
remaining ladder items are operational rollout controls: paper soak, supervised
live modes, same-day unattended mode, and multi-day unattended mode after DDPI/POA
confirmation. Those stages still require operator evidence and signoff before the
runtime flags should be advanced.

Paper-soak acceptance evidence should track reconciliation drift, missed
protection arms, dashboard freshness, auth freshness, audit completeness, and
operator acknowledgement latency across the required 10 trading days.
