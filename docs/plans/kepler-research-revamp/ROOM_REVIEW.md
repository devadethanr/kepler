# Review of the activated local research room

Reviewed 1 November 2026 at `aebd42d164e48882284c30e3d995eb562d212162`, using three Terra reviews for lifecycle/storage, grounding/evaluation, and tools/UI, followed by independent cloud checks and targeted reproductions.

**Decision:** keep the installed Codex App Server + local adapter and measured model pair. This is a usable personal research workspace with unfinished conversation and answer-quality behavior. The next work is [NEXT_PHASE_IMPLEMENTATION.md](NEXT_PHASE_IMPLEMENTATION.md); local Codex can use [NEXT_PHASE_HANDOFF.md](NEXT_PHASE_HANDOFF.md).

## What was independently checked

| Check | Cloud result | Boundary |
|---|---|---|
| Existing research-room backend tests | 22 passed, 8 skipped | Five disposable-Postgres checks and three disposable-graph DNS/address checks were not run here. The destructive graph integration directory was not collected. |
| Frontend tests / TypeScript / build | 16 passed; typecheck and build passed | Existing large KnowledgeScreen bundle warning remains. This was not a new browser visit to the user's PC. |
| Ruff | Passed on all 27 Python files changed by the implementation | No application source was changed by this review. |
| Committed evidence identity | 14 review files, 5 activation files and 6 activation source hashes matched their manifests | Hashes establish identity against the manifests, not independent replay of the local GPU/UI observations. |
| Grounding results | Recomputed all 120 saved rows; declared gold-policy outputs and saved scores matched | This reuses the declared evaluator. It does not independently establish that every task description or label is unambiguous. |
| Targeted reproductions | Actual Store/Gateway/outcome helpers exercised with temporary SQLite and dummy artifacts | No model request, live browser, Postgres/graph service, broker call or user-PC operation. |

Reproducible source, results and commands: [cloud evidence manifest](evidence/cloud-review-aebd42d/manifest.json), [validation](evidence/cloud-review-aebd42d/validation.json), [probes](evidence/cloud-review-aebd42d/probe-results.json), [saved-score recalculation](evidence/cloud-review-aebd42d/grounding-recalculation.json).

The local report's **89 backend/graph tests and actual UI/model/browser/cancel/API-restart runs** remain operator-reported results supported by the committed summaries. They were not rerun on this cloud machine. The report's active cancellation measured about 6.94 seconds with two model calls; that is not evidence for cancellation during a slow browser fetch.

## What the implementation delivers

- Two model-specific Codex threads independently investigate, then receive addressed peer messages. Subsequent turns depend on those messages; this is more than a fixed thesis/rebuttal script. Each turn publishes one public message and can retrieve evidence.
- Existing Postgres cognition tables persist room state, immutable events, tool intents/results and usage/lease records. The normal dashboard reaches the host API through the owner-only Unix socket and existing authentication.
- Actual current-graph lookup/one-hop neighbors, scoped document search/read, skill discovery/loading and isolated public-HTML browser reading are wired. A missing project graph result remains empty.
- The Research Desk shows actual messages, excerpts, tool events and saved history. Interpretation is visibly distinct from exact excerpt verification.
- The graph environment-precedence defect and destructive-test guard are repaired in the normal disposable launcher. Retain the independent endpoint, named database and network checks.

Recovery is **saved-history replay plus a linked fresh attempt after worker interruption**, not continuation of the same live Codex threads after a worker crash. The normal activation restarted the host API, not the mid-turn worker. Browser reading currently fetches approved public HTML and inspects it in a networkless DOM; interactive authenticated navigation, external page resources and general web search are not delivered by that reader. TimesFM, Scrapling, GIFT/STI and scheduled research-room triggers are not in the current room tool registry.

## User follow-up: Research Desk is not loading

The user subsequently reported that the Research Desk view is not loading. It is an intended current feature, not a future UI milestone. The exact failing origin, console error and API response have not been observed in cloud. Add local diagnosis/restoration as task 0 in the next phase. Inspect the first render failure as well as the proxy/services; `crypto.randomUUID()` is called unguarded on mount and can be unavailable on some non-localhost HTTP origins. That is one candidate to check, not a confirmed root cause. Existing compile/API/event tests do not cover this actual browser failure.

## Findings to fix next

P1 means work to do first in the next personal-workspace iteration, not a separate commercial deployment process.

