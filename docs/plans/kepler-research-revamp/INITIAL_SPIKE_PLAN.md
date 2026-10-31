# Mandatory initial spike — local execution and findings

Revision 1, 1 November 2026. Run this spike BEFORE the product implementation phases. This is a feasibility, measurement and decision task, not permission to enable autonomous trading or to declare the revamp implemented.

## Outcome and stop rule

Local Codex must:
1. Inspect the supplied hardware and safe local environment.
2. Provision isolated, pinned experimental serving environments if needed.
3. Test model/runtime, cache/context, tools and Codex compatibility using the stages below.
4. Populate [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md) with measured results, failures and evidence.
5. Return the handback summary to the user and **STOP**. The user will bring the findings to the planning conversation before product implementation starts.

Minimal disposable benchmark runners, fixtures and model start/stop scripts are allowed within the spike. Do not change product agent logic, database schemas, risk controls, live policies, application dependency declarations or production services. Do not turn a protocol failure into an open-ended compatibility project.

## Confirmed starting hardware

Source: user-pasted local nvcc/nvidia-smi output received 1 November 2026, not a measurement by this cloud session.

| Item | Supplied observation |
|---|---|
| GPU 0 | RTX 5070 Ti, 16,303 MiB total, 568 MiB in use, display active |
| GPU 1 | RTX 3060, 12,288 MiB total, 2 MiB in use, display inactive |
| Driver | 610.43.02 |
| CUDA UMD reported by nvidia-smi | 13.3 |
| nvcc toolkit | 13.3, V13.3.73 |
| Desktop indication | GNOME/Xorg processes; exact distro/kernel/native versus WSL still to record |

Preferred model assignment remains Gemma 4 E4B on the 3060 and Qwen3.5-9B on the 5070 Ti. Record actual GPU UUIDs; numeric indices are not stable deployment identifiers. The display GPU needs additional headroom as the desktop/browser load varies.

Host nvcc does not determine the CUDA/PyTorch runtime bundled in a serving wheel or image. Do not downgrade the working driver, replace system CUDA or force a source build against CUDA 13.3 merely because nvcc reports it.

## Decision questions

- Can both preferred models serve valid structured outputs and tools while resident together?
- Which engine gives the best measured latency, cache/context behavior and reliability for this workload?
- Does the actual endpoint support Codex's Responses/tool/streaming requirements?
- Can an agent browse, read/search approved artifacts, traverse graph fixtures and consume forecasts with grounded citations?
- Can collaborative messages, cancellation, child routing and global accounting be captured correctly?
- Which prerequisites are blocked, and what product changes are justified by evidence?

There is no assumed winner. vLLM is the FIRST candidate; SGLang is the required comparison where a compatible configuration exists; the existing llama.cpp/GGUF setup is the retained baseline. A missing or unsupported combination is reported, not hidden.

## SP0 — safety, inventory and reproducibility

Read [PRE_IMPLEMENTATION_AUDIT.md](PRE_IMPLEMENTATION_AUDIT.md). Broad/destructive graph tests are unsafe until the documented target guard is fixed. This spike uses fake graph/tool fixtures or an independently proven disposable target; it never runs the deletion fixture against a configured application graph.

Record:
- Git branch, HEAD, uncommitted changes, and baseline code commit.
- OS/kernel/native Linux or WSL, CPU/RAM/free disk.
- GPU UUID/name/total/free VRAM, display processes, driver, and current model processes/ports.
- Existing llama.cpp binary/build, model file hashes, Python/PyTorch versions and bundled CUDA.
- Available artifact/registry access by status only; no process-environment or credential dumps.

Read-only inventory can use nvidia-smi query fields, nvcc version and OS metadata. Capture the state again while both models run. Preserve current services and operator data; never use broad pkill, docker prune, git reset/clean, or a blanket package upgrade.

Use a fresh spike result directory. Raw logs and large outputs stay outside production state and should be ignored by Git. Commit/report only sanitized summaries, configs and reproducible runner code if appropriate. Keep secrets, private evidence and model weights out of Git.

**Gate:** the test cannot write to or delete production data and cannot place broker orders. If this cannot be shown, mark the affected stage BLOCKED. Safe independent GPU work may continue without connecting to an unsafe graph.

## SP1 — engine and artifact feasibility, before downloading large files

