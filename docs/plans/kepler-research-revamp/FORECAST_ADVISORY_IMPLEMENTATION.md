# Next implementation: synchronized office and advisory forecasting

**Updated priority:** [VISUAL_WORKSPACE_COMPLETION_HANDOFF.md](VISUAL_WORKSPACE_COMPLETION_HANDOFF.md)
comes first after the user's screenshots. The office foundation is partial;
complete its usability and interactions as well as the correctness fixes below
before starting new forecasting work. Preserve any work already in progress.

4 November 2026. Start from Track C `3bd12d0`, findings `5b3db54` and
[independent review](VISUAL_WORKSPACE_REVIEW.md). Keep the implemented office and
Codex/Gemma/Qwen runtime. This phase repairs two UI issues and makes the existing
TimesFM component a usable **shared CPU tool**. It does not add a third resident
chat model or confer trading authority.

## 1. Repair current-event synchronization

Implement the two fixes in the review before adding forecast events:

- Distinguish successful room polling from verified event delivery. Reconcile
  snapshot sequence versus the highest contiguous delivered cursor with bounded missing-history
  reads and pagination; keep current activity unknown until caught up. Recover
  a silent OPEN SSE connection without duplicate events, new rooms or inference.
- Preserve `recipient: room` on broadcast bubbles and accessible controls. Keep
  a broadcast distinct from an addressed analyst/skeptic handoff.

Test silent OPEN SSE with an advancing snapshot, normal quiet inference with an
up-to-date cursor, delayed/out-of-order polls, concurrent SSE/catch-up, failed or
partial history pages, terminal gaps, cancellation and room-switch cleanup.
Verify the corrected office in an actual browser with a labeled offline trace;
saved real rooms must retain their messages and outcomes unchanged.

## 2. Repair and pin TimesFM before connecting it

Read [TIMESFM_AUDIT_AND_REUSE.md](TIMESFM_AUDIT_AND_REUSE.md) and the completed
[follow-up findings](FOLLOW_UP_FINDINGS.md). Refresh the current call sites;
the old forecaster still checks ticker/horizon cache before validating input,
accepts future cache timestamps and can invent ±5% fallback bounds. The legacy
ADK wrapper retries inference after broad exceptions and always says generated.
The scorer serializes the entire stock block, so legacy forecast data may already
reach its prompt. These are concrete repairs, not requests for another spike.

Retain the measured **TimesFM 2.5 200M** checkpoint
`google/timesfm-2.5-200m-pytorch@1d952420fba87f3c6dee4f240de0f1a0fbc790e3`.
Resolve the installed package/source bytes before pinning the compatible library
and Torch environment. Source inspected in the earlier review was
`e51928e27119cb17bebc005be2696b75e0a9e688`; reported installed package version
3.0.2 alone does not prove that source mapping. Record hashes and actual API
behavior. Replace the product's unpinned Git dependency; do not silently move
to TimesFM 3.0 or redownload an unchanged checkpoint.

Use the returned point forecast explicitly. At the tested 2.5 pin it is full-array
channel **5**, with quantile channels **1–9** at nominal levels **0.1–0.9**.
Channel 0 is not the separately returned point. Validate batch/horizon/channel
shapes, finite outputs and quantile order; never infer mapping from array width.
If using the measured upstream crossing correction, record its configuration;
remaining invalid shapes/crossings fail explicitly. Ordering is not calibration.
Remove fabricated bounds, automatic entries/stops/targets and success wording
on degraded output. Do not rerun inference because a later unrelated step failed.

## 3. Trusted input and immutable forecast artifact

Expose a small typed gateway operation, for example `forecast_timesfm`, using
the existing read-only capability and evidence registry. Its inputs are a trusted
immutable candle-snapshot reference, resolved instrument and horizon/cutoff.
Agents cannot supply invented price arrays, arbitrary files or their own model
configuration. A validated application adapter may construct snapshots from
existing permitted historical candles; a cached parquet is not sufficient proof
of freshness or point-in-time availability.

Initial scope is daily closes, **32–512 completed bars**, default **20** and
maximum **128 future bars**. Validate instrument/exchange, units/currency,
ordered unique session timestamps, positive finite closes, calendar and explicit
adjustment/source/version basis before cache lookup. Reject incomplete/future
bars and unavailable-by-cutoff observations. Preserve unknown adjustment basis
as unknown; do not manufacture corporate-action history. Unknown/missing session
calendars yield an explicit unavailable temporal result, not invented dates.
Keep current-vintage historical data labeled as such; it cannot retrospectively
prove that an old forecast could have existed at its simulated origin.

Each result records:

| Field | Required meaning |
|---|---|
| Status and reason | `ok`, `insufficient_data`, `invalid_data`, `unavailable`, `busy`, `timeout` or `cancelled`; degraded results contain no forecast values. |
| Identity and provenance | Exact instrument, source/snapshot/version, interval, units, adjustment basis, calendar version, canonical input hash. |
| Time | Last completed bar, data availability cutoff, request cutoff, generation/first-seen time and future session labels. These are different fields. |
| Model | Checkpoint/library/artifact pins, numerical config, CPU device and thread count. |
| Output | API-returned point path; explicitly mapped nominal quantiles; warnings and same-input last-price/drift baseline paths. |
| Artifact operation | Stable artifact ID/hash, original inference latency and generation outcome. |
| Access record | Per-request cache hit/miss, queue/load/access latency and cancellation/error status; recorded separately from the immutable artifact. |

