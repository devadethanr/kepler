# Isolated follow-up findings — 1 November 2026

**The three queued requests have been executed. Codex works through an experimental local adapter on both preferred models. Forecast quality gates remain failed. No product implementation or deployment is approved.**

Read alongside [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md), which preserves the original runtime comparison and its failures. These follow-ups do not replace the poor selected-record grounding results, strict-GPU fast-lane timeout, or unsuccessful optimized-runtime arms.

## Run, limits and preservation

Evidence root **F**: /home/devadethanr/.local/state/kepler-spikes/20261101T051358+0530-followups.

The user explicitly authorized browser/network troubleshooting, isolated Codex tool-type fixes and forecast-validity testing after the original work, then asked to resume after the usage pause. All executable prototypes, fixtures, caches and logs are under F; only reporting documents changed in the repository.

- Branch/tested HEAD: feat-generic-broker / 5ebdd171cf3dc3862e1b7a1dd17427ad626471a3. No commit or push.
- Declared limits: 120 minutes, 200 model-call attempts, 200 forecast attempts, 2 GiB additional downloads. Recorded: **106 admitted LLM requests, 127 forecast attempts**, including the deliberately failed forecaster call; approximately 34 minutes through the final cleanup audit. Invalid gateway requests were rejected before inference and logged separately. Additional download was the 48,903-byte historical CSV; runtimes, binaries and image were reused.
- Both model servers remained assigned by GPU UUID, TP=1. Functional Codex tests used 32,768-token context and default llama.cpp placement, which retains CPU embeddings. This is a separate functional arm, not a passing strict full-GPU latency result.
- Sampled peak used/minimum free VRAM: 5070 Ti 7,576/8,297 MiB; 3060 3,580/8,330 MiB. Minimum sampled available RAM 7,332 MiB; no resource-floor stop.
- Seven original production containers retain identical IDs/start times and remain running. No experimental processes, containers or TCP listeners remain. No driver, production config, dependency, broker, graph or service changes.
- Original runtime changes were preserved. Four files remain byte-identical to the initial snapshot; agent_activity.json continued evolving with production running. Original and final snapshots are retained without overwriting newer state.
- No application pytest/conftest imports or graph deletion fixtures were executed. The current forecaster behavioral probe extracted only its class AST into an isolated namespace, with private storage and a real CPU model; it did not import application modules.

Evidence: F/run.json, evidence/cleanup-final.json, evidence/final-work/, evidence/runner-sha256.json. The original R evidence and runner hashes are retained.

## 1. Browser and skill execution

**PASS, fixture scope. No additional network access or host security change was required.**

The original failure occurred while configuring loopback in a private namespace. The successful sandbox maps the invoking host user to UID 0 inside a new user namespace, with new network/PID/IPC namespaces. It can configure only its own loopback. It has no host routes or production sockets; host root privileges were not granted.

The pinned agent-browser 0.41.0 executable and Chrome actually:

1. Opened the loopback inventory fixture.
2. Returned a snapshot and body containing source b1.
3. Denied example.com outside the domain allowlist.
4. Denied a redirect to 169.254.169.254.
5. Closed cleanly.

Both native Codex models discovered the skill, loaded the complete 39,807-byte official core workflow, called the enforcing browser_read bridge, received actual browser output and cited b1. The bridge requires discovery before loading, loading before browsing and the exact approved fixture URL. It grants no shell.

The negative prompt asking Gemma to browse without loading the skill produced a safe refusal before a tool call. Its strict exact-callback/output criterion was therefore **not met**; this is retained, rather than counted as an executed denial callback. Four separate direct capability checks passed: missing skill, missing discovery, forbidden URL and repeated tool action. This proves the bridge checks independently of model obedience.

This does not establish unrestricted internet browsing, authenticated pages or production news freshness.

Evidence: browser-probe.json, conformance-suite.json, edge-cases.json, direct-capability-denials.json, real-tool-executions.ndjson and native RPC traces.

## 2. Working Codex and protocol fixes

**PASS for the bounded experimental research-worker configuration on both Gemma 4 E4B and Qwen3.5-9B. Unmodified native endpoint failures remain recorded.**

The initial rejected tool was the multi_agent_v1 namespace. Disabling Codex's optional multi-agent, shell, goals and sleep features removed that namespace. This alone was insufficient: Gemma returned commentary instead of exactly READY, and Qwen rejected the ordering of Codex developer/system messages.