Build a compatibility table for each engine/model combination:

| Required field | Evidence to record |
|---|---|
| Runtime | Exact release/commit, package hashes/lock, Python/PyTorch/bundled CUDA |
| Hardware/backend | GPU UUID/SM architecture, actual attention/quantization kernel selected |
| Model | Source, immutable revision, original model identity and licence |
| Format | Actual safetensors/AWQ/GPTQ/bitsandbytes/GGUF etc.; not just “4-bit” |
| Template | Tokenizer, chat/reasoning/tool parser and exact configuration |
| Capacity | Weight estimate plus cache/buffer/display headroom at bounded context |
| Interface | Chat, Responses, streaming, tool and schema support in that pinned build |

Important constraints:
- Existing Gemma QAT Q4_0 and Qwen Q5_K_M pins are GGUF artifacts. They are not AWQ/GPTQ checkpoints.
- vLLM's current GGUF path is experimental and may require a separate plugin. Treat it as a feasibility arm, not the assumed optimized path.
- SGLang's Gemma QAT-unquantized example is BF16-sized, not the packed Google GGUF.
- Full BF16 weights for these models do not automatically fit the assigned GPUs; do not knowingly launch an oversized configuration to obtain an OOM.
- Architecture listed in a moving main branch does not establish support in a chosen stable release or for a particular quantization.
- RTX 5070 Ti consumer Blackwell is SM120, not a B200 SM100. A datacenter-only kernel claim is not compatibility evidence.
- Native FP8/NVFP4 assumptions do not transfer to the Ampere 3060.
- Model-specific sliding/global/hybrid state can constrain cache behavior.

Inspect a trustworthy, compatible optimized-format checkpoint before provision. Record changed quantization/tokenizer/template and upstream provenance. A community checkpoint's presence is not approval of its code or quality. Do not execute unaudited remote model code or silently convert/calibrate a checkpoint.

If the preferred artifact is unsupported, mark that arm BLOCKED/UNSUPPORTED with source evidence. Try a separately reviewed compatible checkpoint only with the difference disclosed. Do not replace Gemma/Qwen with a different model without flagging the substitution.

## SP2 — reproducible launch: native scripts are a first-class option

Docker is optional. On this PC, isolated virtual environments plus start/stop scripts are an accepted default.

- Separate environment per engine/version; no system pip and no changes to application requirements/lockfiles.
- Preserve proxy and TLS verification for downloads; verify model/build hashes.
- Bind each model process to one GPU UUID, tensor parallelism 1, no CPU offload initially.
- Use loopback-only experimental endpoints. Suggested per-arm ports: 19081 fast, 19082 slow; run arms sequentially, leaving the existing 8080 service untouched.
- Scripts must record exact executable, version, model, flags, UUID, PID/start time and log path; readiness includes a real structured request and model identity.
- Stop scripts stop only their own verified process/group; handle Ctrl-C, timeout, cancellation and failed startup.
- Detect occupied ports instead of killing an existing service.
- Restore pre-spike service state afterward. Do not enable permanent systemd services yet.
- If Docker is used, record image digest, driver visibility, inherited proxy/CA trust, UID/mounts, local binding and limits. Do not make Docker success a prerequisite for model evaluation.

Initial capacity targets:
- Engine memory-fraction target about 0.75 per GPU, adjusted only after measuring actual free/peak memory. Engine flags have different semantics and are not strict VRAM caps.
- Preserve at least 1 GiB observed free headroom plus enough allowance for display variability; reject unstable OOM/restart behavior.
- Fast: 4K TOTAL context, max 128–256 generated tokens, thinking off, one request slot.
- Slow: 8K TOTAL context, bounded reasoning plus final JSON; small probes at 256–512 generated tokens, then one realistic research profile with its full documented budget.
- Input, tool schemas, history, reasoning and output all count toward context/output limits.
- Use supported per-engine flag names from the pinned --help/docs; do not copy a command for another version blindly.

Record startup/load time, peak VRAM and actual model/parser identity. Failure to fit safely is a failed capacity gate, not permission to silently enable offload or pool the GPUs.

## SP3 — speed, context, concurrency and cache matrix

