# Phase 13 Slow Brain Desk Implementation Plan

Date: 2026-05-16  
Status: implemented and Docker-verified  
Scope: `docs/architecture/live_trading_one_shot_plan.md` Phase 13, local llama.cpp
integration, structured slow-brain desk, pre-market session planning, dashboard visibility.

## Goal

Phase 13 replaces single-pass stock scoring as the final source of new entries with a bounded
overnight/pre-market multi-agent desk:

```text
RegimeSynthesizer
  -> UniverseFunnel
  -> EvidenceAssembler
  -> ThesisAgent
  -> SkepticAgent
  -> PortfolioRiskJudge
  -> FinalIntentJudge
  -> SessionPlanner
```

The desk may create structured entry intents and advisory policy proposals. It must not place
orders, mutate broker state, mutate `config.yaml`, or become part of the market-hours execution
hot path.

Plain English rule:

```text
Slow brain proposes and plans.
Postgres records truth.
Operator and policy gates decide activation.
Execution worker remains deterministic.
```

## Current Findings

Phase 13 is implemented behind `USE_SLOW_BRAIN` and verified through Docker-backed tests.

Current flow:

- `agents/research/pipeline.py` runs `RegimeAgent -> FilterAgent -> BatchScannerAgent ->
  ScorerAgent -> SlowBrainDeskAgent -> ResultsSaverAgent -> KnowledgeGraphAgent`.
- `ScorerAgent` still performs the lightweight scoring/funnel pass and writes `scan_results` /
  `shortlist`.
- When `USE_SLOW_BRAIN=true`, `SlowBrainDeskAgent` replaces the shortlist with only actionable
  final desk decisions.
- `ResultsSaverAgent` preserves slow-brain identity and audit fields when creating pending
  approvals.
- `entry_intents` are produced for every final multi-agent desk decision, including watching and
  rejected decisions that do not create approvals.
- `USE_SLOW_BRAIN` is now wired in the research pipeline.
- Phase 12 memory views and Toolbox are present and should be the read path for agent context.
- `llm/router.py` and `llm_bridge.py` have first-class `llama_cpp` provider support, with
  deterministic fail-closed fallbacks for normal tests.

Local llama.cpp finding:

- Host port `127.0.0.1:8080` is currently occupied by `llama-server`.
- `GET http://127.0.0.1:8080/health` returns `{"status":"ok"}`.
- `GET http://127.0.0.1:8080/v1/models` exposes
  `Qwen_Qwen3-4B-Thinking-2507-Q4_K_M.gguf`.
- The intended non-thinking instruct model is also present at
  `/home/devadethanr/local-llm/llama.cpp/models/qwen3-4b-instruct/Qwen3-4B-Instruct-2507-Q4_K_M.gguf`.

Important port decision:

- Keep the already-running host llama.cpp server on host port `8080`.
- Do not run llama.cpp inside this repo's Docker Compose stack for Phase 13.
- If we revisit a Dockerized llama.cpp later, expose it as `8082:8080` to avoid the host port
  conflict.
- Containers cannot call the host server through `127.0.0.1:8080`; from `app`/`worker`, the host
  server URL should be `http://host.docker.internal:8080/v1` with `extra_hosts:
  ["host.docker.internal:host-gateway"]`.

The repeated `GET /tools 404` log is expected for llama.cpp. `llama-server` is an
OpenAI-compatible inference server, not an MCP server with a `/tools` endpoint. Tool calling, when
used, goes through `/v1/chat/completions` with a `tools` payload. Phase 13 should prefer
code-assembled context packets over live LLM tool calls.

## External Research Notes

Relevant llama.cpp behavior from current docs:

- `llama-server` is an OpenAI-compatible HTTP API server and supports
  `/v1/chat/completions`.
- It listens on `127.0.0.1:8080` by default.
- Official Docker images include `ghcr.io/ggml-org/llama.cpp:server` and CUDA variants.
- Docker Compose can pass settings through `LLAMA_ARG_*` environment variables such as
  `LLAMA_ARG_MODEL`, `LLAMA_ARG_CTX_SIZE`, `LLAMA_ARG_N_PARALLEL`, and `LLAMA_ARG_PORT`.