The isolated adapter therefore:

- Uses flat approved dynamic research functions and filters the two remaining ungranted built-ins, request_user_input and view_image. Unknown function or namespace definitions fail closed.
- Translates the supported text/function Responses subset to Chat Completions, merges system/developer instructions at the beginning in their original order, preserves user/tool evidence roles and explicitly disables thinking for this functional arm.
- Caps generation at 512 tokens for normal Codex turns, temperature 0 and one model slot per GPU; no hosted authentication or fallback is configured.
- Emits Responses events from actual streamed model text/function calls, with sequence numbers, stable response/item/call IDs and content/output indices. It does not manufacture model answers or successful tool results.
- Checks tool names, argument keys/types/bounds and issued call ownership; rejects unmatched outputs and changed result replays before inference.
- Shares atomic model/tool/token admission across coordinated threads, includes retries and applies cancellation/deadline checks. Unknown usage reserves the entire 32,768-token context per admitted model call.

The supported subset excludes multimodal/encrypted reasoning transport, arbitrary native tool namespaces and unrestricted coding tools. This disposable bridge is not a product adapter, full OpenAI API implementation or a change to the user's normal Codex configuration.

| Gate | Result and evidence |
|---|---|
| C1 native App Server | Both models returned exactly READY; real initialized/thread/turn/completed lifecycle |
| Adapted R2 | 84 streams checked: monotonic sequence numbers, stable IDs/indices, tool identities and completed terminal outputs; zero validator problems |
| Adapted R3 | Actual tool/output continuation; unmatched call ID, cross-model call ID, unknown function and namespace denials |
| C2 | Both models passed graph, artifact search/read, traversal denial, full skill/browser and real TimesFM tool scenarios: 5/5 each |
| Additional C2 states | Native empty, unavailable, unsupported_as_of, graph limit/hops, symlink and .env cases passed 7/7; unloaded-browser exact-callback case safely refused, as described above |
| C3 generation interrupt | Both native turns terminal interrupted; backend observed busy then idle about 0.11 seconds after the turn returned; late tools denied |
| C3 pending tool interrupt | Actual native callback interrupted before execution; late execution denied |
| C3 crash and recovery | Model stopped during a pending native tool callback; exactly one real tool execution, failed terminal; restarted model and same Codex thread continued without repeating the tool |
| C4 global admission | Eight simultaneous HTTP attempts across both model routes admitted exactly 2 and rejected 6 with 429; reserved 65,536 tokens; post-cancel work denied |
| C4 other boundaries | Cross-lane exhausted model budget, exhausted tool budget, zero token allowance and expired injected deadline rejected before execution |
| C5 routing | Concurrent externally mediated native Codex threads reached different independently logged model endpoints under one coordinator/budget |

C5 is **externally mediated top-level threads**. Native heterogeneous spawn/message/provider inheritance was not demonstrated; native multi-agent tools are disabled in the working research configuration. The installed Codex binary remains 0.164.0 with the original binary hash. Servers use the original pinned llama.cpp/GGUF artifacts, not the unsuccessful vLLM/SGLang arms.

An earlier timed crash attempt lost a race to model completion and failed its criterion. The subsequent callback-triggered crash is the passing evidence; both traces are retained.

