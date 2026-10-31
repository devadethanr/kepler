# Initial spike findings — fill locally, then return for review

**Execution status: NOT_RUN.** This page was created as a handoff template on 1 November 2026. No GPU, model, engine, Codex, TimesFM or authenticated feed benchmark was run by the cloud documentation task.

Read [INITIAL_SPIKE_PLAN.md](INITIAL_SPIKE_PLAN.md) and [CODEX_CONFORMANCE_SPIKE.md](CODEX_CONFORMANCE_SPIKE.md). Replace template fields with observed facts and artifact links. Do not turn proposed settings or user-reported hardware into measured results.

## 1. Run identity and safety

- Run ID / date / timezone: NOT_RUN
- Operator / local host label (non-sensitive): UNKNOWN
- Repository branch / HEAD / dirty files: UNKNOWN
- Spike runner/config/evaluator revision: UNKNOWN
- Safety boundary / disposable workspace / no production graph: NOT_VERIFIED
- Cleanup and restoration evidence: NOT_RUN
- Declared call/time/download budgets: NOT_SET
- Gate decision: **UNDECIDED — return findings before product implementation**

Status meanings:
- PASS: attempted and all stated criteria have evidence.
- FAIL: attempted and an observable criterion was unmet.
- BLOCKED: a named prerequisite prevented a meaningful attempt.
- NOT_RUN: not attempted.
- UNKNOWN: a metric/fact was not measured or exposed.

## 2. Hardware

The following is USER_REPORTED, not independently refreshed by the spike:

| GPU snapshot index | Model | Total MiB | Used MiB | Display |
|---|---|---:|---:|---|
| 0 | RTX 5070 Ti | 16,303 | 568 | Active |
| 1 | RTX 3060 | 12,288 | 2 | Inactive |

User-reported driver:610.43.02. CUDA UMD:13.3. nvcc toolkit:13.3/V13.3.73.

Fill actual local observations:
- GPU UUIDs and current total/free memory:
- OS/distro/kernel/native versus WSL:
- CPU / RAM / free disk:
- Driver / toolkit / each framework's bundled CUDA/PyTorch:
- Current inference processes and desktop GPU load:
- Evidence file and observation time:

## 3. Runtime and artifact feasibility

| Engine/version/commit | Model and immutable checkpoint | Format/dtype/template/parser | GPU UUID | Context/slots/memory settings | Status | Exact blocker/evidence |
|---|---|---|---|---|---|---|
| Existing llama.cpp baseline | Gemma E4B or actual existing baseline | Record actual GGUF; do not assume | UNKNOWN | UNKNOWN | NOT_RUN | |
| Existing llama.cpp baseline | Qwen3.5-9B | Record actual GGUF | UNKNOWN | UNKNOWN | NOT_RUN | |
| vLLM | Gemma4E4B | Compatible optimized format unresolved | UNKNOWN | 4K/1 proposed, not tested | NOT_RUN | |
| vLLM | Qwen3.5-9B | Compatible optimized format unresolved | UNKNOWN | 8K/1 proposed, not tested | NOT_RUN | |
| SGLang | Gemma4E4B | Compatible optimized format unresolved | UNKNOWN | 4K/1 proposed, not tested | NOT_RUN | |
| SGLang | Qwen3.5-9B | Compatible optimized format unresolved | UNKNOWN | 8K/1 proposed, not tested | NOT_RUN | |

For each arm link sanitized launch script/config, environment lock, checksum, readiness request/model identity, server log and stop/cleanup evidence. Explain any checkpoint/quantization change; GGUF versus AWQ/GPTQ/BF16 is not an identical comparison.

## 4. Performance, context and cache results

One row per runtime/model/load/cache/context combination. Keep failures and timeouts in counts.

| Arm | Solo/both loaded | Context and slots | Prefix state | Requests/failed/timed out | Queue p50/p95 ms | TTFT p50/p95 ms | End-to-end p50/p95 ms | Output tok/s | Input/output/reasoning tokens | Cache reuse/eviction | Peak/free VRAM MiB | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NOT_RUN | | | cold/warm/changed | | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | |

- Warm shared-prefix behavior:
- Changed-prefix correctness and stale-answer checks:
- Different agent-role prefix behavior:
- Context overflow / truncation / generation budget behavior:
- Concurrency2 and cancellation resource recovery:
- Sample-size/fairness limitations:
- Exact engine metric names and which were unavailable:

Do not substitute vendor TPS, theoretical memory, cache allocation or a route's HTTP200 for these measurements.