- `/health` returns ready status and `/v1/models` lists available models.
- The OpenAI client can target llama.cpp with `base_url="http://localhost:8080/v1"` and a dummy
  API key when no server API key is configured.
- llama.cpp supports JSON/grammar constrained output. Because Phase 13 has several different
  schemas, use per-request JSON schema/grammar constraints instead of one global server grammar.

Sources:

- https://www.mintlify.com/ggml-org/llama.cpp/inference/server
- https://www.mintlify.com/ggml-org/llama.cpp/api/rest/overview
- https://www.mintlify.com/ggml-org/llama.cpp/api/tools/llama-server
- https://github.com/ggml-org/llama.cpp/blob/master/docs/docker.md

## Target Architecture

### Research Side

The existing deterministic research stack remains useful:

- `RegimeAgent` still computes the baseline regime.
- `FilterAgent` still narrows the universe.
- `BatchScannerAgent` still builds technical/fundamental/news candidate data.
- `ScorerAgent` becomes a lightweight funnel score, not the final authority for entry approvals.

The new slow-brain desk consumes the deterministic scan output and produces final structured
intent decisions.

### Execution Side

Market-hours execution remains unchanged in principle:

- The worker consumes database-backed order/session state.
- Live entries still require runtime flags, operator controls, risk checks, broker truth, and
  reconciliation.
- LLM unavailability can reduce new research quality but must not block position protection,
  reconciliation, flattening, or kill switches.

## New Modules

Add:

```text
swingtradev3/cognition/__init__.py
swingtradev3/cognition/types.py
swingtradev3/cognition/llm_client.py
swingtradev3/cognition/slow_brain/__init__.py
swingtradev3/cognition/slow_brain/orchestrator.py
swingtradev3/cognition/slow_brain/regime_synthesizer.py
swingtradev3/cognition/slow_brain/universe_funnel.py
swingtradev3/cognition/slow_brain/evidence_assembler.py
swingtradev3/cognition/slow_brain/thesis_agent.py
swingtradev3/cognition/slow_brain/skeptic_agent.py
swingtradev3/cognition/slow_brain/portfolio_risk_judge.py
swingtradev3/cognition/slow_brain/final_intent_judge.py
swingtradev3/cognition/pre_market/__init__.py
swingtradev3/cognition/pre_market/session_planner.py
```

Keep `agents/research/scorer_agent.py` during the transition. Do not delete or bypass it until the
slow-brain path has deterministic tests and a smoke gate.

## Structured Contracts

Define Pydantic contracts in `cognition/types.py`.

Core input contracts:

- `CandidateContextV1`
- `RegimeSynthesis`
- `UniverseFunnelResult`
- `EvidencePacket`

Agent output contracts:

- `ThesisReport`
- `SkepticReport`
- `PortfolioFitReport`
- `FinalIntentDecision`
- `PolicyProposal`
- `SessionExecutionPlan`

Decision enums:

```text
BUY_NOW
BUY_ONLY_ABOVE_TRIGGER
WAIT_FOR_PULLBACK
AVOID_NO_TRADE
```

Intent status mapping:

| Final decision | Postgres `entry_intents.status` | Approval behavior |
| --- | --- | --- |
| `BUY_NOW` | `proposed` | Create pending approval if risk pre-check passes |
| `BUY_ONLY_ABOVE_TRIGGER` | `proposed` | Create pending approval with trigger assumptions |
| `WAIT_FOR_PULLBACK` | `watching` | Store intent, no execution approval yet |
| `AVOID_NO_TRADE` | `rejected` | Store audit trail only |

LLM agents may propose entry, stop, and target assumptions. Code must recompute:

- position size
- max rupee risk
- risk-reward
- tick/price validity
- live execution eligibility

The model must never be trusted for position sizing or broker action.

## Local LLM Integration

### Config

Extend `config.py`, `config.yaml`, and `.env.example`.

Suggested config shape:

