# Local SLM prompt tuning — execution log

Final source: **`7f6dc9f`**, on `feat-generic-broker` from `5adeaea`. Seven development
rounds and independent validation are complete. The final confirmation is **25/30
Gemma, 24/30 Qwen**; the 27/30 objective remains failed. Experimental prompts are
not installed. Post-reboot research services and actual native UI/tool checks are
restored; see the final accounting and handback below. Earlier estimates are kept
as an audit trail and explicitly corrected by durable admission records.

Prompt packaging follow-up (2 November): retained v7 files are now
`contract-agent.md` / `evidence-agent.md`; retained Gemma v2 files are
`contract-analyst.md` / `evidence-analyst.md`. Text and experiment selectors are
unchanged; frozen snapshots keep original names. See [WORK_HISTORY.md](WORK_HISTORY.md)
for the full reference history and [prompt usage](../../../swingtradev3/research_room/prompts/README.md).

User authorization on 1 November 2026 permits as many local-model prompt iterations
as needed, superseding the completed phase's 120/20 request limits. The user requires
general behavior for unseen data and retention of all findings. No entity, date,
quantity, source ID, answer label per case or case-specific branch is embedded in a
candidate prompt. Protocol field names/enums remain fixed; evidence values and policy
thresholds are supplied as data.

The original 20/30 and 14/30 results and artifacts remain unchanged. The inspected
old held-out set is now seen regression data. This log will distinguish development,
fresh unseen comparison, generic challenge checks and native tool-driven discussion.

## Preparation and independent review

- Created separate policy, output-format and combined candidates. The `baseline`
  variant still reproduces the old task; `generic-baseline` retains the original
  participant instructions but gets a common assessment task with input-defined
  freshness. The old benchmark's fixed age threshold is not a new market-data rule.
- An independent lifecycle/evaluator reviewer identified source-level citation
  blind spots, cautious-label versus unsafe-support confounds, false-abstention
  undercounting and prompt-layer conflicts. These findings are preserved here
  rather than interpreting the composite strict score as factual accuracy.
- New span-aware scoring uses independently authored exact allowed quote text and
  actual wrong-scope gold, not only a document label. It reports raw unsafe support,
  publication-gate acceptance, grounded support, positive recall, false abstention,
  field accuracy and altered publication text separately. Legacy scoring stays intact.
- New validation cases were authored independently by separate Terra agents. The
  integrator has not opened the sealed held-out/challenge contents during development.
  Only development cases are inspected for candidate revisions.
- Fresh held-out freeze: 30 cases, 10 supported / 6 contradicted / 10 insufficient /
  4 unassessed, including three checked repository excerpts. SHA-256:
  `f730965d462192bd4527bdddde06bc6706628f6362c7a9d5322a04a258470bbf`.
- Separate generic challenge freeze: 20 synthetic cases, 6 supported / 4 contradicted /
  6 insufficient / 4 unassessed. SHA-256:
  `83c98c4352e726802814b1122b481545382a40ee2d84ecbdb654a44cc0244fa3`.
- Development freeze: 20 cases with usable positives, explicit contradictions,
  temporal uncertainty, scope mismatch, irrelevant spans, omissions, questions and
  inferences. SHA-256:
  `9505778b16fb40a1ebcfa3bb179e1380cc6d0150d874b3996b326d7ace59337d`.

## Run and protection

Private run: `~/.local/state/kepler-rooms/prompt-tuning-20261101T205220/`.
Changing tracked/untracked work was copied privately first. The research worker was
idle and paused to prevent it competing for model slots. Model services and API/history
remain running; broker services/controls are untouched. Original service identities,
operator safety response and private room configuration were captured for comparison.

Each batch freezes prompt text, evaluator/source hashes, case hash, role/model identity,
counterbalanced order and planned requests before generation. An append-only ledger
records each request intent before the call and its result afterward. One request per
case/arm, no automatic retries. Reservations and actual/unknown usage remain separate.
Operational batch ceilings bound mistakes; they are not a renewed user permission gate.

