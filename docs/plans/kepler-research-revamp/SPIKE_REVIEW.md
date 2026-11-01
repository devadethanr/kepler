# Review of completed spike and follow-ups

Reviewed 1 November 2026 against pushed commit 8d7ddfc4f66603feb89dae83eb569a30af252163. Runtime code under test was 5ebdd171cf3dc3862e1b7a1dd17427ad626471a3. The reports and tracked runtime snapshots were committed later; do not label the reporting commit as the tested executable revision.

Read [SPIKE_FINDINGS.md](SPIKE_FINDINGS.md), [FOLLOW_UP_FINDINGS.md](FOLLOW_UP_FINDINGS.md) and [FOLLOW_UP_REQUESTS.md](FOLLOW_UP_REQUESTS.md) together. The initial spike and all three authorized isolated follow-up requests are complete. A completed request can have failed quality gates. Do not restart the old queue or reuse expired budgets unchanged.

## Implementation decision after user clarification

The user selected **Codex App Server with the tested local adapter** for their personal Kepler workspace. See [CODEX_IMPLEMENTATION.md](CODEX_IMPLEMENTATION.md). The results below remain unchanged evidence; the working Codex path is now the implementation choice, not a parked experiment. Grounding, lifecycle and resource checks belong to that implementation rather than a separate generic production-approval stage.

## Evidence boundary

This review read all six requested documents, inspected the pushed diff and checked the relevant pinned upstream TimesFM source. It did NOT rerun the user's GPU experiments or execute the private prototype. The R/F runners, requests, fixtures, scorer, bridge and logs live on the local PC and are not in the pushed tree or this cloud workspace.

The local measurements are accepted as the operator's reported findings, with their stated limitations. Independent inspection of the exact evaluator and bridge requires a small sanitized export; no need to upload every raw log, licensed dataset or model artifact. No hidden assumption that missing evidence means a reported test was not performed.

## 1. Current readiness matrix

| Area | What the submitted evidence supports | What it does not establish | Decision |
|---|---|---|---|
| Safe execution of experiments | Reported preservation of seven production container identities, working files, driver, cleanup and no destructive graph tests | Production graph-test isolation is not repaired | Keep the graph-test blocker; no broad destructive test command |
| llama.cpp preferred pair | Default placement ran both models; concurrent E2E p95 1.385 s Gemma /1.087 s Qwen, n=30 each | Default retains CPU embeddings; strict full-GPU Gemma timed out at n=1 and no valid strict dual p95 exists | Use this exact measured arm as the initial implementation baseline; improve grounding |
| vLLM/SGLang | Their measured model/artifact/config combinations did not yield a passing preferred-pair replacement | A universal engine ranking or claim that every compatible configuration fails | Do not repeat the matrix unchanged or force migration to satisfy a framework preference |
| Model grounding | JSON syntax passed in all completed profiles; shared-register all-field/citation correctness was 2/30 per preferred lane, baseline 3/30 | General evidence selection or financial competence; scripted room success does not resolve this | Primary quality blocker; audit scorer and per-field errors before model shopping |
| Browser/skills | Actual pinned skill discovery/load and isolated browser navigation/extraction/denials passed | Live public news research, authentication or production freshness | Fixture blocker closed; keep it a scoped capability result |
| Codex runtime | Both models passed bounded App Server turns through the tested local adapter with flat approved tools | Unmodified native compatibility or native heterogeneous child spawning | Selected for personal Kepler implementation; reuse the adapter and external-thread design |
| Collaboration | Codex and isolated ADK both completed the same predeclared evidence challenge/revision/abstention fixture | Spontaneous adaptive research, independent corroboration, or a coordinator speed winner | Use Codex as selected by the user; this fixture does not prove a universal quality/speed winner |
| TimesFM contracts | Real CPU model worked through the disposable wrapper; 36/36 wrapper checks and six product-defect reproductions reported | Product cache correctness, initialization/concurrency recovery or predictive value | Repair product contract only through a later reviewed safety slice; informational use only |
| TimesFM market quality | Historical SP500 point MAE had no demonstrated baseline advantage; nominal 80% coverage 64.5% | NSE/GIFT applicability, point-in-time validation, calibration or profitable decisions | No score, sizing, stop/target or risk influence |
| GIFT/news | Master identity exists; RSS parsing partially worked | Authenticated GIFT quotes/history/socket; current source timestamps/freshness | Saved-session 403 and parser issues remain prerequisites, not evidence of broker incapability |

## 2. Model/runtime decisions

Do not discard the useful latency result, and do not mistake it for model quality. A very fast valid JSON response can select the wrong record or cite another record's evidence.

The default placement's CPU parameter buffers are a documented property, not automatically a deployment failure. For this application, measured correctness, end-to-end latency, recovery and host/GPU headroom matter more than an 'all tensors on GPU' label. Keep the strict-placement failures and measure any future placement change separately. No conclusion that all full-GPU configurations are slow follows from one long prompt timing out.