Store immutable artifacts using existing durable infrastructure and an additive
migration only if needed. Canonical cache identity includes values/timestamps,
all provenance/cutoff fields, horizon, model and config revisions. Validate first;
reject future creation timestamps and invalid/stale cache records. Use atomic
concurrency-safe storage. Preserve the old JSON cache as legacy evidence and
never silently treat it as the new contract. A current read may reuse the exact
valid artifact; a historical as-of read cannot see an artifact generated later
than its cutoff. Label retrospective evaluation separately.

## 4. One bounded CPU worker

Start from the measured profile: explicit **CPU**, **two Torch threads**, compiler
off, lazy single-flight load, one inference at a time and a small bounded queue.
Account for process multiplication: one per API worker would not be shared.
Use one supervised worker reachable by the research service; agents reuse it.
Native scripts/isolated environments are valid. No GPU allocation or changes to
the two existing LLM endpoints.

Cancellation and timeout must release the actual computation. Cancelling an
async wait around `to_thread` does not stop Torch: either complete within the
owned slot or terminate/join the owned worker before admitting another job.
Expose unloaded/loading/ready/degraded, bounded queue and recovery. Inference
must not execute within a broker mutation/protection path.

The earlier sample was about **2.28 GiB RSS** and **0.111 s warm latency**; this is
not combined-load evidence. Refresh available host RAM/swap, measure cold and
warm latency plus peak RSS while the normal services, browser and existing pair
coexist. Stop admission on sustained pressure rather than killing existing
services. If the worker cannot fit, keep typed unavailable and complete the
independent contract/UI work; no silent GPU placement or engine migration.

## 5. Room integration and visible advisory evidence

Both existing participants can invoke the shared tool when useful and inspect
the same saved artifact. Use existing tool-start/result/status events and the
Pixel office/inspector. Add a compact forecast view: point/quantile paths,
session horizon, same-input baselines, provenance, timestamps, latency and an
explicit **nominal, uncalibrated** band label. Preserve missing-data states and
saved replay after reload/restart. No fake forecast in a normal app view.

Do not add ForecastAnalyst as a third required participant now. That later logical
role can use this same tool/model pair if it adds measurable interpretation.
Keep the discussion adaptive; forecasting does not become a mandatory turn.

Contain legacy influence explicitly: exclude forecast fields from scoring,
recommendation/risk inputs and automatic signal promotion, including nested
legacy/graph packets where they actually enter those paths. Retain old records
and other signals. Record the exact narrow call-site changes and verify with
hostile forecast payloads that changed forecast values cannot change scoring
inputs or entry/stop/target/sizing inputs. A UI label alone is not containment.
Broker services, protective orders, manual live-entry approval and other controls
remain intact; no broker-worker restart is needed for forecast delivery.

## 6. Validation and finite local exercise

Use the protected disposable launcher for integration tests. Add focused tests
for invalid/empty/NaN/Inf/zero bars even with a warm cache, changed values under
the same ticker/horizon, cross-cutoff and future caches, concurrent initialization
and atomic writes, exact point/quantile mapping, no fabricated intervals, worker
timeout/cancel/crash cleanup and advisory containment. Contract fixtures are
labeled offline; separately exercise the actual pinned model on permitted real
saved candles. Do not run the old random-walk test against the product cache.

Complete engineering and offline/browser checks with **zero new model admissions**.
For a final tool-connected smoke check, if existing services/resources permit,
use at most **two rooms**, **16 model / 16 tool admissions total**, four minutes
per room, no automated retries. This is the new forecast-task ceiling when this
handoff is executed, not unused market budget. Persist it across cancellation
and restart; count failures/denials/unknown usage honestly. Provider reads, if
needed for permitted candles, have a separate explicit small cap recorded before
the first fetch; no source crawling or GIFT/STI requalification. Stop at the cap
and report partial results; successful tool calls do not establish grounded
reasoning. If models remain stopped, finish independent work and report the
unrun smoke check without pretending it passed.

Same-input last-price/drift comparisons demonstrate computation and display
only. No new broad backtest or predictive claim is required for an advisory
tool. Prior SP500 results had no demonstrated baseline advantage and nominal
80% coverage **64.5%**; NSE skill is unestablished. Any later score influence
needs its own chronological evaluation, calibration and user decision.

Write `FORECAST_ADVISORY_FINDINGS.md` after execution, not a pre-filled success
page. Report precise implemented/failed/blocked/unrun scope, source/evidence
commits, tests and artifacts, actual model/data provenance, service state,
resource observations, usage and preserved runtime/control hashes. Push source
and sanitized evidence on `feat-generic-broker`. Return the handback below so
the next review can decide on scheduling and Harness² using the actual results.
