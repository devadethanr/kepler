# Research sources and evidence limits

Checked 31 October 2026. Repository source was read from origin/main at 8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0. The application checkout was not switched or edited. Six parallel research/audit roles covered markets/news, local models, frameworks/learning, browser extraction, backend and UI.

No local-PC GPU benchmark, authenticated GIFT feed request, new application test suite, live order or model training was performed. Public model metadata, documents, instrument masters and selected RSS feeds were inspected. Report model memory figures are artifact sizes, not observed GPU allocation.

## Repository anchors

- Current baseline: https://github.com/devadethanr/kepler/commit/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0
- Slow-brain bounded workflow: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/cognition/slow_brain/orchestrator.py
- Single-endpoint cognition routing: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/cognition/llm_client.py
- Scheduler jobs, including GIFT print-only check: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/api/tasks/scheduler.py
- Existing news: https://github.com/devadethanr/kepler/tree/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/data/news
- Research route/in-memory sessions: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/api/routes/scan.py
- Operator UI: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3-dashboard/src/screens/TelemetryScreen.tsx
- Durable SSE: https://github.com/devadethanr/kepler/blob/8fb50888c47a8b4f62e0917dd0475ee5dfaa6fb0/swingtradev3/api/routes/sse.py

## Selected models and runtime

- Official Qwen3.5-4B: https://huggingface.co/Qwen/Qwen3.5-4B
- Community Q4 artifact: https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
- Official Qwen3.5-9B: https://huggingface.co/Qwen/Qwen3.5-9B
- Community Q5 artifact: https://huggingface.co/unsloth/Qwen3.5-9B-GGUF
- Google Gemma4 12B official QAT challenger: https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf
- Liquid LFM3-1.7B: https://huggingface.co/LiquidAI/LFM3-1.7B
- Liquid licence: https://huggingface.co/LiquidAI/LFM3-1.7B/blob/main/LICENSE
- llama.cpp runtime release: https://github.com/ggml-org/llama.cpp/releases/tag/v0.8.0
- Pinned runtime architecture support: https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/src/llama-arch.cpp
- Pinned server/schema/reasoning documentation: https://github.com/ggml-org/llama.cpp/blob/8642541b255bfb5dc39cd351a178be09013a55d6/tools/server/README.md
- NVIDIA hardware capabilities: https://developer.nvidia.com/cuda-gpus

Pinned model/revision/file/SHA256 values are recorded in MODEL_CANDIDATES.json. Community quantizations are labelled as such. Parameter counts and vendor benchmark scores are not memory or latency measurements on the user's PC.

## Flint

- Official card: https://huggingface.co/RecursiveSI/flint/blob/2a247be0c0aec895ccb0ac7ca92229ec6df37288/README.md
- Config: https://huggingface.co/RecursiveSI/flint/blob/2a247be0c0aec895ccb0ac7ca92229ec6df37288/config.json
- Official NVFP4: https://huggingface.co/RecursiveSI/flint-nvfp4-gguf
- Community low-bit alternatives: https://huggingface.co/unsloth/flint-GGUF
- NVIDIA runtime guide: https://docs.recursive.com/local/nvidia
- BF16 SGLang kit: https://huggingface.co/RecursiveSI/flint/blob/2a247be0c0aec895ccb0ac7ca92229ec6df37288/sglang/README.md
- Rec engine: https://github.com/recursive-oss/rec

Verified:39.8Btotal,~2.5Bactive,Apache2.0,~80GBBF16 and22.86GBofficialNVFP4. Aggressive community3bit file14.54GBmay allow a shorter-context16GBexperiment, not an established official-quality fit. Rec's published requirements are Apple Silicon48GB, not this dual-NVIDIA system. Coding scores do not prove financial decision quality.

## Primary runtime and Harness²

