# Initial local spike findings — 1 November 2026

**EXECUTED, with FAIL and BLOCKED gates. No production engine/model/coordinator is approved. Product P0–P6 implementation has not started.**

The user subsequently authorized isolated browser, Codex compatibility and forecast-validity follow-ups. These are now executed: [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md), with the completed [request queue](FOLLOW_UP_REQUESTS.md). The browser fixture and both Codex models work through the isolated adapter; forecast quality remains unqualified. These results do not change the initial measurements below.

## 1. Run identity and safety

- Run: 20261101T004535+0530, Asia/Kolkata. Measurements began 00:45 IST; reporting resumed after a usage pause at 05:08 IST. No inference or service changes continued during the pause.
- Branch: feat-generic-broker; tested HEAD: 5ebdd171cf3dc3862e1b7a1dd17427ad626471a3. Configuration-audit reference: 8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0. No report commit or push.
- Evidence root, abbreviated **R**: /home/devadethanr/.local/state/kepler-spikes/20261101T004535+0530 (mode 0700). Runners, locks, fixtures, requests, events, hashes and logs remain outside application state.
- Original five dirty runtime files were copied before work. Four remain byte-identical; agent_activity.json evolved while services stayed running. Its original and final snapshots are retained, without replacing newer state. See R/evidence/work-preservation.json, original-work/ and final-work/.
- **No graph deletion fixtures, pytest/conftest imports, production graph/DB connections, broker orders, broker migration, application dependency changes, risk/config edits, driver changes or production service restarts.** Graph tests used an in-memory fixture. Broker probes used GET only.
- Experimental HTTP listeners were loopback-only on 19081/19082/19083. The existing 8080 service was untouched. One GPU UUID per server, TP=1; no remote model Python or checkpoint conversion/calibration.
- Declared measurement budget: 90 minutes, initially 600 model-call attempts, amended before strict-placement tests to 750 with all pilots retained. Actual count: **376**, including failed connections. Download allocation 45 GiB. Fast deadline 10 s, slow 60 s, startup 300 s; these targets were not raised after failures.
- Resource floors: 1536 MiB available RAM, 1024 MiB observed free VRAM. Framework servers used owned transient scopes with 4 GiB MemoryHigh, 5 GiB MemoryMax and no scope swap. Stop/kill operations targeted only recorded spike PIDs/groups/scopes.
- Cleanup: no spike processes/listeners remain; all seven inspected production containers retain their original IDs/start times and remain running. No permanent services were installed. Evidence: R/evidence/cleanup-final.json.

PASS means an observed stated criterion passed; FAIL means an observed unmet criterion; BLOCKED means a prerequisite was missing; NOT_RUN means not attempted; UNKNOWN means unmeasured/unexposed. Model-list readiness alone is not successful inference.

## 2. Refreshed hardware

| GPU | UUID | Architecture | Total MiB | Initial used/free MiB | Display |
|---|---|---|---:|---|---|
| RTX 5070 Ti, slow | GPU-afdd0316-820f-339d-78c2-d173b72e5457 | SM120 | 16303 | 610 / 15263 | active |
| RTX 3060, fast | GPU-fe6b9da0-31a7-e026-0b40-8957cb0d5b4c | SM86 | 12288 | 2 / 11908 | inactive |

Native Ubuntu 24.04.4 LTS, kernel 7.0.0-31-generic, x86_64; Intel Core Ultra 7 270K Plus. RAM 15605 MiB, initially 7362 MiB available; swap 4095 MiB; initial free disk 118 GiB. Driver 610.43.02; nvcc 13.3/V13.3.73. Framework CUDA versions below were measured separately.

Evidence: R/evidence/inventory-before.json and cleanup-final.json. Production services/background transfers remained active. GPU peaks are 0.5-second samples, not guarantees against shorter transients.

## 3. Runtime/artifact pins and feasibility

### Runtime pins