## Development iteration 01 — completed

Compare `generic-baseline`, `policy-v2`, `format-v2`, `combined-v2` on the same 20
development cases for both installed models: **160 planned local requests**. Arm
rotation and reversed role case order counterbalance execution. All arms use the real
Responses bridge and publication gateway with supplied fixture packets, not native
retrieval. No prompt is promoted from this batch alone.

Initial offline checks: nine focused tests passed, Ruff passed. Candidate prompt files
were checked for embedded development entity names: none. Performance results, selected
candidate, later iterations, unseen outcomes and service restoration will be appended
after measurement. No unmeasured gain is claimed.


## Measured development so far

The [results appendix](PROMPT_TUNING_RESULTS.md) retains every role/arm and failure.
Iterations 01–04 used 480 local requests. The repeated 20-case development set is
not 480 independent observations. Main observations before iteration 05:

- On the common generic-input baseline, both roles scored 12/20 strictly correct.
  The first combined v2 candidate scored 16/20 Gemma and 13/20 Qwen. The original
  old-set 20/30 and 14/30 remain a different, unchanged evaluation.
- Wording changes are not monotonic improvements. Combined v3 fell to 7/20 on
  Gemma, including incomplete non-function replies at the unchanged 512-token cap.
  Qwen scored 16/20 but lost a positive case. This candidate was not promoted.
- Combined v4 improved function use, but Gemma made an unsupported support proposal.
  The short wording is therefore not an automatic quality or safety improvement.
- Compact representation retained all source text/status/time/omissions, placed
  quote options together, removed duplicate requested-scope labels, and restricted
  selectable IDs using existing deterministic metadata validation only. Gold spans
  and answer labels were never used to filter model options. It did not uniformly
  improve both models: combined v2 was 16/20 Gemma and 15/20 Qwen; combined v4 was
  11/20 Gemma and 16/20 Qwen, with one accepted unsupported Gemma proposal.
- A different current-time `fetched_at` is present on repeated case requests, and
  repeated controls showed small output variability despite temperature zero.
  Neither a cache defect nor a single deterministic prompt cause is established.

Iteration 05 compares the retained v2 control with an independently drafted v5
and a general priority/field-consistency v6. Cases/values/expected answers do not
appear in any candidate. All considered changes remain experimental.

## Sealed-set audit before any generation

An independent reviewer found semantic overlap with seen cases and some labeling /
source-time ambiguities in the initially authored sealed files. The authors repaired
those before any validation output was generated, preserving counts and class balance.
The integrator remained blind to contents/answers. Original intermediate hashes above
remain as authoring history; final reviewed freezes are:

- Fresh 30-case held-out SHA-256:
  `88c5d95599e540babb258a74f25c5acdcf463f9b7a379fc2c74f1eefe2931407`.
- Separate 20-case challenge SHA-256:
  `afd24bf0c5417d77716392fab273af8d5139e0859edf5a322f96a35317303a04`.

Exact span gold, actual-scope errors, class balance and cutoff admissibility were
reviewed independently. The supplied freshness threshold is forwarded both to the
actual packet builder and to the model's input policy. Repository excerpt availability
was checked against source history before the applicable cutoff. No held-out score
is reported until candidate selection and the full validation matrix are frozen.

## Restart recovery and frozen validation

The PC restarted during the opaque-ID probe. The six completed development batches
survived: 680 recorded model calls, 35 incomplete protocol attempts and one call with
unknown token usage. The opaque probe retained 28 completed rows and one final
intent without a result; its JSONL tails were NUL-padded and summary empty. Original
files are retained privately, including their bytes and hashes. The unmatched intent
is an additional potentially admitted request with unknown outcome, never a zero.

