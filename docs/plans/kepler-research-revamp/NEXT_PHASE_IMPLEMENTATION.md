# Next phase: useful, grounded research on the installed room

Prepared 1 November 2026 for `feat-generic-broker@aebd42d`. Read [ROOM_REVIEW.md](ROOM_REVIEW.md) for findings and independently repeated checks. This plan extends the user's installed personal workspace. Codex App Server + the tested local adapter is selected and stays in place.

## Scope and result

The first milestone delivered a working local room. This phase makes its discussion, terminal state and evidence handling more useful and dependable. It does not rebuild the harness, repeat the framework matrix or wait for a new generic deployment approval. Existing broker services and manual live-entry approval retain their authority.

Restore the reported UI loading failure first, then work in three small slices. A and offline B can proceed independently; run integrated model checks after their relevant paths are connected. Preserve the user's five uncommitted runtime-state files and any newer local work. Commit source/docs, not changing account/runtime state.

## 0 — restore the intended Research Desk screen first

After the `aebd42d` review, the user reported that Research Desk is not loading. This screen is intended to work now at :8502, with question entry, saved rooms, actual conversation and evidence/tool events. The optional office/animation view is later work. Treat the current loading problem as an implementation issue, not a deferred UI feature.

Reproduce the user's actual browser origin and identify the first render/network error. Check lazy-chunk/tab loading, initial `crypto.randomUUID()` calls, secure-context support, the dashboard `/api/research` proxy, API/socket/service readiness, authentication status and response-schema parsing. The unguarded UUID initialization in ResearchDeskScreen can fail on some non-localhost HTTP origins; there is not yet evidence that this is the user's cause. Preserve valid UUID/idempotency semantics when handling feature availability.

The component must still render its title/form and clear loading/empty/error or unavailable states when APIs/models are unavailable; a blank screen is not acceptable. Add a suitable error boundary/retry path and focused mount/interaction coverage for the demonstrated failure. Keep authentication server-side and use a temporary test browser profile. Verify the real browser view, including the actual origin and localhost, history reload and unavailable-backend recovery. Passing TypeScript/build alone does not establish this behavior. Diagnose/start only needed research services through the existing runbook; leave broker services alone.

## A — conversation and lifecycle correctness

Targets: `research_room/worker.py`, `store.py`, `codex.py`, `api/routes/research.py`, the Research Desk and focused tests.

1. **Address the latest objection before closing.** Track pending/delivered/responded message identity, not whether each role has ever received mail. A new objection gets a bounded recipient response opportunity. A supported revision, explicit unresolved disagreement or abstention is valid; agreement is never forced. A real budget/deadline/cancel can stop earlier with its exact reason.
2. **Finish terminal transitions once.** Queued cancellation writes status, completion timestamp and `room.finished` together. Repeated cancel, cancel/finish races, and stale-owner actions do not add contradictory terminal records. The UI uses terminal state as well as events to stop reconnecting, including after reload.
3. **Respect the last allowed message.** Check for a causally valid result before applying the cap. Otherwise display “message/call/time limit reached” rather than asserting that the agents themselves concluded insufficient evidence. Keep the existing status contract where possible and add a typed termination reason.
4. **Fix request/retry identity.** Immutable identity includes question, target and linked parent. Compatible repeated requests return the same room; conflicting use returns 409. Resolve concurrent insert races on disposable Postgres. A linked retry must not silently return an unrelated ordinary room.
5. **Stop peers on failure.** Observe completed futures promptly; on an initial participant failure signal stop and interrupt both owned RPCs instead of waiting by role order. Preserve partial public history and actual failure/cancel reason.
6. **Describe recovery honestly.** History survives API restart; worker interruption currently ends the attempt and offers a linked fresh attempt. Keep this behavior unless resumable threads and their tool state are explicitly implemented and verified. Reconcile stale active counters or label them unknown; missing usage remains unknown.

Acceptance checks use concrete sequences, not merely calls mirroring the implementation:

- A valid proposal, a newly delivered objection, a response/revision, then a correct terminal reason. Assert no finalization while the latest objection is still waiting for its recipient, absent a real limit.
- Agreement and unresolved objection at the final message slot; unresolved cap exhaustion separately.
- Queued cancel/repeated cancel and cancel/finish race; exactly one terminal event, no reconnect loop after reload.
- Concurrent same-ID create and retry requests, conflicting parent/target, and preserved linked history on actual disposable Postgres.
- Analyst-first and skeptic-first failures, cancellation during initial work, and interrupted-worker recovery with no ambiguous tool replay.

## B — source contract and grounded claims

Targets: `research_room/grounding.py`, `tools.py`, prompt/publication handling, evaluation helpers and the Research Desk.

### Fix the concrete retrieval boundaries

- Open the original requested relative path using no-follow descriptor traversal. Refuse hidden/forbidden components, symlink components, special files and outside-root escapes before reading. Keep the current size/type limits; use dummy files for these regressions.
- Return selected target/entity/event identity, source IDs/URLs, source type, publication/event/fetch times, decision cutoff, and known adjustment/delay metadata. Distinguish `record_id`, `target_entity` and `event_id` explicitly. A request label alone is not proof the excerpt concerns that entity/event.
- Show what retrieval omitted: scope/filter, excerpt offsets, truncation, scan/result cap, and incomplete/unknown completeness. Search snippets are leads; fetch the necessary surrounding source before treating an absence as evidence. Keep relevant contradictory sources.
- Use one browser-job deadline and cancellation context from the start of fetch through redirects/read/DOM processing. Retain allowlist, private-address/redirect denial, isolation, cleanup and ownership. Do not enable authenticated/personal browser access for this change.

### Keep observations separate from interpretations

Use a compact typed publication/evidence representation that fits the current output cap. A reasonable starting shape is:

```text
Message: recipient, reply_to, stance, text, claims[], unresolved_questions[]
Claim: id, text, kind [observation|inference|question],
       target_entity, event_id?, evidence_refs[],
       support_assessment [unassessed|supported|contradicted|insufficient]
EvidenceRef: evidence_id, quote_id
```

These are intended semantics, not required field spelling or a demand for a large schema. Keep public messages concise. A model's `support_assessment` is a proposal, visibly identified as such; it is not a truth-check stamp.

The gateway deterministically checks IDs, span membership, authoritative metadata, cutoff/future times and declared omissions. Compute freshness from known timestamps/configured policy, not from the model's guessed date. Missing dates remain unknown; distinguish publication time from event time and decision time. Do not automatically classify arbitrary prose contradictions or entailment with string rules. Keep inferred facts and model proposals visibly distinct from direct observations.

The UI should show “excerpt verified”, “model interpretation/unassessed”, “inference”, “conflicting sources” or “insufficient evidence” accurately. An irrelevant but real quote must not make a narrative assertion look verified. Allow agents to ask questions and discuss hypotheses; restrict any claimed supported final summary to the recorded support and limitations. A room's agreement describes the conversation, not proven market truth.

Keep the two measured models and local serving settings. Put unambiguous metadata checks in code before trying to improve prose reasoning with more agents. Do not add a third model as an unvalidated truth judge. Role/prompt adjustments are fine when recorded and evaluated; changing the GPU engine is unrelated to these fixes.

### Focused evaluation, not another framework spike

1. Reuse existing saved errors and [cloud recalculation](evidence/cloud-review-aebd42d/grounding-recalculation.json). Do not rerun the old 120-call comparison unchanged or rewrite its scores. Test whether neutral wording and explicit entity/event/record definitions resolve a particular error before attributing it to the model/grammar/cache.
2. Create independently authored, manually checked source-question/claim pairs with development and untouched held-out partitions. Include real permitted excerpts and synthetic adversarial cases, marked separately. Cover wrong entity/event, missing/unknown/stale/future dates, relevant contradictions, irrelevant-but-real quotations, source outages, incomplete retrieval and prompt injection.
3. Freeze the sources, as-of policy, labels, evaluator and development/held-out split before generation. The same semantic case can be evaluated across models; repeated transport calls or paraphrases of one template do not count as independent cases. Counterbalance order for any paired comparison. Define which target facts are supplied by the query and what missing evidence means.
4. Evaluate the actual new prompt/publication contract and separately the integrated tool-driven room. State which transport/tool path each check exercises. A direct chat-completions extraction result is not an end-to-end room result.
5. Report unique cases and exact denominators, field accuracy, raw wrong-entity/nonexistent citations, relevant-span support, correct uncertainty/abstention, incorrect rejections, and unsupported narrative claims accepted by the real publication/UI path. Give concrete failures and uncertainty; do not count an exact-match acceptance rule as independent proof that hallucinations cannot pass.

