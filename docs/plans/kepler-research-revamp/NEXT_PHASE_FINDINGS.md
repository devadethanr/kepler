# Next research-room phase — measured findings

Subsequent user-authorized prompt tuning and reboot recovery are recorded in
[PROMPT_TUNING_FINDINGS.md](PROMPT_TUNING_FINDINGS.md),
[PROMPT_TUNING_RESULTS.md](PROMPT_TUNING_RESULTS.md) and
[REBOOT_BROWSER_CHECKS.md](REBOOT_BROWSER_CHECKS.md). Those requests supersede the
old inference ceiling only for the new experiment; the completed phase's scores
and usage below remain unchanged. No experimental prompt has been promoted.

Completed 1 November 2026 on `feat-generic-broker`, starting at `3bc6876`.
Implementation source: **`921088c`**. Documentation/evidence are committed separately
after that source commit. Read the [evidence manifest](evidence/phase2-v1/manifest.json)
for file hashes, freeze records and the small native-check timing distinction.

## Research Desk restored first

The actual failing origin was **http://192.168.1.33:8502**. It is an insecure HTTP
context: `crypto.randomUUID` was undefined and calling it threw `TypeError:
crypto.randomUUID is not a function`. Mounting ResearchDeskScreen blanked the view;
the console reported that component's render failure. The explicit same-origin
health/history probes both returned 200. At **http://localhost:8502**, secure-context
UUID support existed and the desk rendered. This established a render failure,
not an unavailable API, socket, stale lazy chunk or rejected response schema.

The UUID-v4 helper now uses cryptographic `getRandomValues` when `randomUUID` is
unavailable. A local error boundary/retry surface and visible loading/unavailable
states prevent a silent blank view. No API key enters JavaScript. Actual isolated
browser checks on both origins passed after the fix. On the LAN origin, stopping
only the host research API produced a real proxy/socket 503 while the desk/form
remained visible; restoring the API returned 200 and recovered automatically.
Saved-room selection, direct-ID access, reload and all three recorded public
messages/claims were verified. Terminal reload made **zero stream requests**.

Evidence: [before](evidence/phase2-v1/ui-before.json),
[after](evidence/phase2-v1/ui-after.json),
[real outage/recovery](evidence/phase2-v1/ui-service-recovery.json).
Screenshots and full private records remain outside Git.

## Review findings

| Finding | Delivered change and verification | Remaining boundary |
|---|---|---|
| R1 | Persist addressed delivery attempts and completed response opportunities. A new objection blocks a terminal outcome until its recipient publishes a response, unless an explicit real limit intervenes. Concrete sequences and independent review cover late objections and final-slot acknowledgement. | An opportunity does not prove a semantic answer. Repeated new objections can exhaust the room; their limit is shown honestly. |
| R2 | Queued cancel atomically writes completion and exactly one terminal event. Repeated cancel and Postgres cancel/finish races pass. UI recognizes terminal state as well as events, including old rooms without a terminal event. | Historical events are retained, not rewritten. |
| R3 | Walk original relative path components using no-follow descriptors; refuse visible links into hidden paths, directory links, escapes, hard links and nonregular/oversized files. Dummy-artifact regressions pass. | Research root remains explicitly approved; no private/config expansion. |
| R4 | Request identity includes immutable parent/question/target. Savepoint conflict recovery handles synchronized concurrent inserts on actual disposable Postgres; incompatible create/retry use returns 409. UI retains retry UUID after lost response and blocks repeated clicks. | Linked retry is a new attempt, not a resumed Codex thread. |
| R5 | Evaluate valid outcomes before message cap. Persist typed limit/failure reasons; observe either initial role's failure promptly, signal peer stop, keep heartbeat coverage through cleanup. Owned graph reads are cancellable/bounded. Stale activity and missing usage become explicitly unknown. | Mid-turn worker kill ends the old attempt after lease expiry; it does not replay tools or resume threads. |
| R6 | One monotonic browser deadline starts before fetch and covers DNS/redirect/read/DOM. Owned fetch processes are killed/joined on stop/deadline. A real blocked child was cancelled/deadlined in offline tests; a real pending native browser job cancelled in 3.99 s. | Public allowlisted HTML/DOM only; no authenticated/general interactive navigation. |
| R7 | Compact atomic claim/evidence records distinguish record/entity/event, exact source spans, deterministic time policy and model support proposals. Unknown dates stay unknown; future publication is inadmissible; a future scheduled event is distinguished from occurrence. UI states narrative unassessed. | **Quality remains failed.** Valid excerpts do not establish narrative support; two unsupported support proposals were accepted in the held-out sample, explicitly unassessed in the public contract. |
| R8 | Show scope, offsets, omissions, scan/result caps and incomplete retrieval. Bounded artifact/search/browser continuation; direct room-ID access beyond newest 30, with an actual Store regression. | Search uses a live tree; browser continuation refetches, so offsets may shift. Browser capture stops at 12,000 characters; evidence pages are 6,000 characters. |