Recovery uses a new batch, reuses the exact prepared packets, skips only recorded
complete results and makes the remaining 12 calls. This includes a declared new
attempt for the unknown outcome. The resulting 40 distinct role/case observations
score **Gemma 16/20, Qwen 13/20**, with strict supported-case recall **5/5 and 4/5**;
neither role has an accepted unsupported-support proposal in this probe. These are
relabeled development cases, not 20 new independent cases. Qwen's drop from 16/20
on readable IDs is an identifier-sensitivity warning; no prompt was changed to fit it.

Selected before unseen generation: Gemma `combined-v2` with full packets; Qwen
`combined-v4` with compact packets. Fresh held-out compares `control-full`,
`control-compact` and `selected` on the same 30 cases per model (180 calls). Separate
challenge compares `control-full` and `selected` on 20 cases per model (80 calls).
The full control retains installed participant instructions with the common generic
assessment task. The compact control separates representation from prompt effects.
Prepared packets, including fetch timestamps, are shared across arms and roles.
The predeclared objective remains 27/30 strict, no accepted unsupported support and
at least 9/10 strict positive recall per model. No threshold was changed after results.

The new `paired_experiment.py` freezes source snapshots and prompt/case/evidence
hashes before admission, and fsyncs both request intents and completion records.
Recovery is explicit into a new directory; there is no hidden replay or overwrite.

After restart, the normal Docker broker/API/database/graph/dashboard were already
running; transient research model/API units were absent. Recreated those research
units using the existing launcher, hashes, model files, GPUs and serving settings.
The research worker remains paused only while the isolated model matrix runs. The
private configuration matches its pre-experiment snapshot byte-for-byte. The
owner-only Unix socket has mode 0600 and the dashboard health proxy reports both
models ready. No broker service or manual-entry control was changed by this work.

Post-restart checks so far: **124 backend/guarded graph tests passed**, including
the new evaluation and recovery tests; **21 frontend tests and TypeScript passed**.
An initial test command named a nonexistent isolation test and collected no tests;
the immediate overlapping disposable cleanup caused a second attempt to exit 137.
The serialized corrected command passed. The default frontend build encountered
Docker-owned `dist` permissions; building to a new private output directory passed,
without deleting or changing ownership of the existing served files. Vite's existing
large-chunk and two dependency deprecation warnings remain.

Actual isolated browser checks passed on localhost and the LAN origin at :8502:
lazy screen load, saved discussion/history schemas, UUID fallback on insecure LAN
HTTP, reopening after reload and direct access to an older room omitted from the
recent list. Simulated API failure and malformed response show useful errors without
a blank view. Reload clears selection but the saved room can be reopened. The only
console 404 was the favicon; dashboard unmounts aborted irrelevant initial requests.
These outage/list/schema cases used browser request interception, not a claimed real
service outage. Live discussion/cancellation/restart checks follow the model matrix.

## First independent comparison — objective failed

All 180 held-out and 80 challenge requests completed. The appendix preserves every
arm. These compare the same new cases against the common generic-input baseline;
they are not a before/after comparison with the old 20/30 and 14/30 corpus.

| Frozen arm | Gemma strict / positive recall / unsupported support accepted | Qwen strict / positive recall / unsupported support accepted |
|---|---|---|
| Fresh 30, full control | 22/30 · 10/10 · 1/30 | 20/30 · 9/10 · 0/30 |
| Fresh 30, compact control | 21/30 · 10/10 · 1/30 | 21/30 · 9/10 · 0/30 |
| Fresh 30, selected | 23/30 · 10/10 · 1/30 | 20/30 · 7/10 · 0/30 |
| Challenge 20, full control | 7/20 · 3/6 · 1/20 | 14/20 · 6/6 · 1/20 |
| Challenge 20, selected | 10/20 · 4/6 · 0/20 | 14/20 · 6/6 · 0/20 |

The 27/30 strict and zero-unsafe requirements fail. Neither selected candidate is
promoted. Qwen's selected policy improved support-label agreement on the fresh set
(25/30 versus 22/30 full control) while rewriting more supplied claims (five versus
one). This explains part of the strict positive-recall loss; it is not evidence that
the model refused three true observations. The exact benchmark and original scores
remain intact. False-abstention diagnostics include missing proposals, so they are
not a pure count of explicit conversational abstentions.