- ADK: https://github.com/google/adk-python
- Stable release inspected: https://github.com/google/adk-python/releases/tag/v2.13.0
- Workflow: https://github.com/google/adk-python/blob/v2.13.0/docs/guides/workflow/workflow/index.md
- Database sessions: https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/sessions/database_session_service.py
- Invocation-scoped run budgets: https://github.com/google/adk-python/blob/v2.13.0/docs/guides/agents/run_config/index.md
- Harness²: https://github.com/google-research/harness2
- Pinned README: https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/README.md
- Paper: https://arxiv.org/abs/2610.14224
- Provider/setup constraints: https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/docs/SETUP.md
- Persistent improvement library: https://github.com/google-research/harness2/blob/1cfe254e8d25b15f37048c3730134686abe60335/harness2/core/library.py

Harness² README explicitly keeps weights fixed, supports OpenCode/Codex executors, warns executor networking is unrestricted/Codex sandbox disabled, and says it is not an officially supported Google product. Do not copy those benchmark execution permissions into live Kepler.

Alternatives considered:
- LangGraph: https://github.com/langchain-ai/langgraph
- Deep Agents: https://github.com/langchain-ai/deepagents
- OpenAI Agents SDK: https://github.com/openai/openai-agents-python
- Codex Apache2.0: https://github.com/openai/codex/blob/main/LICENSE
- OpenHands SDK: https://github.com/OpenHands/software-agent-sdk
- Claude wrapper: https://github.com/anthropics/claude-agent-sdk-python
- Actual Claude Code licence: https://github.com/anthropics/claude-code/blob/main/LICENSE.md

The Claude SDK wrapper's licence does not make Claude Code itself open source. MCP/A2A are interfaces, not a self-learning algorithm or durable job scheduler.

## Browser tools and extraction

- Agent-browser Apache2.0: https://github.com/vercel-labs/agent-browser
- Scrapling BSD-3-Clause: https://github.com/D4Vinci/Scrapling
- Crawl4AI Apache2.0: https://github.com/unclecode/crawl4ai
- Browser Use MIT: https://github.com/browser-use/browser-use
- Browser Use local-model caveats: https://docs.browser-use.com/open-source/supported-models
- Playwright contexts: https://playwright.dev/python/docs/browser-contexts
- Playwright authentication-state caveats: https://playwright.dev/python/docs/auth
- Scrapling adaptive-list behavior: https://github.com/D4Vinci/Scrapling/issues/259
- Crawl4AI process lifecycle report: https://github.com/unclecode/crawl4ai/issues/2202
- Agent-browser tab binding: https://github.com/vercel-labs/agent-browser/issues/1530
- Browser Use navigation-control report: https://github.com/browser-use/browser-use/issues/5815

Issue reports are scoped evidence, not platform-wide failure statistics. Agent-browser restrictions are opt-in; its built-in allowlist cannot be assumed compatible with persistent profiles/CDP/state restore. Smaller local-model API compatibility does not establish browser-task success.

## GIFT and Singapore

- Public Kite instrument master: https://api.kite.trade/instruments
- Public Upstox global master: https://assets.upstox.com/market-quote/instruments/exchange/global.json.gz
- Upstox instruments docs: https://upstox.com/developer/api-documentation/instruments/
- Upstox Analytics Token: https://upstox.com/developer/api-documentation/analytics-token
- NSE IX trading sessions: https://www.nseix.com/markets/trading/tradinghoursnew
- Readable content endpoint: https://www.nseix.com/api/contents/page?url=/markets/trading/tradinghoursnew
- NSE IX holiday calendar: https://www.nseix.com/markets/trading/tradingholidaysnew
- NSE IX products: https://www.nseix.com/markets/about-our-products/equity-derivatives-updated
- NSE IX data licensing/products: https://www.nseix.com/markets/market_data/realtime_data
- Migration announcement: https://www.nseix.com/web/pressrelease/2026-04/PR_cc_03072023_1_0_20260401174548.pdf
- SGX hours: https://rulebook.sgx.com/rulebook/practice-note-821-application-market-phases-and-algorithm
- STI September2026 factsheet: https://research.ftserussell.com/Analytics/FactSheets/Home/DownloadSingleIssue?issueName=STI&IsManual=false