- **llama.cpp:** build 9067, source 44dbe8c5218829be1603a08dee8847f4d0bca323, GNU13.3, CUDA architectures 120;86. Existing binary preserved; SHA256 in R/evidence/llama-binary.json.
- **vLLM 0.28.0:** existing isolated experimental venv reused read-only after fresh wheel downloads timed out. Python3.14.6, Torch2.13.0+cu130, CUDA13.0, Transformers5.16.1. Pip check PASS; exact freeze/package RECORD hashes in R/environments/vllm-reused/.
- **SGLang 0.5.23:** source tag resolves to 297e54fd105e974cdf401e5b4d20253a22c16f90. Fresh Python3.12.3 venv, Torch2.14.1+cu130, CUDA13.0, Transformers5.19.0. Pip check PASS for 207 packages. Python3.13 lacked an outlines-core wheel; the Python3.12 hash lock used prerelease-enabled resolution and includes transitive prereleases. This is an experimental lock, not a recommended production dependency set.
- Selected wheels were hash-verified using bounded range downloads, then installed offline. Both Torch builds list SM86/SM120. Installed help, source, locks and wheel hashes are retained. No system pip, CUDA source build or blanket upgrade.
- **vLLM GGUF plugin0.0.5 + gguf0.19.0:** separate overlay installed; import PASS. No serving request was run with that plugin in the initial spike: model compatibility remains NOT_RUN.

### Checkpoint pins

| Model/artifact | Immutable revision | Format/provenance |
|---|---|---|
| Existing Qwen3-4B-Instruct-2507 | unsloth/Qwen3-4B-Instruct-2507-GGUF@a06e946bb6b655725eafa393f4a9745d460374c9 | Local bytes match Q4_K_M at this revision; Apache-2.0 metadata. Original download time unknown. |
| Preferred Gemma4 E4B | google/gemma-4-E4B-it-qat-q4_0-gguf@4b4a2c1d584be7264f87aac328a1bc739ce81b6c | Official Google QAT Q4_0 GGUF, 5154941280 bytes |
| Preferred Qwen3.5-9B | unsloth/Qwen3.5-9B-GGUF@3885219b6810b007914f3a7950a8d1b469d598a5 | Community Q5_K_M GGUF, 6577841376 bytes |
| Optimized Gemma alternative | Vishva007/gemma-4-E4B-it-W4A16-AutoRound-AWQ@895008d877f63126def5e218889a474be03629e8 | INT4/group128 AWQ LM, native FP16; higher-precision embeddings/MM tensors; seven shards, 9.35 GiB. Community card license label differs from official artifact metadata; redistribution review remains needed. |
| Optimized Qwen alternative | cyankiwi/Qwen3.5-9B-AWQ-4bit@e4d2d39cede8c5d1716d824cd843e2889c648083 | Actual quant_method is compressed-tensors W4A16, BF16 config, three shards/9068588904 bytes; Apache-2.0 metadata. Not interchangeable with GGUF or generic AWQ. |

Verified full-file SHA256:
- Existing baseline: 3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597
- Gemma GGUF: 676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee
- Qwen GGUF: dc2a39aef291f91a9116ad214058da0d86eb648743a124bd8c333787c4b9c91c

All shard expected/actual hashes: R/logs/downloads.ndjson and pinned model metadata under R/evidence/. GGUF embedded templates are pinned by file hashes. Launch records identify actual checkpoint paths, UUIDs, parsers, context, slots and flags.

### Serving results