Protocol handling was checked against the [official Responses event reference](https://developers.openai.com/api/reference/resources/responses/streaming-events); lifecycle/tool callbacks used the installed App Server schemas and [official App Server documentation](https://developers.openai.com/codex/app-server/).

Evidence: codex-bridge-C1.json, adapted-stream-validation.json, conformance-suite.json, final-proofs.json, edge-cases.json, bridge-http.ndjson, bridge-events.ndjson and per-worker RPC logs.

## 3. Evidence room and ADK comparison

Both Codex and ADK completed the same frozen fixture exchange:

- Analyst retrieved g1 and f1 and addressed the skeptic.
- Skeptic discovered/loaded the pinned browser skill, retrieved b1 and challenged inventory certainty.
- Analyst explicitly revised to uncertain inventory and abstained.
- Forecast role consumed t1-real, described its synthetic/uncalibrated limits and abstained.

A deliberately unavailable browser produced an honest missing-evidence message; the analyst then retained g1/f1 supply exposure, reported missing b1 and abstained. No browser content was invented.

The held-out evaluator was a predeclared deterministic rubric checking actual tool provenance, addressed messages, challenge, revision and abstention. Prompts deliberately prescribed the fixture wording. These are controlled capability checks, not evidence of spontaneous expert reasoning, a production adaptive room, financial competence or independent corroboration between related models.

The ADK comparison reused immutable application image sha256:29cb059aac8af06008d3a425d6f11cd25b8388a100824cf16e157bb3f03a04ee: google-adk 1.33.0, LiteLLM 1.84.0, httpx 0.28.1. A disposable read-only container had no network, no production environment or volumes, and only a guarded Unix-socket bridge to the experimental model/tool routes. No application agent modules ran.

| Matched fixture, n=1 each | Codex | ADK |
|---|---|---|
| Declared global model/tool caps | 12 / 8 | 12 / 8 |
| Conservative token cap / wall deadline | 393,216 / 120 s | 393,216 / 120 s |
| Context / normal generation cap | 32,768 / 512 | 32,768 / 512 |
| Actual model/tool calls | 10 / 6 | 10 / 6 |
| Actual conservative tokens | 327,680 | 327,680 |
| Evidence-room outcome | PASS / ABSTAIN | PASS / ABSTAIN |

Codex measured 6.69 seconds for the room; ADK measured 10.95 seconds including container startup/imports. Those timing boundaries differ, so they are **not a valid latency ranking**. No p95 or coordinator winner follows from one controlled fixture. The existing 4B baseline and optimized-engine comparison remain in the initial report.

Evidence: room-predeclared-rubric.json, final-proofs.json, followup-room-events.ndjson, codex-matched-comparison.json, adk-matched-comparison.json and ADK request/tool/event traces.

## 4. Forecast validity

**Operational checks PASS in the disposable wrapper; market-quality gates FAIL or remain unproven. The product forecaster is not repaired.**

Reuse: real TimesFM 2.5 checkpoint 1d952420fba87f3c6dee4f240de0f1a0fbc790e3, TimesFM_2p5_200M_torch in library 3.0.2, CPU-only, two threads, compilation disabled, context <=512/horizon <=128. Continuous quantiles, normalization and crossing correction enabled. Exact source/model pins remain in the initial report.

All **36/36** wrapper checks passed: empty/short/nonfinite/nonpositive/bool prices, naive/unordered/duplicate/future timestamps, incomplete bars, invalid horizons, unknown calendar, absent source/version, future cutoff, validation before cache lookup, input/cutoff/horizon/source/version/model cache identity, future/expired cache rejection, output shape/finite/order/median mapping and real inference failure without fabricated fallback. The returned point equals channel 5; quantiles are explicitly channels 1–9, levels 0.1–0.9. Channel 0 is not substituted for the point.

Load/compile 1.03 s; first real inference 0.169 s; evaluation mean inference about 0.111–0.113 s per origin; peak RSS 2,283 MiB. A single serial CPU service provided the native Codex and ADK tools. Cache hits are labelled and return earlier real model output; they are not counted as new inference.

Policy was saved before evaluation: seed 12743; 30 nonoverlapping 20-step origins per family, 128-point context; last-price and 20-observation drift baselines; MAE/RMSE/MASE, directional base rates, pinball loss, 80% coverage/width, endpoint h1/h5/h20 statistics and confidence intervals. Config/thresholds were frozen.

Historical input: [S&P 500 closing index observations from FRED](https://fred.stlouisfed.org/series/SP500), downloaded read-only through 2026-10-28; 2,512 nonmissing observations, SHA256 49faa5a4f87574084a5e525e44013bad74e831947c2cc98b8031e87508d0d6b9. The 30 evaluation cutoffs span 2024-06-06 to 2026-09-30; each forecast sees only prior observations. Missing observations were omitted as observed sessions, not filled into invented prices. Current-vintage revisions and checkpoint training overlap are uncontrolled; this is not a clean point-in-time or NSE/GIFT validation. Raw licensed observations stay outside Git; the report gives aggregate metrics.

| Dataset, 30 origins each | TimesFM MAE | Last-price MAE | Drift MAE | Nominal 80% coverage | Predeclared accuracy gate |
|---|---:|---:|---:|---:|---|
| Seeded random walk | 0.935 | 0.932 | 1.222 | 80.7% | FAIL vs last price |
| Seeded drift | 0.633 | 0.599 | 0.600 | 79.5% | FAIL |
| Seeded seasonal/shock | 0.373 | 1.751 | 1.887 | 90.0% | PASS accuracy only |
| Historical S&P 500, index-point errors | 127.827 | 127.782 | 126.800 | 64.5% | FAIL |

The predeclared endpoint Wilson-interval calibration screen included 80% for all groups, but n=30 is small and this does not establish calibration. Supplementary dependence diagnostics resampled three adjacent origins per block, 2,000 replicates, without new inference or changing the acceptance threshold:

- S&P 500 MAE difference versus last price: 95% interval -10.62 to +10.43 points; versus drift -28.43 to +27.57. No demonstrated accuracy advantage.
- S&P 500 overall 80% coverage: block interval **54.0–75.2%**, below nominal.
- Seasonal/shock coverage: block interval **86.8–93.2%**, above nominal; accuracy success alone does not validate its uncertainty bands.
- Per-horizon errors, direction accuracy versus always-up/down and drift, pinball loss and widths are retained in the evidence.

Six current-product defects were also reproduced using its unchanged class AST with private storage, a small Series equivalent, injected clock/storage functions and a real CPU model:

1. Changing every historical price reused the old cached forecast.
2. Empty input reused the fresh cached forecast.
3. NaN input reused the fresh cached forecast.
4. A future cache creation timestamp was accepted.
5. Empty uncached input raised an untyped IndexError.
6. A deliberately poisoned private-cache fixture with missing quantiles generated arbitrary 95/105 stop/target bounds around last price 100. This is a negative fixture, not model-generated evidence.

Product source hash and individual results are recorded; no product cache was opened or modified. The wrapper's passing cache tests do not validate the unchanged product cache or make its prototype serial cache production-ready.

**Still BLOCKED/NOT VALIDATED:** authenticated NSE/GIFT bars, exchange holidays/half-days and target timestamps, stale-source policy, gap/corporate-action/adjustment provenance, point-in-time universe/vintages, clean post-training holdouts, representative instruments/regimes, product initialization/cache concurrency and timeout recovery, scorer influence and any derived entry/stop/target, transaction costs or profitability. Saved broker-session 403 remains unchanged; no login, token refresh or orders were attempted. These require a separately authorized product/data validation phase.

Evidence: forecast-predeclared-policy.json, forecast-validity.json, forecast-supplementary-analysis.json, current-forecaster-behavior.json and forecast-counter.json.

## 5. Decision and handback

The browser blocker is resolved for the isolated fixture. Codex is a demonstrated experimental research-worker option through the scoped adapter and external coordinator; native namespace routing and a product integration remain unapproved. Both Codex and ADK passed the controlled room. Forecast numeric contracts can be enforced, but accuracy/calibration and current product defects prevent promotion.

No engine/model/coordinator winner, risk-policy change, forecast score influence, broker migration or product P0–P6 implementation is authorized by these findings.

~~~text
KEPLER SPIKE + FOLLOW-UP HANDBACK
Reports: SPIKE_FINDINGS.md and FOLLOW_UP_FINDINGS.md under docs/plans/kepler-research-revamp/
Branch / HEAD: feat-generic-broker / 5ebdd171cf3dc3862e1b7a1dd17427ad626471a3
Runtime comparison: llama.cpp completed; vLLM/SGLang did not yield a passing preferred-pair replacement
Initial default concurrent p95: Gemma 1.385s / Qwen 1.087s, n30 each; CPU embeddings remain
Initial limits: strict-GPU fast timeout; selected-record correctness 2/30 each; no promotion
Browser: real pinned skill + browser PASS, external/private redirect denial; no extra network permission needed
Codex: both models PASS through isolated adapter; real tools, IDs/events, cancellation, crash/recovery and global caps checked
Routing: external coordinator with separate pinned native threads; native heterogeneous spawn not demonstrated
Codex vs ADK: same controlled room and caps; both PASS, 10 model/6 tool calls; no winner from n1
TimesFM: 36/36 disposable contracts PASS; 120 rolling-origin forecasts; no historical baseline advantage
Historical 80% coverage: 64.5%, block 95% interval 54.0-75.2%; not calibrated
Current forecaster: 6 isolated defects reproduced; product remains unchanged and unqualified
Follow-up calls: 106 LLM / 127 forecast attempts; evidence retained outside repository
Remaining blockers: grounding, strict placement, optimized runtimes, native routing, point-in-time market/feed/product validity
Preservation: original local work retained; production identities unchanged; experiment processes/listeners gone
STOPPED BEFORE PRODUCT IMPLEMENTATION: yes
~~~