Test each passing arm:
A. Each model independently, concurrency 1.
B. Both models resident and busy, one request each.
C. Concurrent requests 2 per lane, only if capacity remains safe.
D. Optional context increase fast 4K->8K and slow 8K->16K after the initial gates pass.

Use a seeded, versioned corpus with the same task/response requirements and known expected answers across engines. Compare identical checkpoint/dtype where possible. If quantizations or tokenizers differ, report the comparison as a combined model/engine configuration result, not a pure engine speed measurement.

For each lane/profile/concurrency, include:
- Cold/no reusable prefix.
- Repeated stable system/tool/evidence prefix with new questions.
- Changed evidence inside the prefix, requiring a changed answer.
- Distinct agent-role prefixes representative of the room, not only an artificial identical mega-prompt.

Target at least 30 measured requests per reported p95 comparison, with category counts. Report small-sample uncertainty and all timeouts/errors. Bound execution to a declared total call/time budget; if exhausted, mark incomplete rather than dropping slow failures.

Collect:
- Client queue/admission and end-to-end p50/p95.
- Time to first token, prefill if exposed, inter-token/decode and output tokens/sec.
- Aggregate throughput under concurrent load.
- Actual input/output/reasoning tokens if available.
- Allocated/peak/free VRAM, model/cache configuration, context and slot count.
- Prefix reused/hit tokens or engine metrics, eviction/recomputation when exposed.
- Errors, timeouts, cancellations, malformed output and resource cleanup.

Paged KV allocation is not itself a cache hit. Prefix reuse saves prefill, not decoding. Caches are not shared between Gemma and Qwen or transparently across GPUs. Hybrid/sliding-state models may have special boundaries. Mark unexposed metrics UNKNOWN; do not infer them from a smooth latency chart.

Start KV dtype at a supported default. Test lower-precision KV only as a separately labelled quality/capacity arm. Record any grammar, tool, output or long-context regression.

## SP4 — task quality, structured output and tool use

Use at least 20 labelled tasks per model lane, independent of vendor benchmarks:
- Extract entity, date, source and event type from a provided excerpt.
- Distinguish missing/old/future-dated evidence.
- Identify conflicting facts and abstain when needed.
- Return fixed JSON enums/schema with no invented citation.
- Follow tool schemas, preserve IDs and cite actual outputs.
- Reject instructions embedded inside a retrieved page.
- Produce a short thesis and substantive challenge/revision using supplied evidence.

Separate protocol fixtures from actual financial interpretation tasks. Synthetic ACME fixtures validate wiring, not market competence. Keep development examples separate from scored cases.

Record first-pass schema validity, repaired/failed outputs, field-level correctness, citation validity, abstention and unsupported claims. A faster quantization that breaks tool or evidence quality does not win. Human review and deterministic checks are independent of model self-rating.

Target fast short-task p95 <=5 seconds; hard call timeout 10 seconds. Slow call deadline 60 seconds. Report measured failure if targets are unmet; do not change them retrospectively to claim a pass. These targets select suitability, not live trading latency authority.

## SP5 — Codex App Server conformance

Run [CODEX_CONFORMANCE_SPIKE.md](CODEX_CONFORMANCE_SPIKE.md) on each technically viable endpoint.

Required:
- Actual /v1/responses compatibility, including stream event order, call IDs and tool output round trip.
- JSON/schema, reasoning, multiple tools, cancellation, errors and context behavior.
- App Server initialization, thread/turn lifecycle and actual endpoint/model identity.
- Native child messages/routing to both model identities, or a documented externally mediated thread design under one coordinator.
- Global parent call/token/time/tool budget and cancellation account for children/retries.
- Complete public event capture, provenance and sandbox boundaries.

A chat-completions success, HTTP 200 or route existence is not a pass. Do not build a broad protocol translator just to avoid a finding.

Current rules:
- All mandatory gates PASS -> Codex is an eligible preferred room adapter.
- Observed mandatory FAIL -> use the documented dynamic ADK contingency for product design.
- BLOCKED/NOT_RUN -> selection remains UNDECIDED; no compatibility claim or feature implementation.

Do not silently call hosted inference. Approval in this spike does not authorize a live trade.

## SP6 — tools, skills and TimesFM probes