| Arm | Gate | Observation |
|---|---|---|
| Existing llama.cpp Qwen3-4B | PASS runtime | Final 30-request baseline; not the preferred pair |
| llama.cpp Gemma default | PASS runtime, placement limitation | 4K/1slot/thinking budget0; transformer layers on GPU, but 2730 MiB CPU_Mapped parameters and 2696 MiB CUDA parameters |
| llama.cpp Qwen default | PASS runtime, placement limitation | 8K/1slot/reasoning budget128; 666.88 MiB CPU_Mapped parameters, 5595.78 MiB CUDA parameters |
| llama.cpp strict full-GPU pair | PASS capacity, FAIL fast deadline | Explicit all-tensor override removed CPU parameter buffers; first fast long-register call exceeded10 s. This is a tested placement variant, not proof of an optimal layout. |
| vLLM Gemma AWQ/3060 | FAIL capacity | Native FP16 retry,4K/1slot/text-only/eager/Triton/fraction0.80: 11108 MiB used, **802 MiB free**, below1024 floor; stopped before readiness. Earlier BF16 pilot retained separately. |
| vLLM Qwen W4A16/5070 Ti | FAIL startup | 8K/1slot/text-only/eager/Triton. Weights loaded in7.54 s/7.56 GiB; no readiness within300 s, last stage hybrid/mamba page profiling. Root cause UNKNOWN; compilation/memory hypotheses are unproven. |
| SGLang Gemma AWQ/3060 | BLOCKED selected deployment | Pinned standalone language-model-only and disaggregated language-only allowlists exclude Gemma4. Full-MM weights plus conservative overhead/headroom exceed available capacity. No oversized launch, converted checkpoint or source patch. This does not show every Gemma4/SGLang configuration is unsupported. |
| SGLang Qwen W4A16/5070 Ti | FAIL real inference | Corrected documented language-only route reached identity in35.27 s; first structured request disconnected after50.729 s, then connections were refused. No successful generation/p95. |

Initial SGLang generic-flag rejections were configuration attempts, not architecture-wide findings. Optimized dual arms were BLOCKED by single-lane gates. Evidence: R/evidence/launch-*.json, capacity-*.json, arm-*.json, sglang-fast-text-only-blocker.json and runtime logs.

## 4. Performance, placement, context and cache

Final comparable fixture profile: 20 unique labelled records, 30 requests per completed profile; cold/stable/changed/role counts8/8/7/7; seed20261101. Questions select one independent record from a shared untrusted register and actual tool schema. Earlier three baseline pilot profiles remain in raw evidence but are excluded because cold-prefix/evidence-role controls were corrected before final v4. No targets were relaxed.

| Configuration | Profile | n / errors | E2E p95 s | Final-text TTFT p95 s | JSON valid | All fields/citation sets correct |
|---|---|---:|---:|---:|---:|---:|
| Existing baseline v4 | solo | 30/0 | 0.549 | 0.182 | 30/30 | 3/30 |
| Gemma default placement | solo | 30/0 | 1.387 | 0.481 | 30/30 | 2/30 |
| Qwen default placement | solo | 30/0 | 1.090 | 0.377 | 30/30 | 2/30 |
| Gemma default placement | both busy | 30/0 | 1.385 | 0.473 | 30/30 | 2/30 |
| Qwen default placement | both busy | 30/0 | 1.087 | 0.381 | 30/30 | 2/30 |
| Gemma strict full-GPU | solo | 1/1 | UNKNOWN | UNKNOWN | 0/1 | 0/1 |
| Qwen strict full-GPU | solo | 30/0 | 3.053 | 0.619 | 30/30 | 2/30 |
| Gemma strict full-GPU | concurrent attempt | 1/1 | UNKNOWN | UNKNOWN | 0/1 | 0/1 |
| Qwen strict full-GPU | mixed/resident after fast abort | 30/0 | 3.541* | 0.731* | 30/30 | 2/30 |
| SGLang Qwen | failed first request | 1/1 | UNKNOWN | UNKNOWN | 0/1 | 0/1 |

Strict Gemma solo/concurrent elapsed10.146/10.026 s: no p95 with n1. *Slow strict mixed-load measurements are not a full 30-request simultaneous-busy comparison once fast aborts.*

Default pair: 60 requests,3915 output tokens/37.092 s = **105.55 aggregate output tok/s**. Sampled busy peak-used/min-free MiB: 5070 Ti6895/8978,30603118/8792. These include CPU embeddings.

Strict full-GPU attempts: no CPU parameter buffers. Sampled peak-used/min-free MiB: 5070 Ti7477/8397,30605852/6058. Co-resident snapshot:7475/8399 and5850/6060, available RAM5181 MiB. Capacity passed for these buffers; fast latency did not.

