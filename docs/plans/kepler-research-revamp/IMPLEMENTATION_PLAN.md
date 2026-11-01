# Kepler collaborative-research revamp — revised handoff

Revision 4, 1 November 2026. Read SPIKE_REVIEW.md first: the local spike and all three authorized follow-ups are complete and recorded at `8d7ddfc`. They do not approve production deployment. Read PRE_IMPLEMENTATION_AUDIT.md before tests; the destructive graph-target defect is still unfixed. The next validation scope is evidence export and grounding/evaluator review, not a repetition of the whole spike.

## Mandatory stage before product implementation

The local spike tested runtime/model fit, cache/context, tools, Codex and forecasting with scoped successes and failures. Follow-ups resolved isolated browser execution and adapter-backed Codex worker functionality. Grounding, representative adaptive research, product durability, optimized runtimes and market data/forecast quality remain unresolved. Review the existing evidence before further implementation. Docker remains optional; neither host driver changes nor an unconditional all-GPU placement rule is justified.

Keep the measured default llama.cpp/GGUF pair, including explicit CPU embedding placement, as a comparison baseline. The measured vLLM/SGLang arms did not yield a passing replacement; this is not a universal engine ranking. Selected-record correctness was 2/30 per preferred lane despite valid JSON. No production engine/model/coordinator is selected. Inspect the sanitized runner/evaluator/bridge artifacts and follow NEXT_VALIDATION_PLAN.md rather than reinstall or retest unchanged arms.

## 1. User decisions and scope

The user wants autonomous agents that collaborate, challenge one another, browse, traverse Kepler's graph and revise their views until reaching a supported conclusion. The discussion must be visible live with actual evidence. LIVE TRADE ENTRIES STILL REQUIRE USER APPROVAL.

Keep Zerodha, existing broker reconciliation, protective orders, operator controls and risk limits. This is not a broker migration or authorization for autonomous live execution. Research can conclude no action or unresolved disagreement; it must not manufacture consensus or a trade.

Baseline inspected: origin/main at 8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0. Planning work did not switch or edit the application checkout. The actual implementation must inspect latest local/main, preserve operator changes and retain the pushed hardening fixes.

The user's local output confirms an RTX 5070 Ti with 16,303 MiB and an RTX 3060 with 12,288 MiB in the same PC, driver 610.43.02, CUDA UMD 13.3 and nvcc 13.3/V13.3.73. The display GPU had 568 MiB in use in that snapshot. Refresh GPU UUIDs/current free memory and record OS/WSL/RAM locally. These are user-reported capacity observations, not model benchmarks. Do not ask the user for secret values or replace a working driver.

## 2. Read-first blocker: destructive graph test isolation

Confirmed static defect: app-test environment MEMGRAPH_URI can be shadowed by explicit YAML context_graph.uri. A graph fixture calls MATCH(n)DETACHDELETE n using the resulting repository and default session database. If main graph is reachable, a supposedly isolated test can delete it.

DO NOT run destructive graph tests, broad make test or arbitrary test-file collection until isolation is fixed and refusal is proved. Do not rely solely on a hostname containing 'test'.

The first product safety slice, after spike findings review, must:
- Define effective configuration precedence using dummy-value unit tests and redacted diagnostics.
- Configure an exclusive disposable graph service/database and isolated test identity/network.
- Add a fail-closed guard checking the actual expected test target/database before any destructive operation, including fixture driver sessions.
- Prove a production-like target is refused without executing deletion.
- Test Toolbox disable overrides and graph-client/Toolbox target consistency.
- Preserve all existing operator data. No blind deletion of runtime JSON/caches or actual credentials.

No destructive tests were run for this audit. The blocker describes reachable behavior, not a claim that data has been lost.

## 3. Required replacements before feature expansion

Detailed evidence, usage and migration tests are in PRE_IMPLEMENTATION_AUDIT.md. Important distinctions:

| Current item | Treatment |
|---|---|
| MEMGRAPH_* defaults versus explicit YAML | Fix precedence and test isolation first; redact credentials |
| TOOLBOX_ENABLED/URL overridden by YAML | Fix precedence; disabled must mean no network call |
| LOCAL_LLM_ENABLED | Already has an explicit environment override; do not 'fix' as though broken |
| KITE_MCP_URL example port3000 | Align sample with actual8080/mcp; preserve operator overrides |
| Multiple model routers/role namespaces | Canonical role policy across callers; SmartRouter is role-blind, LLMRouter is not |
| max_tool_calls_per_stock | Legacy iteration budget, not global actual-call cap; migrate with compatibility tests |
| Duplicate schedule fields | Consolidate effective registration after tracing actual consumers; do not remove used auth/approval gates |
| USE_SLOW_BRAIN | Active and affects approved-entry flow; preserve semantics |
| USE_EXCEPTION_ANALYST | Defined but no production reader found; consolidate with learning.exception_reasoning.enabled |
| GIFT05:00 print-only check | Replace with real calendar-aware06:30-session context job |
| In-memory sessions and unleased scheduler tasks | Replace research ownership with durable jobs/messages/leases |
| Single local endpoint / identical debate paths | Add model profiles and adaptive room coordination |
| TimesFM Git HEAD/cache/derived targets | Pin, version inputs and outputs, remove fake bounds and success states before score influence |
| JSON/in-memory activity snapshots | Keep only compatibility projections; durable run/message events become authoritative |

An old provider/model string is not automatically invalid. Verify intended endpoint/model availability separately and record unavailable versus deprecated. Actual local credential validity has not been audited; never rotate/delete keys merely from sample-file names.

## 4. Architecture: adaptive Research Room, not fixed speaking order

Existing data collection may remain a deterministic ingestion pipeline. Deliberation becomes an adaptive conversation.

A room has a question, scope/session, pinned evidence snapshot, participants, unresolved issues, capability grants and a shared budget. Initial independent reports are followed by messages addressed to one another, questions, challenges, evidence requests, revisions and synthesis. The chair selects the next useful action from the current issues; the skeptic can challenge the chair. There is no mandatory thesis -> skeptic -> one rebuttal ordering.

Initial roles (at most3 active, sharing2model processes):
- Evidence/market analyst: primary-source and graph investigation.
- Thesis/portfolio researcher: deeper interpretation and hypotheses.
- Skeptic: counterevidence, missing assumptions and conflicting facts.
- Optional ForecastAnalyst participates when a forecast question matters, using the shared TimesFM tool.

Gemma/Qwen role assignment is configurable. Fast extraction, entity/time checks and simple tool selection use Gemma; deep interpretation uses Qwen. A role can revisit a topic and call either approved profile within budget. Different model families are not independent source evidence.

A RoomMessage contains run/message/sequence IDs, sender/recipients, reply_to, kind, public text, claim/evidence references, timestamps and validation result. Kinds include question, claim, challenge, evidence, revision, synthesis, decision and abstention. Record actual published discussion, not hidden internal reasoning.

Stopping:
- Supported conclusion after meaningful participation and opportunity to object.
- Explicit unresolved/no-action conclusion if evidence remains insufficient.
- Immediate stop/degraded result on cancellation, deadline, exhausted budget, permission violation or unrecoverable persistence/provider failure.
- Loop detection for repeated claims/messages without new evidence.
- No requirement that all agents agree; preserve minority objections.

Full-room ceilings:20 minutes,24 model calls,24 tool calls,100k input and16k generated tokens including children/reasoning. Short-room ceilings:3 minutes,6 model calls,8 tool calls with explicit token caps. Start at1fast+1slow inference concurrently. Limits are ceilings, not targets, and remain outside model-editable content.

## 5. Orchestrator choice: genuinely test Codex