```yaml
llm:
  local:
    enabled: false
    provider: llama_cpp
    model: "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
    base_url: "http://host.docker.internal:8080/v1"
    health_url: "http://host.docker.internal:8080/health"
    api_key: "not-needed"
    timeout_seconds: 30.0
    max_retries: 1
    structured_output: true
```

Add env overrides:

```text
LOCAL_LLM_ENABLED=true
LLAMA_CPP_MODEL=Qwen3-4B-Instruct-2507-Q4_K_M.gguf
LLAMA_CPP_BASE_URL=http://host.docker.internal:8080/v1
LLAMA_CPP_HEALTH_URL=http://host.docker.internal:8080/health
LLAMA_CPP_API_KEY=not-needed
LLAMA_CPP_HOST_PORT=8082
LLAMA_CPP_CONTAINER_PORT=8080
```

### Provider Support

Update `llm/router.py`:

- `_provider_has_credentials("llama_cpp")` should use `cfg.llm.local.enabled`, not a real secret.
- `_call_provider("llama_cpp", ...)` should call `_call_openai_compatible()` with local base URL.
- `_call_openai_compatible()` should accept optional `response_format`.
- Health status should use a `local_llm` key, not `nvidia_nim` or `google_gemini`.

Update `llm_bridge.py`:

- For `provider == "llama_cpp"`, bypass ADK registry and call the local OpenAI-compatible endpoint
  directly.
- Validate every response with the requested Pydantic model.
- Reject empty `message.content`, malformed JSON, and responses that only contain
  `reasoning_content`.
- Retry once with a simplified repair prompt; if still invalid, fail closed.

### Structured Output

Use per-request schema generation:

```text
Pydantic model -> JSON schema -> response_format.type=json_schema -> llama.cpp
```

Rules:

- `temperature=0`
- `top_p=1`
- tight `max_tokens` per schema
- no chain-of-thought storage
- only store `reasoning_summary`, evidence IDs, and risk flags
- fallback to deterministic `AVOID_NO_TRADE` or `WAIT_FOR_PULLBACK` when schema validation fails

The currently running server is loaded with a Thinking model. For production Phase 13, prefer the
present `qwen3-4b-instruct` GGUF or relaunch the Thinking model with reasoning disabled and verify a
schema smoke test. A strict local smoke must assert that `choices[0].message.content` is valid JSON.

## Docker Compose And Startup

### Host-Server Mode

This is the best first integration because the host llama.cpp server is already running on port
`8080` with GPU settings.

Modify `docker-compose.dev.yml`:

```yaml
app:
  extra_hosts:
    - "host.docker.internal:host-gateway"

worker:
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

Set:

```text
LOCAL_LLM_ENABLED=true
LLAMA_CPP_BASE_URL=http://host.docker.internal:8080/v1
LLAMA_CPP_HEALTH_URL=http://host.docker.internal:8080/health
```

### Deferred Compose-Service Mode

Do not add a `llama-cpp` service to `docker-compose.dev.yml` in Phase 13. The first integration
uses the bare-metal host process because GPU/CUDA/model-path tuning is already proven there.

If Dockerized llama.cpp is revisited later, use a separate profile and host port `8082`, never the
already-used host port `8080`.

Add Makefile targets:

```text
local-llm-health
phase13-llm-smoke
phase13-smoke
```

`make dev` should not start or depend on llama.cpp.

## Slow Brain Flow

### 1. RegimeSynthesizer

Inputs:

- existing `RegimeAgent` output
- Phase 12 `regime_snapshot_context`
- policy overlays
- market breadth/news/macro inputs

Output:

- `RegimeSynthesis`

Implementation:

- deterministic summary first
- optional local LLM narration only if enabled

### 2. UniverseFunnel

Inputs:

- deterministic scan results
- current active universe
- position universe
- risk config
- regime synthesis

Output:

- top candidates for full debate
- ambiguous candidates for skeptic check
- skipped candidates with reasons

Rules:

- deterministic, not LLM
- sector diversity cap
- no repeated TCS/RELIANCE bias from static shortlist ordering
- bounded `max_full_debate_candidates` from config

### 3. EvidenceAssembler

Inputs:

- candidate scan data
- `MemoryViewClient.research_context_packet(ticker)`
- Memgraph bounded traversals
- recent similar trades
- open positions
- news evidence
- policy overlays

Output:

- `CandidateContextV1`

Rules:

- no raw unrestricted SQL/Cypher
- degrade if Memgraph/Toolbox is down
- always include evidence IDs/source URLs where available

### 4. ThesisAgent

Inputs:

- candidate context
- strategy philosophy
- regime synthesis

Output:

- `ThesisReport`

Role:

- build the strongest long thesis
- propose setup type, catalyst quality, invalidation logic
- no sizing

### 5. SkepticAgent

Inputs:

- candidate context
- thesis report

Output:

- `SkepticReport`

Role:

- attack late entry, fake breakout, bad RR, news quality, sector/portfolio risk
- structured veto flags only

### 6. PortfolioRiskJudge

Inputs:

- thesis and skeptic reports
- Postgres memory views
- portfolio risk view
- open positions
- policy overlays
- operator controls

Output:

- `PortfolioFitReport`

Implementation:

- deterministic risk engine first
- optional LLM explanation second
- code decides whether risk is acceptable

### 7. FinalIntentJudge

Inputs:

- all prior reports
- code-calculated risk metrics

Output:

- `FinalIntentDecision`
- optional `PolicyProposal`

Persistence:

- upsert `entry_intents`
- write cognition audit reports
- create pending approval only for actionable decisions

### 8. SessionPlanner

Inputs:

- operator-approved intents
- session readiness
- funds/cash
- live flags
- existing positions
- operator controls
- policy overlays

Output:

- `SessionExecutionPlan`

Rules:

- can activate, defer, or cancel
- cannot override kill switch
- cannot override exit-only mode
- cannot activate if broker/session readiness is degraded
- should create/queue order intents only for active approved plans

## Persistence And Audit

Add an Alembic migration for:

- `cognition_runs`
- `cognition_reports`
- `session_execution_plans`

Keep payloads JSON but identities/statuses indexed.

Minimum fields:

```text
cognition_runs:
  run_id, phase, status, started_at, completed_at, payload

cognition_reports:
  report_id, run_id, ticker, agent_name, schema_version, status, payload

session_execution_plans:
  plan_id, trading_date, status, payload