Kite master row:GIFTNIFTY,NSEIX,token291849atchecktime; authenticated entitlement/freshness/history were NOT verified. Resolve current IDs in implementation.

Upstox global row uses legacyGLOBAL_INDEX|SGXNIFTY for displayedGIFTNIFTY and explicitly declares120secondsdelay. This is not proof of a tradable future or an actual authenticated realtime stream.

Yahoo^STI chart probes returned data; no realtime/delay SLA was established. GIFT and STI are distinct inputs. STI's three largest banks were59.14% of the inspected factsheet, so claims of broadAsia predictive value would be unjustified.

## News sources and restrictions

Successful XML/feed parses during research:
- NSE: https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml
- SEBI: https://www.sebi.gov.in/sebirss.xml
- RBI: https://rbi.org.in/pressreleases_rss.xml
- ET Markets: https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms
- Federal Reserve: https://www.federalreserve.gov/feeds/press_all.xml
- ECB: https://www.ecb.europa.eu/rss/press.html

Source catalogs:
- https://www.nseindia.com/rss-feed
- https://www.rbi.org.in/Scripts/rss.aspx

Failed configured/guessed sources at checktime:
- PIB ViewRss returnedHTML/zeroentries despiteHTTP200.
- MoneycontrolRSS andBSE RSS requests returnedwebsite403.
- MAS guessedRSS returnedHTML/maintenance; no productionMASfeed was verified.

Optional APIs:
- Upstox news: https://upstox.com/developer/api-documentation/get-news/ (past7days,notahistoricalcorpus)
- NewsAPI: https://newsapi.org/pricing (Developer24hdelay/devtestingonly)
- GNews: https://gnews.io/pricing (Free12hdelay/noncommercial)
- Tavily: https://docs.tavily.com/documentation/api-credits (quota-baseddiscovery,notcontinuousbackbone)

HTTP200 is not content success; first-seen history is necessary for causal replay; syndicated copies are not independent corroboration. Downloading a page or an open-source scraper does not confer redistribution rights.

## Observability

- OpenTelemetryPython Apache2.0: https://github.com/open-telemetry/opentelemetry-python
- Langfuse: https://github.com/langfuse/langfuse (coreMITwithenterpriseexceptions;moreinfrastructure)
- Phoenix: https://github.com/Arize-ai/phoenix

Choose currentPostgresruns/events+OpenTelemetrycorrelationfirst. Do not addmultipletraceproducts tosolve missingrunidentities.

## Revision 2: additional sources and changes

The selected pair is now heterogeneous Gemma 4 E4B + Qwen3.5-9B, subject to measured local gates; Qwen3.5-4B remains a fallback. Earlier model research is retained as evidence, not as the current default.

- Official Gemma E4B: https://huggingface.co/google/gemma-4-E4B-it
- Official Gemma QAT GGUF: https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf
- Liquid decision model: https://huggingface.co/LiquidAI/d1-2B
- Liquid decision GGUF: https://huggingface.co/LiquidAI/d1-2B-GGUF
- TimesFM current code/documentation: https://github.com/google-research/timesfm
- Integrated TimesFM 2.5 model card: https://huggingface.co/google/timesfm-2.5-200m-pytorch
- Codex App Server pinned source: https://github.com/openai/codex/blob/67f0994b532b8740f14b5b738af7b7b2a915b1d6/codex-rs/app-server/README.md
- Codex collaboration schema: https://github.com/openai/codex/blob/67f0994b532b8740f14b5b738af7b7b2a915b1d6/codex-rs/core/src/tools/handlers/multi_agents_spec.rs
- Official agent-browser skill: https://github.com/vercel-labs/agent-browser/blob/5868f7c05020e047c00e68e4abf9253cce864f41/skills/agent-browser/SKILL.md
- Pixel Agents: https://github.com/pixel-agents-hq/pixel-agents
- Star Office licensing: https://github.com/ringhyacinth/Star-Office-UI/blob/master/LICENSE
- WorkAdventure component licensing: https://github.com/workadventure/workadventure/blob/master/play/LICENSE.txt
- AG-UI protocol: https://github.com/ag-ui-protocol/ag-ui
- CopilotKit: https://github.com/CopilotKit/CopilotKit

