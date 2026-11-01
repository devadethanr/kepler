# Review after room repairs and seven prompt rounds

Reviewed 2 November 2026, Asia/Kolkata, at `feat-generic-broker@ae7d45f`. Terra reviewed lifecycle and evaluation; a smaller Luna agent checked UI/status. The root reviewer repeated safe tests, replayed saved proposals and checked official-feed reachability.

**Keep the installed Codex runtime and model pair.** The room is further along than the earlier `aebd42d` review. The next implementation is a narrow primary-source evidence service, described in [FRESH_SOURCE_IMPLEMENTATION.md](FRESH_SOURCE_IMPLEMENTATION.md) and [FRESH_SOURCE_HANDOFF.md](FRESH_SOURCE_HANDOFF.md), with one remaining terminal-reason fix. Do not restart the old room-fix handoff or add an eighth tuning round on the now-seen cases.

## Verified status

| Area | Current finding |
|---|---|
| Research Desk loading | The LAN failure was established as missing `crypto.randomUUID()` on insecure HTTP. Cryptographic fallback, error/loading states and terminal stream handling are implemented. Local reports record real loopback/LAN browser and reboot checks. |
| Earlier R1–R4 | Causal response opportunities, queued terminal cancellation, original-path/no-follow reads and parent-aware/concurrent create/retry handling are implemented. A response opportunity still does not establish a semantic answer. |
| R5 | Final-slot evaluation, failure cleanup and activity/usage reconciliation are implemented; a small termination-reason edge remains below. |
| R6 / R8 | Shared browser deadline/cancellation, visible retrieval limits/continuation and direct old-room access are implemented. Current live-tree/refetch/capture limits are disclosed. |
| R7 | Atomic claim/evidence and metadata handling are implemented. Narrative remains explicitly unassessed; general source relevance and interpretation are not solved. |
| Active prompts | The installed room still uses `research_room/codex.py:INSTRUCTIONS`. Retained candidate files were renamed without changing their bytes. Neither candidate is active. |

The native checks and restored services are supported by [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md), [REBOOT_BROWSER_CHECKS.md](REBOOT_BROWSER_CHECKS.md), [WORK_HISTORY.md](WORK_HISTORY.md) and their evidence. A worker interruption still becomes an interrupted attempt with a linked fresh retry, not automatic continuation of its old Codex threads.

## Independent cloud checks

- **55 backend tests passed, 11 skipped** because disposable Postgres/graph infrastructure was not provided here. The destructive graph integration directory was not collected. The local report's 125 guarded checks remain local results, not 125 tests rerun in cloud.
- **21 frontend tests, TypeScript, dashboard build and Ruff on 24 changed Python files passed.** The existing KnowledgeScreen bundle warning and Starlette TestClient deprecation remain. Render-unit tests are not a new visit to the user's live browser.
- All **25 phase-2 evidence files and 235 prompt-evidence files** matched their supplied manifest hashes. The four renamed prompt files match their `eda07cb` bytes.
- All **120 final confirmation proposals** were replayed through the actual `Gateway.execute`, `score_v2` and temporary SQLite, without model/network/browser calls. Every score matched the saved output. This verifies reproducibility of the declared gateway/rubric behavior, not independent truth of every gold label.

See [cloud review evidence](evidence/cloud-review-ae7d45f/manifest.json), including [validation](evidence/cloud-review-ae7d45f/validation.json) and [confirmation replay](evidence/cloud-review-ae7d45f/confirmation-recalculation.json). No application source or user-PC service was changed by this review.

## What the final scores mean

| Final confirmation, 30 cases per arm | Gemma / analyst | Qwen / skeptic |
|---|---:|---:|
| Matched control fully correct | 20/30 | 21/30 |
| Retained candidate fully correct | **25/30** | **24/30** |
| Candidate support proposal matches gold | 29/30 | 28/30 |
| Candidate relevant-span field correct | 25/30 | 25/30 |
| Fully correct positive cases | 10/10 | 9/10 |
| Candidate accepted unsupported support | 0/30 | 0/30 |
| Frozen 27/30 objective | Failed | Failed |

These are matched improvements on this assessment. They are not percentages of correct financial research. The assessment supplies the claim and evidence, permits one publication request and forbids retrieval. Strict correctness includes exact text/kind/support/span/event fields and actual publication acceptance. Positive-case correctness also includes all those fields, not just the support label.