| ID / priority | Finding and evidence | Concrete next change |
|---|---|---|
| R1 / P1 | **An objection can end the room before being delivered.** [worker.py](../../../swingtradev3/research_room/worker.py#L130) checks the outcome before dispatching pending mail. Its `all(delivered[r] > 0)` condition proves only some earlier mail was delivered. The actual outcome helper returns disagreement while the latest objection is still pending in the probe. | Track which message/objection was delivered and answered. Offer the recipient a bounded response opportunity before concluding a disagreement, unless cancellation or a real limit intervenes. Persist the causal state needed for honest history. |
| R2 / P1 | **Queued cancel has no terminal event.** [store.py](../../../swingtradev3/research_room/store.py#L254) sets `cancelled` but emits only `room.cancel_requested`, without `completed_at`. The SQLite probe reproduces it. [ResearchDeskScreen.tsx](../../../swingtradev3-dashboard/src/screens/ResearchDeskScreen.tsx#L65) closes SSE only on `room.finished`; the terminal stream otherwise reconnects. | Commit queued cancellation and one terminal event atomically. Make the UI also recognize terminal room state on initial load/reconnect. Keep repeated cancels idempotent. |
| R3 / P1 | **A visible symlink can expose a hidden in-root path.** [tools.py](../../../swingtradev3/research_room/tools.py#L116) resolves the requested path before its no-follow walk. A visible `.md` link to `.hidden/dummy.md` was actually read by the probe. Outside-root links remain refused; this is not an arbitrary filesystem escape. | Walk the original relative path with no-follow checks, validate every component and the final actual file policy, and preserve the configured root boundary. Test with dummy hidden files only. |
| R4 / P1 | **Create/retry idempotency misses parent identity and concurrent insert recovery.** [store.py](../../../swingtradev3/research_room/store.py#L39) checks only question/target and performs check-then-insert. The probe supplies an existing ordinary request ID for a linked retry and gets the old unlinked room back. [retry route](../../../swingtradev3/api/routes/research.py#L136) passes through that behavior. The concurrent insert race is identified by code inspection, not reproduced on Postgres here. | Include the immutable retry-parent identity in request matching. Handle concurrent unique-key insertion atomically and return the same compatible attempt or explicit conflict, including from retry. Verify the race on disposable Postgres. |
| R5 / P2 | **Limits/failures can obscure real outcomes.** [worker.py](../../../swingtradev3/research_room/worker.py#L130) breaks at the message cap before checking the last published outcome. Its initial executor waits for the other participant after an error, and exceptions are awaited in role order. Expired leases leave old active counters in [store.py](../../../swingtradev3/research_room/store.py#L182). These are control-flow findings. | Evaluate a causally valid final result at the cap; otherwise record an explicit limit reason. On a participant failure stop/interrupt peers promptly. Display stale/in-flight work as unknown or reconciled, not as healthy activity; do not invent usage. |
| R6 / P2 | **Browser fetch is outside the advertised whole-job deadline/cancel loop.** [browser.py](../../../swingtradev3/research_room/browser.py#L77) fetches before creating its 100-second deadline at line 151. DNS, redirect and response-read stages do not receive the shared cancellation/deadline. | Start one monotonic deadline before fetch, carry remaining time through resolution/redirect/read/DOM phases and stop owned work on cancel. Test a slow fetch, not only model cancellation. |
| R7 / P1 quality | **Real quotes do not establish narrative support.** [grounding.py](../../../swingtradev3/research_room/grounding.py#L41) checks source/target/span metadata, not whether the message follows from it. The committed normal-room message at sequence 55 claims broker/runtime separation but cites a paragraph saying the first room is connected. Its UI label accurately says interpretation is not fact-checked. | Introduce atomic claim/evidence records, deterministic metadata checks and explicit unassessed/inference/insufficient states. Evaluate support separately from excerpt validity; do not present another model's vote as truth verification. |
| R8 / P2 usability | **Bounded retrieval/history needs visible limits.** [tools.py](../../../swingtradev3/research_room/tools.py#L320) caps scan/results and returns a search excerpt without full completeness/omission metadata; it already labels the result as a search excerpt. [store.py](../../../swingtradev3/research_room/store.py#L145) exposes only the newest 30 rooms and the UI has no older-history browser. | Return explicit scope/offset/truncation/scan limits, retain relevant contradictions and provide a bounded way to retrieve more. Add room-list pagination or a direct room-ID lookup in the desk. |

## Grounding: what the saved data actually says

| Model/lane | Shared register A | Scoped packet B | Schema |
|---|---|---|---|
| Gemma / analyst | 5/30 exact | 4/30 exact | 30/30 per arm |
| Qwen / skeptic | 5/30 exact | 9/30 exact | 30/30 per arm |

The earlier 2/30 result remains its own frozen benchmark. The fresh comparison failed its declared 27/30 threshold. Both arms use the same 30 templated records in the same order, and the run calls chat completions directly; it is not an end-to-end evaluation of the room's tool-driven narrative research.

The analyst emitted `conflict` in all 30 cases in each arm and copied a record ID into `entity` in 22/30 scoped cases. The saved schema permits multiple statuses and the other lane uses them, so a hardcoded status/transport defect is not established. The prompt's blanket “keep its contradictions” wording and underspecified `record_id` versus `entity` are plausible representation problems. Greedy/schema/template behavior and ordering effects are also unisolated. Diagnose narrowly; do not declare a root cause from these correlations or claim the model is universally incapable.

The saved labels/scores remain unchanged. The metric “accepted fabrication = 0” follows from acceptance being exact match to synthetic gold in that evaluator. It is not a measurement of unsupported narrative claims accepted by the actual publication path. The earlier specific cross-record citation counts are supported by the supplied IDs, but future scoring must distinguish wrong-record IDs from nonexistent IDs.

Compute source-known date/freshness/cutoff rules in code, with explicit unknown values. Do not use rules to invent prose entailment, detect every contradiction or identify an event without evidence. The models should interpret a compact, explicit evidence contract and expose uncertainty; the evaluator must measure that behavior independently.

## Next phase decision

Implement conversation/lifecycle/tool-boundary fixes and a compact claim/evidence contract, with real UI state and focused tests. Carry out one bounded quality evaluation after the cases and rubric are frozen. This work proceeds on the existing Codex implementation; it does not require another framework or GPU-engine spike.

Then connect useful fresh sources: official filings/news/RSS and bounded extraction, GIFT/Singapore context with actual data entitlement/quality, and an informational TimesFM tool after its input/cache repairs. Scheduled/event-driven autonomous rooms follow the corrected scheduler and basic source-quality behavior. Keep live-entry approval and broker protection independent throughout.