## 5. Task quality and model behavior

| Model/runtime | Corpus revision/count | First-pass JSON | Repaired/invalid | Correct fields | Valid citations | Abstention/unsupported claims | Tool semantics | Status/evidence |
|---|---|---:|---:|---:|---:|---|---|---|
| NOT_RUN | | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | | | |

- Fast thinking-off and model-specific template confirmed:
- Slow reasoning/final-answer budget behavior:
- Missing/stale/conflicting evidence and injection outcomes:
- Human review and evaluator details:
- Existing baseline comparison:
- Any quality loss from a smaller/changed quantization:

## 6. Codex and collaboration conformance

Complete tests in CODEX_CONFORMANCE_SPIKE.md per model/engine.

| Test | Model/runtime | PASS/FAIL/BLOCKED/NOT_RUN | Expected versus observed | Correlation/event/log evidence |
|---|---|---|---|---|
| R1 nonstreaming Responses | | NOT_RUN | | |
| R2 streaming Responses | | NOT_RUN | | |
| R3 tool round trip / multi-turn | | NOT_RUN | | |
| R4 cancellation / disconnect | | NOT_RUN | | |
| C1 App Server thread/turn | | NOT_RUN | | |
| C2 permitted tools and denial cases | | NOT_RUN | | |
| C3 crash / interrupt / recovery | | NOT_RUN | | |
| C4 global parent+child budget | | NOT_RUN | | |
| C5 actual heterogeneous child routing | | NOT_RUN | | |
| E1 real challenge / evidence / revision | | NOT_RUN | | |

Record:
- Codex version/commit, generated protocol schema and config hash:
- Actual provider/model routing from independent request logs:
- Native child limitations or externally mediated alternative:
- Missing usage/event/cancellation information:
- ADK contingency comparison, or why it was not tested:
- Coordinator recommendation and all mandatory gates:

## 7. Tools, forecast and feeds

| Capability | Fixture versus real component | Status | Evidence and limitation |
|---|---|---|---|
| Graph lookup/traversal/evidence | Fixture only until safe disposable target proven | NOT_RUN | |
| Research file/read/search and escape denial | Disposable artifact root | NOT_RUN | |
| Agent-browser skill loading and actual execution | Pinned skill + matching tool bridge | NOT_RUN | |
| Scrapling extraction quality | Static reviewed fixture | NOT_RUN | |
| ForecastTool protocol | Fake response, not model accuracy | NOT_RUN | |
| TimesFM2.5 CPU smoke/cache/cutoff | Real pinned model, only if isolated setup available | NOT_RUN | |
| GIFT quote/history/socket | Read-only existing entitlement, no order | NOT_RUN | |
| RSS semantic parse/freshness | Small permitted source set | NOT_RUN | |
| Actual room messages and replay artifact | Model/tool events, no simulated discussion | NOT_RUN | |

TimesFM model/library/device, cold/warm CPU time/RAM, shape/quantiles/cutoff/cache observations:
Actual graph isolation status:
GIFT master identity versus authenticated data entitlement, source timestamps/delay:
Feed zero-entry versus HTML/error behavior:
Public message/event artifacts and reconnect/replay findings:

## 8. Findings and proposed decision

- Best observed engine per model:
- Is one common engine preferable, or is a mixed pair justified?
- Preferred model pair confirmed / changed / still undecided:
- Serving mode: native scripts / Docker / undecided, with reason:
- KV/context benefit actually measured:
- Codex eligible / observed fail / blocked / undecided:
- Hard blockers before implementation:
- Remaining risks and unrun tests:
- Smallest next change justified by findings:
- Rollback and cleanup status:

No feature implementation should start automatically. Bring these findings back to the user for planning review.

## 9. Copyable handback for this conversation

Local Codex: fill and return the following block in your final message, plus this report path.

~~~text
KEPLER INITIAL SPIKE HANDBACK
Report path:
Branch / tested commit / report commit if any:
Hardware refreshed:
Engines and exact checkpoints tested:
Measured dual-model peak/free VRAM:
Fast/slow p95 and sample counts:
Cache/context/concurrency observations:
Task/tool/schema quality:
Codex Responses/child routing/budget/cancellation:
TimesFM and graph/tool observations (fixture versus real):
GIFT/news read-only checks:
PASS / FAIL / BLOCKED / NOT_RUN summary:
Recommended engine/model/coordinator:
Blockers or decisions needed:
Cleanup completed:
STOPPED BEFORE PRODUCT IMPLEMENTATION: yes/no
~~~