```

Existing tables still matter:

- `entry_intents`: final desk output for candidates
- `approvals`: operator approval state
- `order_intents`: execution worker input after session activation
- `execution_events`: audit feed for all transitions

## Dashboard And API

Backend additions:

- `GET /dashboard/cognition/runs`
- `GET /dashboard/cognition/runs/{run_id}`
- `GET /dashboard/cognition/reports/{ticker}`
- `GET /dashboard/session-plan`
- health row: `local_llm`

Dashboard additions:

- Agent Activity should show each slow-brain agent step.
- Research/Approvals view should expose the full trail:
  - evidence packet
  - thesis report
  - skeptic report
  - portfolio fit report
  - final intent decision
  - session planner action
- Risk page should show whether an intent was rejected by portfolio fit, policy, cash, sector
  concentration, or session readiness.

SSE:

- emit `cognition_run_started`
- emit `cognition_agent_completed`
- emit `entry_intent_created`
- emit `session_plan_updated`

## Tests

Normal tests must not require a live LLM.

Add:

```text
tests/test_cognition/test_phase13_types.py
tests/test_cognition/test_llama_cpp_provider.py
tests/test_cognition/test_evidence_assembler.py
tests/test_cognition/test_universe_funnel.py
tests/test_cognition/test_slow_brain_orchestrator.py
tests/test_cognition/test_portfolio_risk_judge.py
tests/test_cognition/test_final_intent_judge.py
tests/test_cognition/test_session_planner.py
tests/test_cognition/test_phase13_persistence.py
tests/test_api/test_phase13_cognition_dashboard.py
```

Required scenarios:

- local provider is disabled by default
- local provider health reports disabled/healthy/degraded
- OpenAI-compatible local calls pass `response_format=json_schema`
- malformed/empty LLM output fails closed
- Memgraph/Toolbox unavailable degrades evidence only
- repeated sector exposure downgrades portfolio fit
- existing position conflict blocks duplicate intent
- `WAIT_FOR_PULLBACK` creates a watching intent, not an approval
- `AVOID_NO_TRADE` stores an audit report, not an approval
- SessionPlanner refuses activation under kill switch, exit-only mode, degraded session readiness,
  or insufficient cash
- approvals alone do not bypass SessionPlanner
- market-hours worker continues without local LLM

Smoke gates:

```text
make test-file file=tests/test_cognition/test_phase13_types.py
make test-file file=tests/test_cognition/test_slow_brain_orchestrator.py
make test-file file=tests/test_cognition/test_session_planner.py
make phase13-smoke
make test
```

Optional live local LLM smoke:

```text
RUN_LOCAL_LLM_SMOKE=true make phase13-llm-smoke
```

The live smoke should:

- call `/health`
- call `/v1/models`
- request one tiny JSON-schema decision
- validate `choices[0].message.content` through Pydantic

## Implementation Order

1. Add local LLM config, health, and provider support.
2. Add structured-output helper with Pydantic schema validation and fail-closed behavior.
3. Add cognition Pydantic contracts and deterministic unit tests.
4. Add persistence migration/repository methods for cognition runs/reports/session plans.
5. Add `EvidenceAssembler` and `UniverseFunnel`.
6. Add `ThesisAgent`, `SkepticAgent`, `PortfolioRiskJudge`, and `FinalIntentJudge` using mocked
   LLM tests first.
7. Add `SlowBrainOrchestrator`.
8. Wire `USE_SLOW_BRAIN=true` into the research pipeline behind a safe fallback.
9. Change approvals/session activation so the planner, not approval click alone, creates active
   execution intent when Phase 13 is enabled.
10. Add `SessionPlanner`.
11. Add dashboard/API endpoints and health status.
12. Add Makefile smoke targets.
13. Run focused tests, then full `make test`.
14. Only after all gates pass, mark Phase 13 `[X]` in
    `docs/architecture/live_trading_one_shot_plan.md`.

## Decisions

- Use host-server mode first because the local llama.cpp server is already running and healthy.
- Do not add a Compose llama.cpp service for Phase 13. Use host-server mode only.
- Use the non-thinking `qwen3-4b-instruct` GGUF for production structured decisions.
- Do not use `/tools`; llama.cpp tool/function calling belongs inside `/v1/chat/completions`.
- Do not let the slow brain directly create broker orders.
- Keep deterministic scan/filter logic as the source of raw candidate facts.

## Risks

- Small local models can produce invalid schemas under complex prompts. Mitigation: compact context,
  strict schemas, fail-closed validation, deterministic risk checks, and live local smoke.
- A Thinking model can emit reasoning-only output. Mitigation: prefer the instruct model and assert
  valid JSON content before enabling the desk.
- Docker containers cannot reach host `127.0.0.1`. Mitigation: use `host.docker.internal` with
  `host-gateway` or the Compose service DNS name.
- If approval clicks still queue execution directly, the SessionPlanner can be bypassed. Mitigation:
  under `USE_SLOW_BRAIN=true`, approvals mark operator consent only; SessionPlanner activates.
- Memgraph/Toolbox downtime can weaken context. Mitigation: degrade research context only, never
  execution safety.

## Definition Of Done

Phase 13 is complete only when:

- `USE_SLOW_BRAIN=true` makes new entries come from the multi-agent desk, not from single-pass
  `ScorerAgent` output.
- All slow-brain outputs are structured and Pydantic-validated.
- Final desk decisions persist to Postgres `entry_intents` with complete audit reports.
- Pre-market SessionPlanner is portfolio-aware and universe-aware.
- Dashboard shows local LLM health, desk run status, per-agent audit trail, and session plan status.
- The worker still runs safely with local LLM disabled or down.
- `make test` and Phase 13 smoke gates pass.