Read the specialist reports for exact capability and licensing boundaries. Codex's local heterogeneous-agent compatibility, browser success and model performance are not verified by documentation alone. Current TimesFM integration is 2.5; do not attribute newer TimesFM 3.0 features to it.

The old fixed-order debate proposal is replaced by an adaptive room. Harness² is now an agent-invoked research improvement workflow with isolated probes and manual version promotion. Scrapling is an approved required adapter, not a proposal to install an unrestricted crawler.

Static pre-implementation audit confirmed a destructive graph-test target risk and corrected earlier leads: LOCAL_LLM_ENABLED overrides YAML correctly; model role behavior differs by router; the legacy tool cap counts iterations, not a global tool budget. See PRE_IMPLEMENTATION_AUDIT.md before any tests.

## Initial spike update — 1 November 2026

The user supplied local GPU/toolkit output: RTX 5070 Ti 16,303 MiB (display-active, 568 MiB used in snapshot), RTX 3060 12,288 MiB (2 MiB used), driver 610.43.02, CUDA UMD 13.3 and nvcc 13.3/V13.3.73. This is user-reported capacity evidence, not a serving/model benchmark.

Runtime research used these primary sources:
- vLLM architecture list: https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md
- vLLM GGUF support/plugin caveats: https://github.com/vllm-project/vllm/blob/main/docs/features/quantization/gguf.md
- vLLM prefix caching: https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md
- vLLM CUDA/wheel installation: https://github.com/vllm-project/vllm/blob/main/docs/getting_started/installation/gpu.cuda.inc.md
- vLLM tool parsing: https://github.com/vllm-project/vllm/blob/main/docs/features/tool_calling.md
- SGLang Gemma4 cookbook: https://github.com/sgl-project/sglang/blob/main/docs/cookbook/autoregressive/Google/Gemma4.mdx
- SGLang installation: https://github.com/sgl-project/sglang/blob/main/docs/docs/get-started/install.mdx
- SGLang quantization/backends: https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/quantization.mdx
- Codex App Server: https://developers.openai.com/codex/app-server/

Current main-branch support does not prove a stable release/checkpoint/kernel combination. GGUF, AWQ/GPTQ and BF16 QAT-unquantized are different artifacts. The spike must freeze actual engine and model revisions, test compatible formats and compare quality as well as speed. No local-engine compatibility or performance result was produced by the documentation task.

The spike includes vLLM first, SGLang comparison and retained llama.cpp baseline. Native isolated environments/start scripts are explicitly accepted. Local Codex must populate SPIKE_FINDINGS.md, return a copyable handback to the user and stop before product implementation.

## Completed local evidence review — 1 November 2026

- Operator-reported initial and follow-up results: [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md), [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md), [closed request queue](FOLLOW_UP_REQUESTS.md), pushed in commit `8d7ddfc`. Runtime under test was `5ebdd17`; private R/F runners/logs were not independently executed or inspected in this cloud review.
- [Current review and corrections](SPIKE_REVIEW.md) and [next bounded validation scope](NEXT_VALIDATION_PLAN.md) supersede pre-spike unmeasured/NOT_RUN assumptions. Browser and authorized adapter fixtures passed; record grounding and production readiness remain unqualified.
- [Pinned TimesFM return statement](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py#L473-L513) and [quantile configuration](https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm/timesfm_2p5/timesfm_2p5_base.py#L90-L95): API point is channel 5 of the full forecast array, not channel 0. Installed library 3.0.2 does not change the checkpoint identity from TimesFM 2.5. Ordering fixes are not calibration.

## User implementation decision — 1 November 2026

The user selected Codex App Server + the tested local adapter for their personal workspace after the completed follow-ups. [CODEX_IMPLEMENTATION.md](CODEX_IMPLEMENTATION.md) is the active work order. Earlier experimental/undecided language describes the historical spike, not the current runtime choice. Grounding and integration checks continue as implementation work; no repeat framework-selection stage is required.
