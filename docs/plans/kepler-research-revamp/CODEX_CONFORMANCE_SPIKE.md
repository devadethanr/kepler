# Local Codex conformance spike

This is a **test and findings task only**. Run on the user's actual machine under [INITIAL_SPIKE_PLAN.md](INITIAL_SPIKE_PLAN.md), then stop for feedback. Preparing this document did not install anything or call models. During the requested local spike, Codex may provision the necessary pinned runtimes/models in isolated experimental environments and write minimal disposable runners and fixtures. Preserve application dependency files, production services and the working driver; do not implement a product adapter or change live behavior. No local compatibility, GPU performance, credentials, or quality results have yet been measured. Populate the existing [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md) and return its handback summary before product implementation.

The authoritative decision is in [Implementation plan](IMPLEMENTATION_PLAN.md), section 5. Both actual models must pass every mandatory gate; a chat-completions success is not evidence of Responses compatibility. A failed mandatory gate selects the documented ADK contingency; blocked or unrun is **not** a failure or a pass and leaves selection undecided. Do not create an open-ended protocol translator or silently use cloud inference.

## Sources and protocol boundary

- [Current Codex App Server documentation](https://developers.openai.com/codex/app-server/) and [pinned App Server README](https://github.com/openai/codex/blob/67f0994b532b8740f14b5b738af7b7b2a915b1d6/codex-rs/app-server/README.md): App Server is a JSON-RPC interface; initialize, start a thread, start a turn, observe notifications and completion, and interrupt a turn. Generate/use the schema for the **installed pinned version**; experimental features and event shapes can change.
- [Codex Responses proxy](https://github.com/openai/codex/blob/67f0994b532b8740f14b5b738af7b7b2a915b1d6/codex-rs/responses-api-proxy/README.md) forwards Responses requests; it does not establish a chat-to-Responses translation.
- [vLLM OpenAI-compatible server documentation](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/) and [SGLang OpenAI API documentation](https://docs.sglang.ai/basic_usage/openai_api_completions.html). Inspect the documentation and release/source matching the actual installed versions for `/v1/responses`, including limitations. SGLang's [Responses implementation](https://github.com/sgl-project/sglang/blob/main/python/sglang/srt/entrypoints/openai/serving_responses.py) is evidence of an implementation, not proof that the selected release/model supports Codex's full request and streaming dialect. Check vLLM likewise. HTTP 200 or `/v1/chat/completions` alone is insufficient.

## Stages and prerequisites

Proceed in order; stop a dependent branch on a blocker and record independent observations. Use temporary, isolated, disposable workspace and test-only identities, no production writable mounts, secrets, broker access, graph connection or unrestricted network. No live trading. Use loopback-only endpoints, disable cloud fallback, redact logs and restrict retained request payloads. Pin versions, exact model revision/quantization, tokenizer/template, launch flags and GPU UUID; never record credentials. Request logs must show actual endpoint and model identity, not merely client configuration.

- **S0 safety and hardware:** Read [audit](PRE_IMPLEMENTATION_AUDIT.md) graph warning. Do not run graph deletion fixtures or broad tests: the YAML override can shadow `MEMGRAPH_URI`. Use an in-memory fake graph, never the real DB. Refresh the user-reported 16,303 MiB 5070 Ti and 12,288 MiB 3060 inventory, GPU UUIDs, OS/RAM/driver and current free memory. Record missing prerequisites and never expose secrets. Provision only through the isolated, pinned procedure in INITIAL_SPIKE_PLAN.md; do not substitute silently. Confirm isolation and stop a dependent stage if it cannot be demonstrated.
- **S1 engines:** Compare pinned vLLM and SGLang with the retained llama.cpp baseline, using compatible checkpoint formats and documented Responses support. GGUF, AWQ, GPTQ and QAT-unquantized are not interchangeable. Record missing/unsupported combinations accurately. Start only local loopback services with resource limits and cleanup; capture readiness, GPU mapping, actual model/parser identity and logs. Record unsupported startup or out-of-memory as failure with exact conditions. Do not assume engine version support implies model/template support.
- **S2 models:** On each available engine exercise Gemma 4 E4B and Qwen3.5-9B independently using exact local artifact revisions. Capture load/peak VRAM, context and output limits, cold/warm timing and errors. Test one service per intended GPU and simultaneous load; if hardware cannot accommodate both, record blocker rather than claim the intended deployment works. QAT and other quantizations are distinct candidates.
- **S3 Responses and tool protocol:** Execute matrix below directly against each model/engine pair using actual `/v1/responses`. Preserve redacted request, response and streaming event order and IDs. Compare against the pinned engine and Codex schemas. A pair failing S3 cannot enter S4 as compatible.
- **S4 Codex App Server:** With each S3-passing endpoint, pin Codex build, config and generated schema; initialize once per connection, start thread and turn, capture JSON-RPC request IDs, thread/turn/item IDs and notifications through terminal completion. Exercise each tool and negative case below. Test interruption and process failure, with cleanup and no success claimed for an interrupted turn. Record approvals/denials and whether commands or capabilities actually executed.
- **S5 collaboration/evaluation:** Run the tiny fixture below and the same held-out task with the existing ADK baseline if safely available, using the same evidence, limits and evaluator. Measure native child routing, global accounting and cancellation. If ADK or held-out data is unavailable, record comparison blocked; don't invent a baseline. Report findings and **STOP for user feedback** before any feature implementation or runtime selection.

## Fixtures and manual test matrix

Create an isolated temporary run directory and write fixture files there, not under production data. Give each test a unique run ID and monotonic timestamps. Record input, expected/actual outcome, logs and status in `SPIKE_FINDINGS.md`. Define tool responses independently of model output:

- Graph fake: `ACME -> SUPPLIES -> BETA`, source `g1`, observed `2026-01-02`; unknown nodes return empty, unavailable mode returns explicit error, and historical `as_of` is unsupported. Expose only bounded lookup/neighbors/evidence; prohibit arbitrary Cypher and assert no real DB socket/credentials.
- Files: allowlisted `evidence/brief.txt` contains `ACME supply disruption reported; source f1`; a sibling outside root and a symlink escaping root must be denied. Search returns only that fixture with `f1`; distinguish empty from error.
- Browser: local fixture HTTP page contains `Source b1: BETA inventory is uncertain`; allow local fixture origin only, deny external/private-network redirects and file URLs, and capture actual navigation and returned text. No internet browsing required.
- Forecast: fake TimesFM tool returns a fixed typed result with artifact `t1`, cutoff, horizon, quantiles and explicit uncertainty; invalid/missing bars and unavailable service return errors, never fabricated forecasts. This checks tool integration, not TimesFM model accuracy.

| ID | Procedure and objective pass criterion |
| --- | --- |
| R1 | Send simple non-streaming Responses request; correct response schema, model identity and terminal status, with usage reported or explicitly absent. |
| R2 | Stream the same request; ordered valid events reconstruct the terminal output and correlate IDs; detect truncated/error streams. |
| R3 | Force a typed function call, validate name/arguments/call ID; send its matching output in the next Responses input and require grounded final answer. Repeat multi-turn context and malformed arguments/tool failure. No dropped/reordered call IDs or invented success. |
| R4 | Interrupt/disconnect a deliberately long generation; observe terminal/cancel/error and server-side generation/resource cessation within a measured deadline; capture residual tokens and any late calls. |
| C1 | Initialize App Server and run a thread/turn for **each** model; capture actual engine request, turn/item lifecycle, final text and usage. Confirm effective provider/model match the engine logs. |
| C2 | Invoke graph, file, search, browser and forecast fixtures via the permitted tool bridge; final claims cite fixture IDs and actual outputs. Try empty, unavailable, unsupported `as_of`, traversal and redirect escapes; all deny or report errors accurately. Absence of a safe bridge is blocked, not permission to add unrestricted shell. |
| C3 | Interrupt a long turn and separately kill the isolated server during a tool call. Observe terminal state, child/provider cessation, cleanup and whether resumption is possible; no phantom completion or duplicated tool action. |
| C4 | Run a parent with tiny externally enforced caps (for example 2 model calls, 1 tool call and explicit token/deadline caps). Attempt extra parent and child calls concurrently. Atomic reservations must reject excess **before execution**, include retries/children and record usage or conservative reservations when usage is unavailable. Verify no uncounted work after cancellation/deadline; accounting gaps fail the gate. |
| C5 | Spawn/message/reply/continue a native child when enabled, measuring actual parent and child endpoint/model from independent server request logs. Request each approved model in turn and test overrides/provider inheritance. A configured name or model self-report is not routing evidence. If native heterogeneous provider routing fails, test externally mediated top-level threads only if one coordinator and all other gates remain enforceable; otherwise fail. |
| E1 | Tiny room: analyst cites `g1` and `f1`; skeptic asks whether inventory is known and cites `b1`; analyst revises to uncertainty; forecast role requests `t1` and explains uncertainty. Require actual addressed messages, a challenge and revision, exact citations, no unsupported claim, bounded calls and a terminal conclusion or explicit abstention. Repeat with one unavailable tool and verify honest degradation. Compare same task/budgets to available ADK baseline; record held-out evaluator and outcome, not subjective model self-rating. |

Each row is **PASS** only with its stated observable evidence. **FAIL** is an observed unmet criterion; **BLOCKED** requires a specific missing prerequisite; **UNRUN** means not attempted. Record per model × engine × test, including unsupported, missing usage and unknown child events. Never infer pass from absence of error. Capture actual elapsed time, input/output/reasoning tokens when exposed, model/tool call counts, p50/p95 only with sample count, peak VRAM, and failure/timeout/cancellation outcomes; mark unavailable metrics unknown. Do not expose private data in logs.

## Findings handoff for local Codex

Populate the existing `SPIKE_FINDINGS.md` beside this plan after running. Store redacted logs outside production paths; link each result to reproducible command/config (secret-free), request/event artifact and timestamps. Include versions/revisions and limitations so another operator can repeat it. If execution cannot start, still create the file with blocked/unrun rows and the missing GPU, artifacts, binaries, credentials or authorization spelled out. Report evidence, gate decision and questions to the user; then stop.

```markdown
# Spike findings
Date/time, host/OS, operator, repository commit:
Safety/isolation evidence and cleanup:
GPU UUIDs, driver/CUDA, RAM/VRAM; availability/authentication (no secrets):
Codex version/commit, schema version, configuration hash:

| Engine/version | Model/revision/quantization | GPU UUID | Context/template | Endpoint | Load/peak VRAM | Status/blocker |
| --- | --- | --- | --- | --- | --- | --- |
| vLLM | Gemma 4 E4B | unknown | unknown | local | unknown | UNRUN |
| vLLM | Qwen3.5-9B | unknown | unknown | local | unknown | UNRUN |
| SGLang | Gemma 4 E4B | unknown | unknown | local | unknown | UNRUN |
| SGLang | Qwen3.5-9B | unknown | unknown | local | unknown | UNRUN |

| Stage/test | Engine/model | PASS/FAIL/BLOCKED/UNRUN | Expected vs actual | Evidence/log path | Duration/tokens/calls/VRAM | Reason/next prerequisite |
| --- | --- | --- | --- | --- | --- | --- |
| S0–S5 / R1–R4, C1–C5, E1 | each applicable combination | UNRUN | unknown | none | unknown | not executed |

Artifacts: redacted requests, Responses streams, server logs, App Server JSON-RPC/events, tool outputs, correlation IDs, cancellation/resource observations, budget ledger, evaluator results and cleanup evidence (paths or explicitly unavailable).
Actual child provider/model routing and usage gaps:
ADK comparison and held-out task results:
Mandatory gates: pass/fail/blocked/unrun with evidence; decision or undecided:
Limitations, blockers and questions for user:
```