An independent Terra lifecycle review caught an initially overstrict final-slot
agreement rule, premature “delivered” wording, continuation-budget reason handling
and cleanup heartbeat gaps. These were corrected before final checks. File ownership
was separated between backend, evidence/tools and UI; one integrator owned scheduler,
evaluation and shared verification. No new runtime judge/model was introduced.

## Contract and frozen assessment

The seven compact publication fields are `recipient`, `text`, `quote_id`, `position`,
`claim_kind`, `support_assessment`, `event_id`. Each message carries one atomic claim,
canonical evidence/quote references, source metadata, deterministic metadata policy,
and `narrative_verification: unassessed`. Legacy four-field messages remain accepted
as inference/unassessed. Model assessments are proposals, including “supported.”
Excerpt admission is separate from entailment; agreement describes conversation.

Run **`next-phase-20261101T200149`** declared the 120-request ceiling before inference:
20 development, 60 contract, at most 40 native integration requests. Actual usage:
**20 + 60 + 32 = 112**, with eight unspent. No downloads, engine changes or hidden
retries. Counterbalanced held-out ordering: analyst forward, skeptic reverse.

Development had six unique cases per model (12 calls), followed by the same four
development cases per model (eight calls). The first pass exposed null event-ID
arguments and verbose claim copying. Explicit empty-string/type guidance and event-ID
enum narrowing improved those observed development failures; this does not isolate
model, grammar or caching causes. Old saved extraction scores were not changed.

A separate Terra author created and inspected **30 distinct held-out cases** before
generation: three exact permitted repository excerpts and 27 synthetic adversarial
cases. Source/label/relevance decisions were independent of the evaluator author and
were not tuned to generated outputs. This is agent-authored functional gold, not an
independent human financial assessment. Frozen case SHA-256:
`69f4683aee439ee435bee291ea53e56dcd72106006bf1a26caa69639c2bad912`.

The assessment uses the **actual Responses adapter, current Codex instructions/tool
schema, real Gateway.execute publication path and SQLite persistence** with supplied
evidence packets. It is not a native App Server/tool-retrieval room. Native room checks
below exercise that separate path. Each held-out case consumes exactly one request;
there are no repeated calls counted as new independent cases. Fully correct means
accepted publication, exact supplied atomic claim/kind/support, relevant citation and
correct cited source event identity. The new 27/30 objective remains **failed** and
does not replace the older failed five-field extraction gate.

| Metric | Gemma / analyst | Qwen / skeptic |
|---|---:|---:|
| Unique held-out cases / requests | 30 / 30 | 30 / 30 |
| Fully correct | **20/30** | **14/30** |
| Exact claim text | 29/30 | 25/30 |
| Claim kind | 30/30 | 30/30 |
| Support proposal matches gold | 26/30 | 22/30 |
| Relevant citation choice | 24/30 | 26/30 |
| Cited event identity | 28/30 | 29/30 |
| Publication accepted / valid quote accepted | 26/30 / 26/30 | 28/30 / 26/30 |
| Raw wrong-entity / wrong-event / nonexistent citations | 1/30 / 1/30 / 0/30 | 0/30 / 0/30 / 0/30 |
| Accepted wrong-entity / wrong-event citations | 0/30 / 0/30 | 0/30 / 0/30 |
| Raw irrelevant citations | 6/30 | 4/30 |
| Correct uncertainty on designated cases | 16/20 | 12/20 |
| Incorrect rejection of supported gold cases | 0/5 | 0/5 |
| Unsupported “supported” proposals accepted | **1/30** | **1/30** |
| Published narratives labeled truth-verified | 0/30 | 0/30 |

Both models' accepted unsupported proposal is heldout-09: a current CEO assertion
backed by an undated real span. The metadata correctly stays unknown, but the model
still treats it as current. This is a concrete remaining failure. The evaluator counts
actual accepted proposals independently from correctness; it does not define “accepted”
as exact gold match. Zero nonexistent IDs is only this finite sample's result.
Target is supplied by the query/gateway; no independently generated entity-field
accuracy is claimed. Source relevance/entailment is measured against the authored
labels, not inferred by string rules or another model's agreement.

## Native app and lifecycle checks