Suggested first local inference ceiling: **120 new model requests total**, including development, tools/continuations, retries, cancellation and UI smoke runs; no model downloads. Use at most 20 for development diagnostics, up to 60 for the frozen contract assessment and up to 40 for integrated room checks. These are ceilings, not targets. Predeclare the actual case count and expected calls before starting; tool loops consume requests too. If the ceiling prevents completion, report incomplete coverage rather than silently extending it. Offline tests/case preparation need no inference.

Aim for 30 unique held-out compact cases per model within the 60-request contract allocation where one request per case is supported. If the chosen contract needs multiple requests, declare a smaller case count up front or report the uncompleted cases. The old 27/30 threshold measured synthetic five-field exact extraction and remains failed; retain it if checking that same task. For the new contract, predeclare what a fully correct case means (target/event/time, relevant evidence and correct support/uncertainty against independently checked labels). A proposed 27/30 fully correct objective per model when n=30 is a NEW limited functional target, not a transfer or pass of the old extraction gate. Freeze the metric and threshold before calls and never claim financial reliability from it. Record every unsupported assertion that gets a “supported” treatment; zero such failures in a finite sample is only a sample result. Any remaining weakness stays visible and research remains informational.

## C — integrate and hand back the useful version

- Add older-room pagination or direct room-ID access so the newest-30 limit does not hide saved work. Preserve cursor replay/deduplication and show real role/model identity and termination reason.
- Run focused backend tests; use the verified disposable launcher for graph/Postgres checks. Reuse existing passing component tests and add meaningful regressions for changed behavior. Run frontend tests, typecheck and build.
- On the local PC, verify one real evidence-backed discussion, one unresolved/disagreement case, queued/active cancellation, slow browser cancellation, reload and host API restart. Verify a worker interruption separately if that path changed; do not describe an API restart as worker resume.
- Record exact commit/config/model/prompt versions, tests, call counts and actual-versus-reserved usage in `NEXT_PHASE_FINDINGS.md`. Store only sanitized public/evaluation artifacts in Git. Keep private backups/logs outside Git.
- Activate changed research code using the existing runbook and supported IDE scope. Restart only the research worker/host API or application API when required. Preserve broker worker, controls, approvals, driver, weights and unrelated services. Check the real entry point at :8502.

Continue ordinary reversible implementation and verification within this scope; no extra approval is required to select Codex again. Report a concrete blocker if it prevents dependent work, and keep making independent progress.

## Subsequent capability work

| Order | Scope | Carry forward |
|---|---|---|
| Next source slice | Repair official filings/regulator/RSS ingestion, add permitted primary sources and the Scrapling adapter, then expose current research feeds/tools | Publication/event/fetch times, deduplication, first-seen history, source quality and explicit unavailable/truncated states. A browser and RSS download alone are not a timely news service. |
| Market context | Add GIFT Nifty and Singapore context using verified existing broker/provider entitlement and exchange calendars | Quote/history/socket availability, instrument/contract/roll identity, delay/staleness and local session handling. Evaluate incremental usefulness; do not assume STI causes Indian moves. |
| Forecast tool | Repair TimesFM input/cutoff/cache/error contracts and expose one shared informational CPU service | Returned point/channel mapping, explicit quantiles and no fabricated bounds. The current historical results justify no score/sizing/stop/target authority. |
| Autonomous room operation | Add scheduled/event triggers, deduplication/cooldowns and shared resource budgets | Start with useful operator-visible questions, preserve disagreements, and stop repeated low-information exchanges. Keep broker protection independent and live entries manually approved. |
| Later improvement/UI | Harness² prompt/retrieval experiments; optional office view driven by the same actual events | Versioned evaluation and user-chosen harness promotion; no rewriting trade authority or invented agent activity. |

No new broker migration, model-family shopping or serving-engine comparison is part of this phase. Revisit those only for a concrete measured limitation after the targeted fixes.