The candidate changes **both participant policy and the assessment task instructions** relative to its control. The gain cannot be assigned to policy alone or carried over to live-room research. In particular the `contract-*.md` task asks for a supplied claim copied into a `position=question` publication; it must not replace an open-ended discussion prompt.

Seven development rounds reused development cases. An earlier held-out set was subsequently inspected and became seen; opaque cases include derived/recovered observations. The final confirmation was separately authored/reviewed with selection frozen before unsealing, according to the documented process. It remains a small functional set. Preserve all now-seen sets as regression history; do not tune on them and call them untouched again.

Zero accepted unsupported proposals in this finite confirmation does not guarantee safety or semantic correctness elsewhere. Earlier accepted unsupported proposals, identifier sensitivity and source-selection failures remain in the evidence. Keep the candidates inactive as reported; promotion would require an explicit later decision and an assessment of the participant policy in actual research, not installation of the evaluation task.

Accounting records **1,232 isolated requests plus 55 native admissions**, separate from the earlier 112-request phase. The original SQLite audit includes 12 interrupted-run calls absent from the result prefix; recovered repeats are not independent cases. Actual usage has unknown entries; conservative reservations are not consumed tokens. No new model request was made for this review.

## Remaining small room issue

In [worker.py](../../../swingtradev3/research_room/worker.py#L193), `no_pending_mail` is the default terminal reason. A tool can be denied by `Budget` while the model then finishes without a publication. If no mail remains, the normal `if not mail` exit does not inspect the denial; `last_denial` is only used in the exception path. The room may therefore describe a tool-budget stop as no pending mail. This is source inspection, not a reproduced native model run; the budget still denies the action.

Add a focused regression and typed terminal-cause handling before or alongside source integration. Do not overwrite a valid outcome or unrelated failure with an old global denial string; inspect the relevant cause/current state. This is a small fix, not a reason to repeat the whole room phase.

## Primary-source readiness check

Three unauthenticated, bounded requests from cloud on this review date used the existing configured URLs and inherited proxy/TLS. [Diagnostics](evidence/cloud-review-ae7d45f/source-reachability.json) contain no raw feed body or account data.

| Source | Single observed response | Meaning for implementation |
|---|---|---|
| NSE announcements RSS | HTTP 200, valid RSS, **zero items** | Reachable-empty snapshot. It is not evidence that no company announcements occurred, nor proof that every NSE endpoint is unusable. |
| SEBI RSS | HTTP 200, valid RSS, **30 items** | Sample dates were `30 Oct, 2026 +0530`. The actual current date helper returned `None` for these strings. Add a source-aware date/precision rule, not a fabricated publication instant. |
| RBI press-release RSS | HTTP 200, valid RSS, **10 items** | Sample timezone-less times parse under the current IST convention. Verify that provider convention and preserve raw time/zone basis. |

This is reachability/format evidence, not freshness, completeness, licence/retention clearance or a successful user-PC ingestion run. The latest samples were dated 30 October; weekend or publication cadence must not be confused with outage or a real-time feed.

## What to build next

Reuse `data/news/feed_providers.py`, `core.py`, `constants.py`, the existing `NewsRepository`/tables and bounded room tools. Important reuse boundaries:

- Current source items can be upserted/overwritten. Preserve first-seen time and immutable content revisions before claiming historical as-of retrieval.
- Feed-level caps can stop before later providers are read; expose per-source coverage instead of claiming an exhaustive search.
- The current builder can label text-extracted tickers “verified” for a structured source type. Do not inherit that as authoritative issuer identity. Keep explicit provider identifiers, alias mappings, text mentions and ambiguity separate.
- The configured official-feed group also contains broker blog content. It is not interchangeable with an exchange filing or regulator release. Heuristic confidence values are not calibrated truth probabilities.
- Ingestion currently has persistence/graph side effects. Model research tools must read controlled snapshots; they must not acquire arbitrary graph writes or account access by importing an aggregator.

Build one useful source-backed research task and show its actual provenance in the existing desk. Use the installed participant policy in both baseline and evidence-enriched comparisons to isolate the input change. GIFT/Singapore, the repaired informational TimesFM tool, scheduled rooms and Harness² remain subsequent capabilities. A rough implementation-planning estimate is now **40–45% complete**; this is not a measured research-accuracy score or remaining-time estimate.