The host has about 16 GiB RAM while TimesFM CPU RSS was about 2.28 GiB. Combined models, browser, TimesFM and existing services need a representative sustained resource check before deployment. Do not add RSS values naively or claim simultaneous peak capacity from separate tests; retain free/available RAM, swap, GPU headroom and latency observations together.

The initial optimized trials used different artifacts, quantization, runtimes, flags and capacity floors. Their results cannot isolate engine speed. Root cause of the vLLM hybrid-readiness stall and SGLang generation disconnect remains unknown; do not invent a compiler or memory explanation.

## 3. Codex: what now passes

The follow-up request explicitly authorized isolated compatibility fixes. The Responses-to-Chat bridge was authorized for these experiments; it is not an unauthorized deviation from the original spike.

The working configuration:
- Disables native multi-agent, shell, goals and sleep features.
- Uses flat allowlisted dynamic functions; filters ungranted built-ins.
- Reorders/merges the supported system/developer prefix and preserves user/tool evidence roles.
- Implements the tested text/function Responses subset.
- Uses actual streamed model output and executed tool results, with checked IDs/events.
- Coordinates separate top-level Codex threads under an external parent ledger.
- Uses default llama.cpp placement, context 32768 and ordinary generation cap 512 for this functional arm.

The implementation is Codex App Server with the tested local adapter and externally coordinated threads. Native heterogeneous spawn/provider inheritance remains unproven and is not required for this design. Do not describe this as unmodified native multi-agent support.

The reported stream, tool replay/ownership, interruption, crash/recovery and budget denials are useful fixture evidence. While integrating, inspect the working adapter source/schema and preserve its error, cancellation and accounting behavior. Flattening roles and protocol subsets must remain explicit; do not claim a complete OpenAI-compatible API.

The matched room's 10 calls used 327680 conservative reserved tokens (32768 per call), not demonstrated actual consumption. Its 393216-token fixture cap is different from the planned local room budget. Reconcile actual usage versus conservative admission and reclaim/unknown-usage behavior when setting useful local room limits.

Codex 6.69 s versus ADK 10.95 s includes different startup/import boundaries and n=1. It is not a speed comparison. Both passed a controlled capability fixture; neither is yet a demonstrated superior research coordinator.

## 4. TimesFM correction and decision

Our original audit conflated the model card's channel 0 mean description with the separately returned point forecast. Corrected: the pinned PyTorch implementation returns full_forecast[...,5] as its first API result; the full array contains configured quantile channels 1–9. Keep the returned point and explicit channel mapping. Do not substitute channel 0 or assign a stronger statistic/calibration interpretation than the pinned implementation supports.

Pinned code:
- https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm/timesfm_2p5/timesfm_2p5_torch.py#L473-L513
- https://github.com/google-research/timesfm/blob/e51928e27119cb17bebc005be2696b75e0a9e688/src/timesfm/timesfm_2p5/timesfm_2p5_base.py#L90-L95

Reported tested profile: TimesFM 2.5 200M checkpoint 1d952420fba87f3c6dee4f240de0f1a0fbc790e3, installed library 3.0.2, source inspected at e51928e27119cb17bebc005be2696b75e0a9e688, CPU, 2 threads, compilation off, continuous quantiles/normalization/crossing fix enabled. Record the exact installed-package-to-source mapping in the export; a source revision and package version alone do not prove identical installed bytes.

Crossing correction orders channels; it does not calibrate them. The historical sample:
- TimesFM MAE 127.827, last price 127.782, drift 126.800.
- Nominal80% coverage 64.5%, supplementary dependence-aware interval 54.0–75.2%.
- Current-vintage SP500 data, 30 origins, possible pretraining overlap, not point-in-time NSE/GIFT evidence.

This shows no demonstrated point-accuracy advantage and undercoverage in this sample. It does not prove universal model inferiority. Keep TimesFM as an informational CPU tool and continue independent research if useful. No automated scoring, risk sizing, entry/stop/target or calibrated-confidence use.

The 36/36 checks validate the disposable wrapper, not the product. The six unchanged-product reproductions remain actionable defects. The poisoned-cache 95/105 example is a negative fixture, not a model forecast. No product cache or source was repaired by those experiments.

## 5. Implementation work informed by the findings

Follow [CODEX_IMPLEMENTATION.md](CODEX_IMPLEMENTATION.md). Reuse the working adapter, implement the tool-connected room and actual discussion UI, and improve grounding during that work. [NEXT_VALIDATION_PLAN.md](NEXT_VALIDATION_PLAN.md) describes the focused evaluator/evidence checks, not another runtime-selection gate.

All three follow-ups are closed. Preserve their measurements and reuse unchanged fixtures. The graph target guard is required before destructive graph tests; other adapter/UI work can proceed independently. Keep TimesFM informational and verify GIFT's actual session/data entitlement while implementing the context service. This documentation update does not claim that application code has already been changed.