After the complete frozen run, inspecting fresh-set failures exposed both semantic
and formatting errors: Gemma proposed support for an explicit negated statement;
both roles confused missing premises with contradiction or an unassessed assertion;
Qwen paraphrased otherwise supported claims; some questions omitted contextual spans;
some known-but-unusable future spans reached the gateway and were rejected. Metadata
and exact-span checks cannot establish semantic entailment. The accepted false
negation is a real remaining failure, not excused as a format error.

One further generic candidate (`combined-v7`) explicitly distinguishes an assertion
with missing evidence from a prediction, compares whole propositions including
negation/units, and separates assessment-mode output from conversational output.
It contains no example entities, case IDs, dates, values or expected case answers.
Development round 07 compares it with the full generic baseline and v2 on the same
20 seen cases (120 calls). The first fresh set is now seen diagnostic data and will
never be reported as unseen for v7. A separate author has prepared a new 30-case
sealed confirmation set; root remains blind while the candidate is being selected.

## Final confirmation and stopping decision

Round 07 used 120 development calls. Gemma v7 scored 15/20 versus v2's 17/20;
Qwen v7 scored 16/20 versus the generic baseline's 12/20, with exact text and kind
20/20 and positive recall 5/5. No accepted unsupported support occurred in that round.
The confirmation freeze therefore kept Gemma v2/full and selected Qwen v7/full.
The assessment-only task text remains separate from participant policy; it is not
installed into open-ended conversation turns.

The independently authored confirmation set contains 30 new synthetic cases, balanced
10 supported / 6 contradicted / 10 insufficient / 4 unassessed. A separate reviewer
caught two potential semantic-template overlaps before generation; both were revised.
The first authoring hash was
`645e40ae5e966e795ed087cb45574408745a03c36bb5cb406b62538821edfe99`;
the final independently reviewed freeze is
`3ffd5fd640d5b02bf54fe8624a0cfa63b09c34e4597f43e7b0dd4666e6a78cc5`.
Root remained blind to contents until the selection, source/prompt hashes and 120-call
paired matrix were frozen. No case labels or allowed-gold spans entered model inputs.

| New 30-case confirmation | Gemma full control | Gemma v2/full | Qwen full control | Qwen v7/full |
|---|---:|---:|---:|---:|
| Strict correct | 20/30 | **25/30** | 21/30 | **24/30** |
| Support label matches gold | 23/30 | 29/30 | 25/30 | 28/30 |
| Strict positive recall | 10/10 | 10/10 | 10/10 | 9/10 |
| Gate accepted | 27/30 | 27/30 | 27/30 | 27/30 |
| Unsupported support accepted | 1/30 | 0/30 | 0/30 | 0/30 |
| Relevant-span field correct | 25/30 | 25/30 | 24/30 | 25/30 |
| Raw wrong entity / event / nonexistent IDs | 1/1/0 | 1/1/0 | 1/1/0 | 1/1/0 |
| Incomplete protocol attempts | 0/30 | 0/30 | 0/30 | 0/30 |

Both candidates improve this matched comparison but **neither meets 27/30**. Earlier
accepted unsupported support and identifier sensitivity also remain in the evidence.
The installed participant prompt/configuration is unchanged. This is a completed
seven-round prompt experiment with a remaining quality failure, not a deployed fix
or proof of reliable financial reasoning. Further wording changes on these now-seen
sets would risk fitting the benchmark. The next useful experiment should target
semantic source/span selection and independently validate it, while retaining the
current distinction between verified excerpts and unverified interpretations.