Use disposable fixtures first:
- Graph entity lookup/neighbors/evidence, empty vs unavailable, unsupported historical as_of, strict row/hop limits. No production graph socket or deletion fixture.
- Approved artifact list/read/search, path/symlink escape denial.
- Official pinned agent-browser skill discovery and matching executable function, then a local read-only page fixture; stop on permission/access failures.
- Scrapling title/date/body extraction on known static fixtures and changed markup.
- Typed forecast tool success/invalid/insufficient/unavailable states.

Distinguish fixture integration from the real component:
- A fake forecast response does not validate TimesFM.
- If a safely pinned isolated TimesFM2.5 CPU setup is available, separately run synthetic/timestamped completed-bar inference, assert shape/channel mapping/cutoff/cache-key separation, and measure cold/warm CPU time/RAM. This is an operational smoke test, not profitability or calibration evidence.
- Do not use application caches or silently allocate either LLM GPU.
- Any actual graph probe needs an independently proven disposable target; otherwise mark live graph integration BLOCKED and keep fixtures only.

A successful agent must select/load the skill and use the actual allowed tool bridge. A prompt listing tool names is not execution evidence.

## SP7 — read-only market/news and discussion smoke checks

Only if existing local access is usable:
- Resolve the current Kite GIFT instrument master row; make read-only quote/history/socket probes and record timestamps, declared delay and actual availability. Never place an order.
- If no valid existing session is present, record BLOCKED; do not ask for token values in chat or claim the feed works from the master alone.
- Parse a small current set of primary RSS feeds; detect HTTP200 HTML, unknown dates and actual entry timestamps.
- Run a tiny collaborative room on fixtures: two participants, a question/challenge, a source lookup, a changed view and a conclusion or abstention.
- Capture public messages/tool events/correlation/usage as a replayable artifact. An NDJSON transcript suffices; do not implement the full Gather-like UI in this spike.

A displayed discussion must come from actual messages, not scripted animation. Distinguish real model outputs, synthetic fixtures and provider observations.

## SP8 — findings, selection and return to user

Populate [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md), including:
- Hardware refreshed locally and every runtime/checkpoint/template/flag pin.
- Per-engine/model PASS/FAIL/BLOCKED/NOT_RUN, not just successful examples.
- Fairness limits and variant differences.
- Single-model and concurrent metrics; cache/context observations.
- Codex protocol/collaboration/budget results.
- Tool/TimesFM/feed observations clearly separated from simulations.
- Reproducible sanitized command/config/log paths, cleanup evidence and exact limitations.
- Proposed engine/model/coordinator decision with evidence and unresolved questions.

Selection priority:
1. Safety, capacity and correct tool/evidence behavior.
2. Complete required API/cancellation/accounting support.
3. Concurrent p95/queue/failure behavior on representative tasks.
4. Context/cache benefit and operational simplicity.

vLLM is a starting candidate, not an assumed winner. SGLang's prefix mechanisms may help a conversation workload; measurement must show it. If one engine passes all gates and the other has a measured failure, recommend the passing configuration. If the other is merely untested/blocked, say 'best observed', not 'universally fastest'. A mixed per-model engine pair is allowed only if measured benefits justify its complexity and both satisfy the common contracts.

If neither optimized engine serves the preferred pair correctly, retain the known llama.cpp baseline for comparison and report the choice to the user. Do not change models or write an open-ended compatibility layer silently.

After writing findings:
- Tell the user which tests actually ran, engine/model result, blockers and report path.
- Include the copyable handback block from the findings page.
- Show changed files and any commit if made; never hide spike code/config changes.
- **STOP before product P0–P6 implementation and wait for the user to bring results back here.**

## References

- vLLM architectures: https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md
- vLLM GGUF caveats: https://github.com/vllm-project/vllm/blob/main/docs/features/quantization/gguf.md
- vLLM prefix caching: https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md
- vLLM CUDA installation: https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.cuda.inc.md
- vLLM tool parsing: https://github.com/vllm-project/vllm/blob/main/docs/features/tool_calling.md
- SGLang Gemma4 cookbook: https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/Google/Gemma4.mdx
- SGLang installation: https://github.com/sgl-project/sglang/blob/main/docs/docs/get-started/install.mdx
- SGLang quantization/backends: https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/quantization.mdx
- Codex App Server: https://developers.openai.com/codex/app-server/

These references are source/documentation observations, not local compatibility tests. Freeze actual versions and recheck their documentation at execution time.