The current fixed ADK coordinator is not enough for the requested behavior. ADK itself supports custom dynamic agents, so it can implement the room contract; the existing SequentialAgent dispatch should not define the new room.

Codex offers reusable native agent loops, skills, tool/file/search behavior and collaboration. Prefer a supported external interface over copying Rust internals into Python.

Decision:
1. Build one framework-neutral Python/Postgres Research Room contract and read-only tool gateway.
2. Run the bounded Codex App Server conformance spike before choosing its production room adapter.
3. If EVERY mandatory gate passes, use Codex App Server as the selected room coordinator and retire the ADK room coordinator. Reuse existing Python data/forecast/validation services behind tools.
4. A definitive inability to meet a mandatory product gate selects the dynamic ADK contingency; BLOCKED or unreviewed gates leave selection undecided. A scoped adapter worker pass is not a product coordinator pass. Preserve the explicitly authorized adapter experiment and do not silently call paid cloud models.
5. Never run two competing coordinators for one room or add LangGraph/another framework just to obtain chat.

Post-spike qualification: original native endpoints failed, but the user explicitly authorized an isolated Responses/Chat adapter and it passed bounded worker/tool fixtures on both models. Native multi-agent tools remain disabled; routing used externally coordinated top-level threads. Do not automatically discard that result or call it unmodified native compatibility. Definitive inability to meet required behavior selects the ADK contingency; blocked/unreviewed gates leave selection undecided. The 1-run controlled Codex/ADK comparison proves neither a quality nor latency winner, and its conservative reserved-token counts are not actual consumption.

Mandatory Codex gates:
- Both actual local models support the required Responses request/stream/tool/result/cancellation behavior, not only chat completions.
- Role routing to both model identities works; native child provider inheritance/overrides are measured, not assumed.
- Complete public child messages/tools are captured and correlated durably.
- Strict global parent budgets account for and halt children.
- Sandboxed filesystem/network/tools cannot reach broker credentials or production writes.
- Held-out Kepler evidence tasks are correct, grounded, observable and within latency/resource limits.
- Crash/cancel/reconnect has verified semantics and no false recovered transcript.

Do not treat the Codex Responses proxy as a chat-completions translator. Native collaboration flags and API shapes are versioned. Separate top-level Codex threads with externally mediated chat are acceptable only if the same gates pass and there is still one coordinator. See COLLABORATIVE_HARNESS_RESEARCH.md for pinned source references.

## 6. Durable jobs, discussion and recovery

Postgres owns research jobs/runs, immutable published messages, tool results, evidence versions, budget reservations and lease fencing. Reuse existing cognition artifacts and SSE capabilities rather than inventing a second business-state store.

Persist step/message/final-result state and corresponding outbox event atomically. UI reads history plus a consistent watermark then replays SSE by cursor. Native ADK/Codex events are translated into the Kepler contract, not treated as durable state by themselves.

Use deterministic run/trigger/evidence IDs, one fenced lease per room, heartbeat, expiry and bounded idempotent retries. Persist intent before external calls; uncertain results are unknown until safely reconciled. Restart either resumes verified framework/child state or marks interruption and starts a linked attempt; never pretend full recovery.

Expose queue/run/message/evidence/resource reads and authenticated research pause/cancel controls. Research cancellation cannot affect broker GTTs, worker controls or account holdings. Avoid a database event for every token; final published messages must be recoverable. Any partial message stream is labelled partial and cleared/finalized consistently on reconnect.

## 7. Skills and executable tools

A skill is guidance, not permission and not an executable tool by itself. Supply both versioned skill content and real enforcing tools.

Required initial skills:
- Kepler context-graph investigation.
- Evidence-grounded web research.
- Official agent-browser core/navigation/extraction skill.
- Research artifact file/search.
- TimesFM forecast interpretation.
- Room challenge/synthesis and optional Harness² experiment proposal.