An independent source audit confirmed unchanged legacy-score AST and identical
span-v2 scorer bytes across the exported experiments. Public source snapshots contain
the changing evaluator modules and prompts; the remaining frozen files reconstruct
from the committed repository. Exact spans alone are not a semantic truth verifier.
The new recovery driver now checks prior case/prompt/model/evidence identity, reconciles
ledger intents and requires a declared count for unknown outcomes before retrying.
Older damaged prefixes can only establish a lower bound; original bytes are retained
and SQLite admission records are being reconciled separately from scored rows.

## Durable accounting correction

The damaged opaque JSONL prefix understated actual calls. Read-only inspection of all
40 original per-case SQLite stores proves **40 original admissions**, including the
12 whose JSONL outputs were lost. Each has a persisted model/tool admission and
reported usage. Thirty-nine published a message; one was denied by the gate. The
12 recovery calls were therefore additional repeated attempts. The previously
unmatched analyst intent is resolved as admitted with a persisted publication.

The 20-per-role opaque score above uses 28 retained original rows plus 12 explicitly
repeated recovery rows, not an invented reconstruction of lost response metadata.
The extra original 12 are accounted but not silently rescored. Probe differences
also cross the reboot boundary, so they cannot establish an ID-only causal effect.
Database hashes and per-case counters are exported; databases and raw internal
records remain private. See [the SQLite audit](evidence/prompt-iteration-v1/batches/opaque/sqlite-audit.json).

The experiment consequently used **1,232 confirmed local model requests**:
800 development, 52 opaque (40 original + 12 recovery), 180 fresh comparison,
80 challenge and 120 final confirmation. There are 1,220 JSONL result rows, 37
observed incomplete protocol attempts, and one call with unknown token usage.
Response-status metadata for the 12 DB-only outputs is unavailable; a denied
publication is not classified as protocol-incomplete. The separately scoped native
checks add 55 requests. The completed earlier phase's 112 calls are not included.
Combined: **1,287 admitted/confirmed model requests**, 1,245 tool admissions,
42,172,416 reserved tokens, 2,849,322 reported input and 155,377 reported output
tokens. Four calls have unknown token usage (one isolated, three native), so those
input/output totals are recorded values, not exact overall consumption.

Whole-context reservations are cumulative admission bounds, not measured input or
output tokens. Reported usage, unknowns and per-batch counters are preserved in
[accounting-summary.json](evidence/prompt-iteration-v1/accounting-summary.json).
[manifest.json](evidence/prompt-iteration-v1/manifest.json) hashes all exported
artifacts; [checks.json](evidence/prompt-iteration-v1/checks.json) and
[preservation.json](evidence/prompt-iteration-v1/preservation.json) record verification.
Both local models were exercised concurrently in paired lanes; no hosted-model
fallback, model download, serving change or new model judge was introduced.

## Native handoff verification and preservation

See [REBOOT_BROWSER_CHECKS.md](REBOOT_BROWSER_CHECKS.md) and the
[sanitized native results](evidence/prompt-iteration-v1/native/rooms-summary.json).
These exercise the **original installed policy**, not the experimental candidates.

- Actual normal browser origins: localhost:8502 and 192.168.1.33:8502. Desk lazy
  loading, schemas, insecure-origin UUID fallback, useful unavailable/error states,
  direct older-room access, live events, history/reload and terminal stream closure pass.
- The Kepler runbook room used real file search/read and addressed messages, but did
  not choose graph lookup. It ended at a resource/call boundary, not an asserted
  factual conclusion. This retrieval-choice limitation is retained.
- The SEBI room loaded the pinned skill, executed real browser reads/continuation
  for both agents, exchanged nine addressed messages and concluded. A separate
  pending browser_read cancelled in about 4.4 seconds with one terminal event.
- The explicitly scoped RELIANCE room executed two successful actual graph lookups,
  exchanged seven messages including disagreement, and ended in abstention. Historical
  completeness and narrative truth were not inferred from those graph results.
- Queued cancellation used zero model calls. Real research-API restart produced
  observed proxy 503s, recovered to 200 and retained byte-identical saved history.