Admission concurrency2/lane with one execution slot: fast requests timed out10.17/10.04 s; slow completed3.45/6.78 s. This tests queue admission, not two concurrent execution slots; n2/lane has no p95. Optional expanded context and lower-precision KV were NOT_RUN after initial gates failed.

Actual cached-token reports: cold0; stable after first request865–866 Gemma/966 Qwen. Median final-text TTFT cold→stable: Gemma0.466→0.120 s; Qwen0.363→0.099 s (n8 each, descriptive only). Role changes reduced reuse to4–7 Gemma/0 Qwen. Changed entity was correct7/7 each, but record grounding still failed. Eviction/recompute and server queue latency are UNKNOWN. No cache sharing between models was assumed.

Completed solo client output rates including prefill:57.79 tok/s Gemma,67.31 Qwen; not pure decode rates. All failures remain in counts. Different model/quantization/GPU/placement/eager settings prevent a pure engine-speed winner. Evidence: R/evidence/analysis.json, requests.ndjson, scored.ndjson, resource traces and metric/slot snapshots.

## 5. Quality and actual discussion

- Completed llama.cpp profiles had first-pass valid JSON throughout, with no repairs.
- Shared-register all-field correctness:3/30 existing baseline,2/30 each preferred lane. Models merged contradictions/citations from other independent records. Citation-order normalization does not change these counts; this is an evidence-scope failure, not a claim that all wrong citations were fabricated.
- Each preferred lane answered4/6 synthetic financial-reading cases correctly. These test arithmetic, conflicting EPS, future reports, unsupported price targets and master-versus-entitlement distinctions; not market predictive competence.
- Actual addressed analyst→skeptic→analyst revision→forecast-role conversation completed: four public messages, six model calls, three executed fixture tools, with g1/f1/t1. The skeptic questioned missing BETA inventory evidence; the analyst revised to uncertainty; the forecast role described synthetic uncalibrated output and abstained.
- Browser b1 was unavailable and honestly reported; complete E1 with b1 is BLOCKED. The degraded-room trace is real, but a predeclared smoke sequence is not native child routing or a full adaptive product coordinator/UI.
- Human/expert financial review, real-market quality and a safely isolated ADK comparison were NOT_RUN/BLOCKED. Do not promote based on schema or speed alone.

Evidence: R/evidence/financial-*.json, room-events.ndjson and room-summary.json.

## 6. Codex, Responses, tools and budgets

Installed Codex0.164.0; binary SHA256 in R/evidence/codex-native.json. Installed experimental schema generated under R/codex-schema/. Disposable home mounts hid real credentials/product files; successful thread results confirmed readOnly/networkAccess=false and provider fallback disabled. The successful thread/start enum was read-only; the initial wrong-enum attempt is retained separately.

| Gate | Initial preferred llama.cpp lanes | Observation |
|---|---|---|
| R1 nonstream Responses | PASS | correct identity/object/terminal output |
| R2 strict streaming | FAIL | ordered core events/stable IDs, but sequence_number absent |
| R3 function round trip | positive subtest PASS, negative FAIL | real graph fixture cited; unmatched call_id accepted instead of rejected |
| R4 disconnect | PASS observed cessation | strict fast running→idle ~0.561 s, strict slow ~0.141 s |
| C1 App Server inference | FAIL | both initialized/created threads; actual HTTP400: tool type must be function |
| C2 complete tools/skills | BLOCKED | C1 and browser prerequisite failures |
| C3 crash/interrupt/recovery | BLOCKED | no successful App Server tool lifecycle |
| C4 native global accounting | BLOCKED | standalone ledger only |
| C5 heterogeneous children/mediated Codex threads | BLOCKED | C1 missing; chat room is not a substitute |

SGLang's subsequent App Server transport failure is blocked by the dead model server, not proof of a particular tool-type rejection. vLLM-dependent Codex tests were NOT_RUN/BLOCKED because no server passed readiness.

Standalone ledger subtest PASS:12 concurrent model reservations admitted2;12 tool reservations admitted1;8192 conservative tokens reserved; work after cancellation denied. This does not prove native child/retry usage or deadline accounting. Actual endpoint requests, JSON-RPC IDs/events, failure terminals and config hashes are in R/evidence/codex-*. No interrupted/failed turn was called successful.