Each run pins skill IDs/content hashes, model/prompt/tool versions and capabilities. Official agent-browser's current skill stub requires matching CLI core instructions; capture and review those at build time. In Codex use a reviewed .agents/skills installation; in ADK implement explicit registry/loading. Do not give an unrestricted Bash tool merely because upstream skill front matter mentions Bash(agent-browser:*).

One typed gateway, usable via MCP or framework functions:
- graph.lookup / neighbors / evidence / bounded paths.
- research.list / read / search under approved artifact roots.
- web.search / fetch.
- browser.open / snapshot / click / extract / close through an isolated service.
- forecast.timesfm with a typed request/result.
- experiment.propose / probe / compare for approved research-harness candidates.

Enforce run/role grants, bounded sizes/hops/rows/time, URL/redirect and path validation, provenance, secrets redaction and budget at the gateway. No arbitrary Cypher/SQL/shell, broker writes or arbitrary filesystem access.

Current graph methods provide useful traversal but not historical time travel. Return projection cursor/lag, coverage and unavailable versus empty. graph as_of must be rejected as unsupported unless source/edge version history and first-availability prove it. Consequential current portfolio/risk truth remains the authoritative curated Postgres view, not a stale graph.

See SKILLS_AND_CONTEXT_TOOLS.md for actual repository gaps, capability contracts and official skill pin.

## 8. Heterogeneous two-model deployment

The initial spike is executed. Existing artifact pins below identify candidate and comparison profiles, not approved production defaults. Only default-placement llama.cpp completed the preferred-pair latency measurements; optimized formats and strict-GPU fast latency failed or were blocked in the measured arms. Native scripts remain a first-class option. Consult MODEL_CANDIDATES.json and SPIKE_REVIEW.md for reported versions and unresolved quality gates.

Preferred pair:
- RTX 3060: official Google Gemma 4 E4B QAT Q4_0, text only, file5.15GB/4.80GiB; no multimodal projector.
- RTX 5070 Ti: Qwen3.5-9B Q5_K_M, file6.58GB.

GemmaE4B has roughly 8B total / 4.5B effective parameters. Weight size is not peak VRAM. A6GB3060 can be tight;8/12GB is more plausible but still needs actual measurement.

Preserve known working baseline. Detect hardware locally and bind independent servers by GPU UUID. Start one slot each; fast4Kcontext/thinkingoff/shortschema, slow8Kcontext/boundedreasoning/finalJSON. Use matched model templates rather than Qwen tokens for Gemma. Keep cloudfallbackOFF unless explicitly configured.

If Gemma fails fit/latency/quality, use the tested Qwen3.5-4Bfallback or existing model, clearly labelled; do not silently offload/tensor-split. Same-family fallback is operationally valid but does not provide model diversity.

Check runtime/driver supports both Blackwell and Ampere. Candidate llama.cppv0.8.0 supports researched architectures, but benchmark actual endpoints concurrently and pin binaries/artifacts/checksums. Account for existing FinBERT/TimesFM separately.

Flint is optional offline coding/research experimentation, not a required third resident service. Its39.8Btotal weights dominate memory despite~2.5Bactive; officialNVFP4~22.86GB is not a single16GB fit. Low-bit community experiments are unvalidated quality/headroom.

See MODEL_CANDIDATES.json and MODELS_AND_FAST_BRAIN.md. No local GPU benchmark has been performed.

## 9. Intelligent fast brain

Deterministic means reproducible authority, not an unintelligent system.

Layer1: hard invariants, broker truth, quote freshness, position sizing/risk, operator controls and protective execution.
Layer2: versioned decision/state policy on validated features, with thresholds, hysteresis, confidence/unknown handling, cooldown and permitted actions.
Layer3: asynchronous Gemma text understanding and optional independently evaluated ML/decision scoring for research/alerts.

Allowed fast decisions:ignore/defer/notify/requestevidence/escalate/review. No model can approve a live entry, clear a kill switch, alter GTTs or hold the execution mutation lock.

