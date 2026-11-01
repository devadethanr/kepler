Execution update: the user subsequently authorized as many local SLM iterations as needed. See [PROMPT_TUNING_FINDINGS.md](PROMPT_TUNING_FINDINGS.md) and [all measured development results](PROMPT_TUNING_RESULTS.md). The original budget-pending preparation below is retained as history.

> Completed experiment: subsequent user-authorized iterations are recorded in [PROMPT_TUNING_RESULTS.md](PROMPT_TUNING_RESULTS.md), [PROMPT_TUNING_FINDINGS.md](PROMPT_TUNING_FINDINGS.md) and their accounting manifest. Candidates remain inactive after final 25/30 and 24/30 scores. The active next task is [FRESH_SOURCE_IMPLEMENTATION.md](FRESH_SOURCE_IMPLEMENTATION.md), not another round on the now-seen sets.

# Iterative prompt work — prepared, not promoted

Prepared after `5adeaea` in response to the user's request to improve the installed
agents iteratively. **No fresh model calls, active prompt change, service restart,
commit or push has been performed by this follow-up.** The prior 20/30 and 14/30
results remain unchanged. A new inference budget is awaiting the user's selection:
the completed run spent 112/120 total requests and all 20 development requests.
No new run is started to bypass those limits.

## What the saved failures establish

The strict score combines claim copying, kind, support label, citation choice,
event identity and actual publication acceptance. It is not a count of false facts.
The [offline audit](evidence/prompt-iteration-v1/saved-failure-audit.json) groups the
saved failures without relabeling cases or inventing new model results.

| Disjoint outcome bucket | Gemma, n=30 | Qwen, n=30 |
|---|---:|---:|
| Fully correct under the frozen rubric | 20 | 14 |
| Only verbatim claim text wrong, accepted | 0 | 4 |
| Only support label wrong, accepted | 2 | 6 |
| Only citation choice wrong, accepted | 2 | 2 |
| Multiple errors or publication rejection | 6 | 4 |

Across all cases, support labels matched 26/30 and 22/30, citation choices 24/30
and 26/30, and exact claim text 29/30 and 25/30. Each model's accepted unsupported
support proposal concerned an undated current CEO claim. These are demonstrated
failures; their causes are hypotheses until a controlled change is evaluated.

The audit also found rubric/representation issues to clarify before a new freeze:

- Old development dev-05 disallows a stale quote, while held-out heldout-11 permits
  a stale quote as context for uncertainty. The candidate distinguishes relevant
  context from support; old labels/scores stay fixed.
- `insufficient` for an inference/question is cautious, but misses the frozen
  `unassessed` label. Report label adherence separately from unsafe support.
- A useful explanation or corrected source sentence fails exact claim copying.
  Diagnose that formatting failure separately from its factual assessment.

The old held-out set is now **seen regression data** after failure inspection.
It cannot serve as a fresh independent validation set for these candidates.

## Prepared candidates and attribution

The evaluation CLI supports explicit opt-in variants; default remains `baseline`:

| Variant | Participant policy | Assessment task |
|---|---|---|
| baseline | Existing Codex instructions | Existing frozen TASK |
| policy-v2 | Ordered entity/event/time/conflict checks | Existing TASK |
| format-v2 | Existing instructions | Explicit unchanged-claim output contract |
| combined-v2 | Both candidates | Both candidates |

Files: `research_room/prompts/evidence-v2.md`, `contract-v2.md` and
`prompt_candidates.py`. The runtime `codex.py`, worker and configuration remain
unchanged. No candidate is selected by the installed room. Candidate evidence
policy makes the following choices explicit:

1. Classify observation/inference/question before its support label.
2. Wrong entity/event/period or missing coverage is insufficient, not contradiction.
3. An undated statement containing “currently” does not establish a current fact.
4. An event plan is distinct from a completed event; publication and event times differ.
5. Unresolved relevant source conflict means insufficient, not selective certainty.
6. Copy only an established cited event ID; no quote means an empty event-ID string.

`format-v2` is an **assessment-specific diagnostic**. Better claim copying in that
task must not be described as better live research reasoning. `policy-v2` is the
first proposed comparison because it targets unsafe temporal support. Test one
factor before combining candidates. No performance improvement is claimed yet.

## Proposed next bounded run, subject to the requested budget

For a user-authorized fresh 120-request run, keep the original allocation ceilings:

- Development: at most 20 requests total. Four cases × two models × baseline/candidate
  =16 calls, plus two new development confirmation cases × two models =4. Each case
  has one request, no retries. Freeze the comparison and counterbalance arm order.
- Fresh held-out assessment: at most 60 requests, 30 new distinct cases per model,
  evaluated once on the selected candidate. Author labels independently, keep them
  out of development prompts, and freeze before generation. Balance positive support,
  contradiction and uncertainty so an indiscriminate abstainer cannot appear useful.
- Native room checks: at most 40 requests, including tools, continuations, cancellation
  and retries. Verify the chosen participant policy with actual retrieval and addressed
  messages, separately from the supplied-evidence contract assessment.

Keep the installed Codex/Gemma/Qwen/llama.cpp profiles, 32,768 context, 512 output and
existing serving settings. No hosted API, new engine, downloads or third-model judge.
Cases/paraphrases used during tuning never become independent held-out cases.

Promotion requires the frozen functional objective, no accepted unsupported support
in that finite sample, explicit supported-case recall, citation/uncertainty metrics,
and the real room checks. Keep the previous 27/30 limited objective unless a new
rubric/threshold is justified **before** generation; never loosen it after results.
Failure remains a reported failure. Stop at the budget rather than silently starting
another run. A benchmark-only formatting improvement does not justify changing runtime
agents. Preserve broker services, manual approval and changing runtime files.

Each future freeze now hashes the exact system prompt including its joining newline
and records the variant. Variant result directories share total/development/assessment
allocations; changing case IDs or candidate names cannot renew the allocation. This
continues to rely on a single orchestrated run; it is not a global accounting service
for unrelated user-created rooms or crashed processes without a saved result.

## Checks performed so far

Five offline tests passed: shared allocation across candidate/result names, exhausted
held-out allocation, overall ceiling, and existing real publication/scoring regressions.
Ruff and whitespace checks passed. No local-model inference occurred. Old artifact
hashes and scores were retained. Live research services were not changed.

Workflow reference: [OpenAI Docs evaluation flywheel](https://developers.openai.com/cookbook/examples/evaluation/building_resilient_prompts_using_an_evaluation_flywheel).
This informs experiment separation; it is not evidence that a specific prompt will
improve the installed local models.