| Check | Result |
|---|---|
| Evidence discussion, LAN form | `room:3d02d834-20fc-46c3-8636-5d066e5800e1`: actual files and current graph (empty honestly), three live messages, 12 requests, `call_limit`; reload preserved history. |
| Unresolved discussion, LAN form | `room:e01582bd-7050-4779-82dd-eba9c3f4aef1`: six live addressed messages including repeated objections, ten requests, `message_limit`; latest unresolved objection remained visible, reload preserved history. |
| Queued cancellation | Zero inference, exactly one finished event after repeated cancel. |
| Active UI cancellation | Two active model requests; cancelled in 4.28 s, one terminal event. |
| Browser cancellation | Six requests, five tool actions; actual browser_read pending when cancelled, terminal after 3.99 s, one finished event. |
| API restart/cursor | Same immutable event IDs afterward; cursor 34 replays the identical 33 subsequent events; socket 0600. |
| Killed worker | Two admitted calls before SIGKILL; recovery after lease expiry marks interrupted, active reconciled to zero, unresolved activity two models and unknown usage two. No tool replay. Linked fresh retry replays the same compatible request ID and was queued-cancelled without inference. |

These observed discussions do not prove financial reliability or that objections were
semantically resolved. Limit-triggered `abstention` retains a typed limit reason rather
than claiming the agents concluded that no evidence exists.

## Checks, usage and service preservation

- **112 focused backend/graph tests passed, zero skipped/failed.** Actual Postgres
  insert/cancel races and guarded disposable graph tests included. The graph launcher
  independently verified the internal network/address before collection/deletion.
- **21 frontend tests, TypeScript, Vite build, Ruff and whitespace checks passed.**
  Vite built to `/tmp/kepler-ui-phase2-final-build`; existing root-owned `dist` was
  preserved. Existing KnowledgeScreen chunk and two uvicorn/websockets deprecation
  warnings remain. No full trading/backtest suite was needed for this research slice.
- **112 model admissions**, 101 tool admissions, 356,585 reported input tokens,
  10,593 reported output tokens, **three unknown-usage calls** (one cancelled model,
  two killed-worker calls). **3,670,016 reserved context tokens** are cumulative
  reservations, not measured consumption. Available host RAM snapshot: 7,285,064 KiB;
  both pinned model identities remained ready. No new GPU benchmark/OOM claim.
- Versions retained: Codex **0.164.0**, agent-browser **0.41.0**, pinned skill commit
  `5868f7c05020e047c00e68e4abf9253cce864f41`, llama.cpp **9067 / 44dbe8c5**,
  Gemma E4B q4_0 and Qwen3.5-9B Q5_K_M, 32,768 context, 512 output, thinking disabled,
  single slot/profile and existing CPU embedding placement. Prompt/evaluator hashes
  are in the [freeze](evidence/phase2-v1/heldout-freeze.json).
- Only needed host research API/worker units were restarted/recreated. Models stayed
  running. Normal Docker API, dashboard, broker worker, broker MCP, database and graph
  container identities/start times remained unchanged. Controls, block/kill switches,
  DDPI/POA and open incidents compared equal. Manual live-entry approval and TimesFM's
  lack of trading authority remain. Original private room config restored byte-for-byte.
- All research units are left running at **:8502 → Research Desk**. A stopped transient
  API unit may be collected; `make research-start` recreates it. No security policy,
  driver, model weights, broker migration, authentication refresh or order action.
- Fetch and fast-forward check found branch already current. Git stash cleanup hit
  permission-denied untracked directories, leaving the working files intact. Each of
  the five tracked runtime files was checked byte-for-byte against both private backup
  and retained stash **`stash@{0}` / `b69b0eb`**, named
  `safe-next-phase-before-pull-20261101`. No duplicate apply or cleanup was attempted.
  The runtime files remain uncommitted: agent_activity.json, event_log.jsonl,
  macro_cache.json, regime_cache.json, scan_status.json.

Private backup/log root: `~/.local/state/kepler-rooms/next-phase-20261101T200149/`.
Normal/disposable database backups, full browser data, screenshots and private service
environments stay there. Sanitized artifacts are under
[evidence/phase2-v1](evidence/phase2-v1/manifest.json). Old evidence/scores are retained.

## Remaining limits and smallest next capability

R1–R6 and R8 correctness changes are implemented; R7's structured representation and
honest UI are delivered, while its semantic-quality objective remains unmet. No
automatic forecast/trade authority follows. The smallest useful next improvement is
an explicit temporal requirement on atomic claims (so an undated current claim cannot
look supported), evaluated on independent cases, then one bounded primary-source feed.
Keep provenance/omissions and manual approval intact before scheduling autonomous rooms.