LiquidAI d1-2B is a real single-forward decision model, not a chat replacement. Its system_one questions/probabilities require a compatible interface, reviewed code/licence and own-data calibration. Keep it as a later offline/shadow challenger; no third required service and no zero-shot trading authority.

Measure recall/falsepositives/calibration/drift and eventual outcomes on chronological development/calibration/held-out data. Late, stale or malformed inference abstains explicitly. Urgent broker incidents follow existing deterministic response before research diagnosis.

## 10. TimesFM: shared tool plus an optional forecasting participant

Post-spike decision: informational CPU use only; NO score, sizing, stop/target or risk influence. The 36/36 disposable wrapper checks do not repair the unchanged product. The reported historical sample showed no baseline accuracy advantage and nominal 80% interval coverage 64.5% (supplementary block interval 54.0–75.2%), with current-vintage/pretraining/NSE-applicability limits. Use the API-returned point (channel 5 at the tested pin), not channel 0 from the full array. Quantile crossing correction is not calibration. See SPIKE_REVIEW.md and FOLLOW_UP_FINDINGS.md before changing this component.

Current integration is TimesFM 2.5 200M, context512/maxhorizon128, dailyclose caller requesting20bars. Existing TimesFMAgent is a deterministic ADK wrapper, not a conversational LLM.

Keep TimesFM as one shared typed ForecastTool. ForecastAnalyst is a room role that invokes it, compares baselines, explains uncertainty and responds to questions. Multiple agents reuse the same forecast artifact rather than load separate forecasting models.

Required replacements:
- Pin compatible library commit and checkpoint revision; current dependency follows GitHEAD.
- Reuse a validated timestamped candle snapshot with completed bars, exchange/calendar, source/adjustment version and decision cutoff.
- Validate before cache lookup. Cache key includes input hash, cutoff/lastbar, interval/horizon, instrument, model/config revision and adjustment basis; use atomic concurrency-safe storage.
- Reject future/stale cache entries, invalid/insufficient/nonfinite input and shape/quantile errors.
- Typed statuses, no empty-dict success or blanket 'forecast generated'.
- Keep raw point/quantile outputs with explicit channel mapping and dates.
- Remove inferred entry/stop/target levels and invented±5%fallback bounds; an80%nominal band is not calibrated risk protection.
- Do not retry inference merely because an unrelated async step failed.
- Start explicitly CPU-first, single-flight loading, bounded queue/concurrency. Benchmark CPU before any reservedGPUoption; do not silently occupy the two LLMGPUs.
- Forecast status/provenance/latency and baseline comparison visible in graph/evidence/UI.
- Disable automatic score influence until evaluation; advisory artifacts remain usable.

Evaluation: rolling-origin same-cutoff forecasts versus last-price/random-walk and predeclared drift baselines; per-horizon error/direction, quantile pinball/empiricalcoverage/width, regime/instrument stability. Any strategy translation needs separate realistic-fee/slippage holdout evaluation. Historical cache and pretrained-data contamination must be acknowledged. Current tests/cache are not proof of live forecast skill.

See TIMESFM_AUDIT_AND_REUSE.md for code-level findings. Do not silently upgrade to TimesFM 3.0 or assume2.5has its multivariate/API behavior.

## 11. GIFT Nifty and Singapore implementation

Implement the market-context service; only its predictive authority is gated.

GIFT Nifty is the Indian index derivative on NSEIX, formerly SGXNifty. Current normal session starts06:30 IST before NSE09:15. Singapore equities also open09:00 SGT=06:30 IST, so 'opens early' does not prove Singapore causes Indian moves.

First probe current Kite master-resolved NSEIX:GIFT NIFTY using existing entitlement, read-only; publicmasterpresence does not prove streaming/history/freshness. Optional Upstox global row declares120secondsdelay; label it and verify actual account support.

Treat discovered quote rows as proxies, not expiry-specific tradable futures. Use source timestamps, declared delay, actual freshness and contract/roll limitations. Do not convert futures-minus-spot directly into a predicted gap.