Native Codex is ineligible in tested configs. The plan's ADK contingency remains a design fallback, not implemented code. The user later authorized isolated protocol fixes; subsequent adapter passes must not erase these native failures.

## 7. Tools, TimesFM and read-only feeds

| Capability | Initial result | Scope |
|---|---|---|
| Graph lookup/neighbors/evidence/limits | PASS | fake ACME→BETA; empty/unavailable/unsupported_as_of distinct; no real graph |
| Artifact list/read/search and escape denial | PASS | approved fixture root; traversal/symlink/.env refusals |
| Tool contract cases | 28 PASS /1 BLOCKED | blocked case is real browser execution |
| Pinned browser discovery/core retrieval | PASS subtest | stub5868f7c05020e047c00e68e4abf9253cce864f41; CLI0.41.0/matching core; not autonomous agent execution |
| Browser execution | BLOCKED | PermissionError configuring private-namespace loopback; no host permission/security changes |
| Scrapling0.5 | PASS n2 | real static title/date/body extraction across changed markup |
| Fake ForecastTool | PASS fixture | success/invalid/insufficient/unavailable; not real forecast accuracy |
| TimesFM CPU load/shapes | PASS | real checkpoint below |
| Raw quantile ordering | FAIL | crossings below |
| GIFT authenticated data | BLOCKED | saved session403 |
| RSS | parsing partial PASS; freshness BLOCKED | unresolved timestamps and unavailable source |

Real TimesFM checkpoint: google/timesfm-2.5-200m-pytorch@1d952420fba87f3c6dee4f240de0f1a0fbc790e3; real2.5 class in library3.0.2, Torch2.13.0+cu130, CPU-only, torch_compile=false, two threads. Source/API reviewed at e51928e27119cb17bebc005be2696b75e0a9e688. Input512 synthetic completed weekday bars, horizon20/max128; no product cache or GPU.

Raw arm: load0.923 s; cold/warm0.165/0.113 s; peak RSS2290.6 MiB. Shapes(1,20)/(1,20,10), finite. Raw adjacent quantile crossings37 (unchanged input),1(changed input). Point matched channel5, not channel0; do not label it a channel0 mean. Separate fix_quantile_crossing=true arm:0 crossings in all three profiles; load1.103 s,cold/warm0.163/0.115 s,peak2294.4 MiB. These are operational/numeric smoke results, not accuracy/calibration/trading validity. Changed-bar hashes differ; production cutoff/cache was not repaired or validated. Evidence: R/evidence/real-components*.json and model/library source/hash records.

GIFT master: NSEIX, symbol **GIFT NIFTY** (space), token291849, INDICES. Saved session failed GET /user/profile with403. Quote/history/socket were blocked; no refresh/login/orders or token disclosure. A master row is not entitlement.

NSE RSS HTTP200/XML:1 item, raw date01-Nov-2026 00:12:59 without explicit timezone; generic parser left it unresolved. SEBI HTTP200/XML:30 items, sampled strings such as30 Oct,2026 +0530 also unresolved. Freshness is not validated despite valid RSS. RBI failed with URLError. Evidence: rss-observations.json and kite-observations.json; HTTP200 was not treated as a usable current feed.

## 8. Decision, reproducibility and stop

**No promotion.** Only llama.cpp completed preferred-model measurements; default placement is fast but retains CPU embeddings. Strict full-GPU fast latency, evidence grounding and native Codex gates failed. Optimized configurations did not provide a passing replacement. No engine winner is declared.

Review needed: CPU embeddings versus full-GPU latency, compatible Gemma optimized/text-only artifact, vLLM hybrid readiness failure, grounded evaluation, full Codex adapter gates, forecast validity/calibration and authenticated feeds. Unsafe graph isolation remains a product prerequisite and was not fixed in this spike.

R/scripts/ contains disposable benchmark, fixture, component, feed and Codex runners. Exact source SHA256s: R/evidence/runner-sha256.json; runtime locks and checkpoint hashes are retained. Expired initial wall-budget guards intentionally prevent reruns unchanged; new work needs a newly declared isolated run. No optional model family, production graph integration, real-market calibration or product P0–P6 was implemented.