- Killed only the owned research worker scope after two actual model admissions.
  The real lease became stale, replacement worker marked the old room interrupted,
  and exactly one terminal event persisted with two unknown-usage calls. No tools
  replayed. A linked retry had fresh identity/zero counts and was queued-cancelled.
  Chrome verified both saved rooms, unknown activity, reload and zero terminal SSE.
  Private harness assertions initially used the wrong public field names; corrected
  against the actual schema and verified the existing rooms without extra inference.

Final regressions: **125 backend/guarded disposable graph/Postgres tests passed**,
**21 frontend tests**, TypeScript, private-output Vite build, Ruff and diff checks.
No unsafe operator-graph fixture ran. Earlier failed command/build attempts and
their corrections remain recorded above. No full trading/forecast suite or repeat
of the already completed engine/forecast spike was claimed by this prompt follow-up.

Models, research API and managed worker scope are running at handoff. Models remain
the installed Gemma E4B q4_0 / Qwen3.5-9B Q5_K_M pair, llama.cpp build 9067,
Codex 0.164.0 and agent-browser 0.41.0, 32,768 context / 512 output, temperature zero,
reasoning disabled and existing embedding placement. Private configuration is
byte-identical to the pre-run snapshot. Existing Docker broker, API, database, graph
and dashboard container IDs/start times match the post-reboot pre-test snapshot.
Operator controls and block reasons match before; manual live-entry approval stays
enabled. The original runtime event-log prefix is preserved. No broker migration.

Five runtime files remain uncommitted: `agent_activity.json`, `event_log.jsonl`,
`macro_cache.json`, `regime_cache.json`, `scan_status.json` under
`swingtradev3/context/`. Backup `stash@{0}` (`b69b0eb`,
`safe-next-phase-before-pull-20261101`) is retained. Experimental source and sanitized
docs/evidence are committed separately; no private config, SQLite, credentials,
browser HTML, model reasoning or changing account/runtime state is published.

## Copyable handback

```text
KEPLER PROMPT / REBOOT HANDOFF
Branch / source: feat-generic-broker, 5adeaea -> 7f6dc9f; following docs commit.
Desk: http://localhost:8502 -> Research Desk; LAN UUID fallback verified.
R1-R8: prior fixes retained; 125 backend/guarded graph/Postgres and 21 UI tests pass.
Prompts: seven development rounds, frozen generic candidates; no case-value hardcoding.
Unseen: first 30-case paired comparison 23/30 Gemma, 20/30 Qwen; still failed.
Challenge: 20 cases, selected 10/20 Gemma, 14/20 Qwen; failures retained.
New confirmation: 30 cases, 25/30 Gemma v2/full, 24/30 Qwen v7/full.
Confirmation support labels: 29/30 and 28/30; strict positive recall 10/10 and 9/10.
Confirmation unsafe support accepted: 0/30 each; earlier unsafe failures retained.
Objective: 27/30 still failed. Candidates inactive; no reliability claim or forced consensus.
Calls: 1232 isolated + 55 native = 1287 confirmed local requests; usage unknowns explicit.
Opaque recovery: SQLite proves 40 original +12 repeated calls; lost JSONL not fabricated.
Native: actual graph/files/browser, addressed discussion, pending browser cancel pass.
Recovery: real API 503/recovery; actual worker SIGKILL/lease expiry -> interrupted.
Retry: new linked identity/zero counters, then queued-cancelled; no ambiguous replay.
Services: models/API/worker running; installed serving config and original policy retained.
Safety: broker services/controls/manual entry approval preserved; runtime files excluded.
Docs: PROMPT_TUNING_FINDINGS.md, PROMPT_TUNING_RESULTS.md, REBOOT_BROWSER_CHECKS.md.
Evidence: evidence/prompt-iteration-v1/ (hashes, frozen prompts, public results, native checks).
Remaining: semantic span selection, negation/scope mistakes, bounded context/call limits.
Next: independent semantic-retrieval experiment; do not fit these now-seen sets or add trade authority.
```