Singapore v1: STI and macro context, separate calendar/lunch/holidays. STI is bank-heavy, not a broadAsia oracle. Yahoo^STI is best-effort/unofficial; no realtimeSLA. Missing input staysunknown, notneutral0.5.

Use current NSEIX session/calendar/circulars (06:30–15:40,16:05–02:45nextday normal sessions), SGX09:00–12:00/13:00–17:00SGT. Initial outputs: morningcontextbriefing, observedovernightmove where definitionvalid, source/staleness and divergence flags. NoSingaporetrading.

Shadow/ablation: baseline vs+GIFT vs+STI using data available before each decision, fees and chronological splits. Do not claim a causal lead or tradingedge from correlation. GIFTimplementation is required; an unavailable entitlement produces an honest unavailable state until a usable source is configured.

## 12. News, Scrapling and browser skill

Repair and reuse current source registry/normalization/store. Ingest feeds once and query locally. Primary baseline: NSE/SEBI/RBI, ETpermittedheadlines, Fed/ECB; companyIR/filings for relevant names. HTTP200HTML is not a feed. Quarantine currently broken/blocked source configs until semantic validation succeeds.

Store namespacedIDs, stablecontenthash excludingfetch time, first_seen/published/sourceupdated/fetchedUTC, versionhistory, evidence spans, entitymappingconfidence and syndicationclusters. Unknownpublication staysunknown; all providers share freshness/domain filters and cache keys include thosefilters.

Scrapling is now an approved REQUIRED extraction adapter behind the existing provider boundary. Start ordinaryHTTP/adaptive selectors with source profiles and completeness/quality fixtures. Do not replace everything or expose stealth/proxy/CAPTCHA features.

The official agent-browser skill AND executable capability must be available to approved research agents during work. Use HTTP/sourceparser first, repairedCrawl4AI second, agent-browser for navigation-heavy questions. Browserisolation, publicreadonlyscope, fixedbudgets and groundedtoolresults are mandatory. No personalChrome, credentialmounts or unrestrictedhostshell.

Initialworkerbudgets:1browserjob,2HTTPfetches, source-specificratebackoff;120secondwholebrowserjob,12actions, boundedretries,10newenrichmentdocuments/day. Skillinstallation alone is not completion; demonstrate an agent selecting/loading the skill and executing a permitted workflow.

Do not use freeNewsAPI/GNews as timelyproductionbackbone: inspectedfreeplans have24h/12hdelays andusage restrictions. Optional paid/quota discovery is explicitly configured, not an automatic fallback.

## 13. Real-time conversation and Gather-like UI

Primary: existing ReactResearchDesk with actualpublishedmessages, replies, objections, evidence and conclusions. Use typedstreamingrecords and durablefinalmessages. Source drawer shows quote/artifact, sourceURL, dates, asof/firstseen/version, model/tool identity and unknown/stale state.

Optionalofficeview: selectively reuse/reference PixelAgents' MITReactCanvas approach after third-partyasset review. Its current Claudehook provider is not a Kepler/Codexadapter; implement the Kepler eventprovider. Each actor maps to real run/step/agentinstance, speaking only on actualmessageevents. Staleconnection must not look active. Transcript remains usable withoutcanvas.

StarOfficeUI art has noncommercial restrictions; WorkAdventure adds a heavier stack and CommonsClause restrictions. Do not call alltheirassets/commercialuse unrestrictedopensource.

AG-UI/CopilotKit can supply protocol/components after version-fit proof; they do not replace durablestate. CodexJSONRPC orADKevents translate into the same Keplerownedcontract.

Keep graphvisualizationoptional, keyboard/reducedmotion/mobileusable. No syntheticpercentage or inventedconversation; display committedpublicrationale, not hiddenchainofthought. Pause/cancelresearch leaves brokerprotection alone.

See LIVE_DISCUSSION_UI_RESEARCH.md.