Cleanup and preservation checks completed. User-authorized follow-ups are separately documented and completed; product implementation remains stopped.

## 9. Copyable initial handback

~~~text
KEPLER INITIAL SPIKE HANDBACK
Report path: docs/plans/kepler-research-revamp/SPIKE_FINDINGS.md
Branch / tested commit / report commit: feat-generic-broker /5ebdd171cf3dc3862e1b7a1dd17427ad626471a3 /none
Hardware refreshed: Ubuntu24.04.4; RAM15.2GiB;5070Ti16GiB SM120 +3060 12GiB SM86;driver610.43.02
Engines/checkpoints: llama.cpp9067/44dbe8c;vLLM0.28.0;SGLang0.5.23; immutable GGUF/AWQ/W4A16 pins in report
Dual peak-used/min-free MiB: default5070Ti6895/8978,30603118/8792; strict7477/8397,5852/6058
Fast/slow p95/count: default concurrent1.385/1.087s,n30/lane;strict fast timeout n1(no p95),strict slow solo3.053s,n30
Cache/context/concurrency: real prefix hits; changed entity7/7; role prefixes reduce reuse; strict dual profile incomplete after fast timeout
Quality: completed JSON valid; selected-record all-fields2/30 each; financial microcases4/6; fixture tools28PASS/1BLOCKED
Codex: native R2/R3/C1FAIL;C2-C5BLOCKED; direct cancellation and standalone ledger subtestsPASS
TimesFM/graph/tools: real CPU2.5 shapesPASS;raw crossings37,fixed0;point=channel5; graph fixture only; no accuracy/calibration claim
GIFT/news: master GIFT NIFTY291849;session403/dataBLOCKED;NSE/SEBI parse but dates unresolved;RBI unavailable
PASS/FAIL/BLOCKED/NOT_RUN: per-gate details in report; no winner or promotion
Recommended engine/model/coordinator: retain baseline;product selection undecided;ADK contingency until Codex gates pass
Decisions: placement/latency,grounding,optimized runtime/format,Codex dialect,browser permissions,forecast validity
Cleanup: spike processes/listeners gone;production container IDs/start times unchanged;local-work snapshots retained
STOPPED BEFORE PRODUCT IMPLEMENTATION: yes
~~~

## 10. Completed follow-ups and current decision

Full results and the current copyable handback are in [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md).

- Browser: real pinned skill loading and browser execution now PASS inside a private namespace, including external-domain/private-redirect denials; no additional network permission or host security changes.
- Codex: both preferred models now PASS native App Server turns through an isolated Responses/Chat adapter and flat approved tools. Actual graph/file/search/browser/CPU TimesFM callbacks, stable IDs/events, interruptions, crash/recovery, replay boundaries, deadlines and atomic global caps were exercised. External coordinated model routing passed; native heterogeneous child spawning remains unproven. Original unmodified endpoint failures remain above.
- A matched controlled room passed on both Codex and isolated ADK 1.33.0: identical global caps, 10 model calls and 6 tools each. Scripted wording, one fixture and unequal timing boundaries prevent a reasoning-quality or latency winner claim.
- Forecast testing: 36/36 disposable contract checks passed; 120 rolling-origin forecasts did not show a historical baseline advantage. Nominal 80% S&P 500 interval coverage was 64.5% (supplementary block interval 54.0–75.2%). Six current forecaster defects were reproduced with its class AST and private storage; product code/cache remained untouched.
- Follow-up evidence: /home/devadethanr/.local/state/kepler-spikes/20261101T051358+0530-followups. Recorded 106 LLM requests and 127 forecast attempts. Experimental processes/listeners are gone; original production identities and local work are preserved.

**No promotion or product implementation.** Grounding, strict-GPU fast latency,
optimized-engine readiness, point-in-time market/feed validity and current product
forecast defects remain unresolved. The user-requested isolated spike and its
three follow-ups are complete.