## 14. Harness² inside the agents' working process

Integrate an agent-invoked improvement workflow, not arbitrary live self-modification.

A room participant can propose a prompt/skill/retrieval change and call experiment.propose. A separate disposable research experiment runs baseline/candidate probes, evaluates groundedtaskresults and composes a candidate. Proposed changes, probe results and rejection reasons appear in the room/UI.

Agents use the currently APPROVED immutable harness during ordinaryresearch. They can initiate/review experiments, but cannot promote their own changes. Development -> held-outtemporalreplay -> shadow -> manualpromotion -> rollbackpointer.

Freeze risk/permissions/budgets/executioncode/networkguards/productionconfig. No broker secrets or production writable mounts. UpstreamHarness² defaults disableCodexsandbox/unrestrictnetwork; replace those with isolatedexecution. Its fixed weights process is harnessimprovement, not model training.

A customKepler task/evaluator is required. LocalResponses/executor compatibility remains a realgate. Reject citationfabrication/authorityviolations regardlessscore. Do not promote on selfpraise oronePnLbacktest.

## 15. Acceptance and delivery order

P0 BEFORE ANY DESTRUCTIVE TEST: configuration precedence audit, isolatedtarget/refusalguard, preserveoperatorstate; local hardware/runtime inventory and non-mutating baseline checks.
P1 Shared room/message/job/evidence contracts, transactional outbox, lease fencing, parent budgets and read-only tool/skill gateway.
P2 Model pair validation and Codex App Server conformance decision. Selectone room coordinator using mandatory gates.
P3 Feed/news correctness, GIFT/STIservice, TimesFMtyped tool/cache/cutoff; enable diagnostic UI, no new decision authority.
P4 Adaptive collaborative rooms, scheduled/event triggers, graph/artifact/browser research skills, ForecastAnalyst and intelligent advisory fast policy.
P5 Real-time Research Desk, evidence/history/reconnect, optional Pixel office adapter after the transcript works.
P6 Agent-invoked Harness² experiments and optionald1/Flint challengers; manual promotion only.

Required tests:
- Production-like graph target refused BEFOREdelete, correcteffectiveenv/YAMLprecedence, namedDBsession.
- Crash/lease takeover/cancel/idempotentmessages/globalbudget enforcement; no fake recoveredresult.
- Graph empty/stale/unavailable and unsupportedhistoricalasof; boundedtraversal and permissions.
- Browser/skill actualexecution, path/redirect escapes, blockedpage/timeouts and processcleanup.
- Diversemodels under simultaneousload, malformedJSON, endpointfailure, groundedfacts and abstention.
- TimesFM cachecrosscutoff/source/model changes; invalidbars; quantileshape; baselines; no fakebounds.
- Market calendars/delay/roll; late-arriving/revisednews; point-in-time replay without futureevidence.
- UIconcurrentagents, durablemessages, reconnect/cursor, evidencecitations andaccessibility.
- Execution/protection/risk remain correct with allresearch components unavailable, and without awaiting anyLLM/browser under mutationlock.
- Candidateimprovement rejected/promoted/rolledback independently.

This review adds no new benchmark/test/inference run beyond the operator-reported findings. Record passed/failed/skipped/unrun and actual source entitlement distinctly.

## 16. Local Codex starter

Read README.md, SPIKE_REVIEW.md, both completed findings reports and PRE_IMPLEMENTATION_AUDIT.md. Do not rerun the old spike or closed follow-up queue. The next bounded task is G0/G1 in NEXT_VALIDATION_PLAN.md: export sanitized existing evidence and audit evaluator/grounding failures, without new inference. Preserve the original results and private artifacts. Any later inference experiment needs a fresh declared scope and budget. Do not run destructive graph fixtures, change product agents/schemas, expose credentials or promote a model/coordinator. Keep Zerodha and manual LIVE-entry approval; report evidence and the smallest justified next step.
