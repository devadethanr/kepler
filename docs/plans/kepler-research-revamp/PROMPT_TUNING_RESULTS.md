# Prompt tuning results appendix

Development and held-out results for the local Gemma/Qwen experiment `prompt-tuning-20261101T205220`; bookkeeping by Luna. These experimental measurements do not promote a prompt or change serving behavior. The held-out and challenge results are reported separately. All rows are retained, including negative and incomplete results.

## Reading the tables

- `strict` is fully correct; `accepted` is gate accepted.
- `raw unsafe → accepted` reports raw unsupported-supported proposals and raw ungrounded-support proposals that were accepted, respectively. Counts are shown as `unsupported/ungrounded`.
- `grounded support` is supported-case-correct / supported-gold, the positive recall denominator and numerator.
- `incomplete` counts protocol attempts that did not complete with exactly one published tool proposal. Every attempt still incurred a recorded model call unless noted in the source results. `calls / unknown usage` gives recorded model calls and calls with unknown token usage accounting.

## Development 01

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · generic-baseline | 20 | 12 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Analyst · policy-v2 | 20 | 14 | 15 | 0 / 0 → 0 / 0 | 5 / 5 | 5 | 20 / 0 |
| Analyst · format-v2 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Analyst · combined-v2 | 20 | 16 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 1 | 20 / 0 |
| Skeptic · generic-baseline | 20 | 12 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · policy-v2 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · format-v2 | 20 | 8 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 13 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |

Source: [development-01 summary](<evidence/prompt-iteration-v1/batches/development-01/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-01/results.jsonl>), [freeze and prompts](<evidence/prompt-iteration-v1/batches/development-01/freeze.json>).

## Development 02

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · combined-v2 | 20 | 16 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 1 | 20 / 0 |
| Analyst · policy-v3 | 20 | 12 | 17 | 0 / 0 → 0 / 0 | 5 / 5 | 2 | 20 / 0 |
| Analyst · combined-v3 | 20 | 7 | 7 | 0 / 0 → 0 / 0 | 3 / 5 | 13 | 20 / 1 |
| Skeptic · combined-v2 | 20 | 13 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · policy-v3 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v3 | 20 | 16 | 18 | 0 / 0 → 0 / 0 | 4 / 5 | 1 | 20 / 0 |

Source: [development-02 summary](<evidence/prompt-iteration-v1/batches/development-02/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-02/results.jsonl>), [freeze and prompts](<evidence/prompt-iteration-v1/batches/development-02/freeze.json>).

## Development 03

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · combined-v2 | 20 | 17 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 1 | 20 / 0 |
| Analyst · combined-v4 | 20 | 11 | 18 | 1 / 1 → 1 / 1 | 4 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v4 | 20 | 15 | 20 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |

Source: [development-03 summary](<evidence/prompt-iteration-v1/batches/development-03/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-03/results.jsonl>), [freeze and prompts](<evidence/prompt-iteration-v1/batches/development-03/freeze.json>).

## Development 04 · compact representation

This batch uses the same `case_sha256` and the same frozen prompt hashes as earlier runs for `combined-v2`, `policy-v2`, and `combined-v4`. The packet representation changed to compact form, removing duplicate scope labels while retaining the source records. Available quote IDs were derived from actual `validate_claims` known metadata, not gold labels. Therefore, differences in these results cannot be attributed to prompt wording alone.

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · combined-v2 | 20 | 16 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 1 | 20 / 0 |
| Analyst · policy-v2 | 20 | 12 | 14 | 1 / 1 → 1 / 1 | 5 / 5 | 6 | 20 / 0 |
| Analyst · combined-v4 | 20 | 11 | 17 | 2 / 2 → 1 / 1 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 15 | 19 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |
| Skeptic · policy-v2 | 20 | 13 | 18 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v4 | 20 | 16 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |

Source: [development-04-compact summary](<evidence/prompt-iteration-v1/batches/development-04-compact/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-04-compact/results.jsonl>), [freeze and representation record](<evidence/prompt-iteration-v1/batches/development-04-compact/freeze.json>).

## Development 05 · full representation

This batch returned to the full packet representation, using the same frozen 20-case set. It follows the compact representation batch, so a comparison across the two batches cannot isolate prompt wording from representation/order effects.

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · combined-v2 | 20 | 17 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 2 | 20 / 0 |
| Analyst · combined-v5 | 20 | 12 | 19 | 1 / 1 → 1 / 1 | 5 / 5 | 0 | 20 / 0 |
| Analyst · combined-v6 | 20 | 16 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v5 | 20 | 16 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v6 | 20 | 14 | 17 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |

Source: [development-05 summary](<evidence/prompt-iteration-v1/batches/development-05/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-05/results.jsonl>), [freeze and prompts](<evidence/prompt-iteration-v1/batches/development-05/freeze.json>).

Batch-05 negatives: Gemma analyst `combined-v5` had one raw unsupported-supported proposal and one raw ungrounded-support proposal, both accepted. Qwen skeptic `combined-v6` had a correct support-assessment field on 20/20 cases but strict all-fields correctness on 14/20; citation/event identity mismatches and one gate rejection contribute to this composite score. This shows that strict bench correctness is a composite metric, not a count of false factual assessments.

## Development 06 · compact representation

This batch reuses the same 20-case hash and the same `combined-v2` / `combined-v6` frozen prompts as development-05, with compact packet representation. Prompt wording is therefore held constant for those comparisons; the input representation changes. It remains a repeated development set, not an independent sample.

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · combined-v2 | 20 | 16 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 2 | 20 / 0 |
| Analyst · combined-v6 | 20 | 14 | 19 | 1 / 1 → 1 / 1 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 15 | 19 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v6 | 20 | 15 | 19 | 0 / 0 → 0 / 0 | 3 / 5 | 0 | 20 / 0 |

Source: [development-06-compact summary](<evidence/prompt-iteration-v1/batches/development-06-compact/summary.json>), [results](<evidence/prompt-iteration-v1/batches/development-06-compact/results.jsonl>), [freeze and representation record](<evidence/prompt-iteration-v1/batches/development-06-compact/freeze.json>).


## Development 07 · combined-v7 comparison

This completed 120-call batch compares the selected `combined-v7` prompt against `combined-v2` and `generic-baseline` on the development set. The frozen objective remains 27/30 per role, no accepted unsupported or ungrounded support, and positive recall at least 9/10; because these arms contain 20 cases per role, the 27/30 objective is not mechanically applied here. No accepted unsupported or ungrounded support occurred in this batch.

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · generic-baseline | 20 | 13 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Analyst · combined-v2 | 20 | 17 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 1 | 20 / 0 |
| Analyst · combined-v7 | 20 | 15 | 19 | 0 / 0 → 0 / 0 | 4 / 5 | 0 | 20 / 0 |
| Skeptic · generic-baseline | 20 | 12 | 18 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v2 | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |
| Skeptic · combined-v7 | 20 | 16 | 19 | 0 / 0 → 0 / 0 | 5 / 5 | 0 | 20 / 0 |

Source: [development-07 summary](evidence/prompt-iteration-v1/batches/development-07/summary.json), [sanitized results](evidence/prompt-iteration-v1/batches/development-07/results.jsonl), [freeze](evidence/prompt-iteration-v1/batches/development-07/freeze.json), [ledger](evidence/prompt-iteration-v1/batches/development-07/ledger.jsonl), [export hashes and scrub list](evidence/prompt-iteration-v1/batches/export-manifest.json).


## Confirmation run · 30 cases per role and arm

This 120-call confirmation matrix uses the reviewed confirmation set. It includes the analyst `combined-v2` full-packet replication and skeptic `combined-v7` full-packet candidate, each alongside the generic full-packet control. The 27/30 strict-correctness, no-accepted-unsafe-support, and 9/10 positive-recall objective remains unchanged. The first fresh-held-out set had already been seen during v7 selection; this confirmation table is reported separately, without a score comparison to that earlier run. Both selected arms fall short of the 27/30 strict threshold, so no prompt is promoted by this run.

| Role / variant | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · generic-baseline | 30 | 20 | 27 | 2 / 2 → 1 / 1 | 10 / 10 | 0 | 30 / 0 |
| Analyst · combined-v2 | 30 | 25 | 27 | 0 / 0 → 0 / 0 | 10 / 10 | 0 | 30 / 0 |
| Skeptic · generic-baseline | 30 | 21 | 27 | 0 / 0 → 0 / 0 | 10 / 10 | 0 | 30 / 0 |
| Skeptic · combined-v7 | 30 | 24 | 27 | 0 / 0 → 0 / 0 | 9 / 10 | 0 | 30 / 0 |

Source: [confirmation summary](evidence/prompt-iteration-v1/batches/confirmation/summary.json), [sanitized results](evidence/prompt-iteration-v1/batches/confirmation/results.jsonl), [run freeze](evidence/prompt-iteration-v1/batches/confirmation/freeze.json), [candidate-selection freeze](evidence/prompt-iteration-v1/batches/confirmation/candidate-selection-confirmation.json), [ledger](evidence/prompt-iteration-v1/batches/confirmation/ledger.jsonl), [export hashes and scrub list](evidence/prompt-iteration-v1/batches/export-manifest.json).

## Identifier-invariance fixture

[development-opaque.json](evidence/prompt-iteration-v1/development-opaque.json) is deterministically derived from the existing `development-new.json` cases. Its case IDs append `-opaque`; source IDs, record IDs, and event IDs are replaced consistently with domain-separated SHA-256 identifiers, including expected source mappings. Claim text, entity names, source text, dates, category labels, and expected classifications are preserved. This is a regression fixture for identifier invariance, not a new or independent case set.

## Opaque identifier-invariance run · interrupted and recovered

The original batch's result and ledger files were interrupted by the reboot and contain NUL tails; the summary file is empty. The valid result prefix has 28 scored rows. A read-only audit of all 40 original `room.db` files confirms 40 admitted model and tool calls with known usage, 39 public message events, and one denied `room_message` result. Twelve original calls are absent from the result prefix. Those 12 role/case keys are the same cases later run in recovery (11 original DB public messages and one denial), so recovery added 12 repeated calls, not 12 new independent cases. The SQLite audit resolves the final analyst case-14 ledger intent as an admitted call with an `ok` public-message event, although its JSONL result row is missing. Protocol-completion fields for the other DB-only rows are absent; they remain unscored and are not counted as observed incomplete attempts. No DB-only message was inserted or rescored.

The table below preserves the existing score rows: 28 original JSONL-prefix rows plus 12 recovery rows, 20 per role. It does not score the 12 additional original calls found in SQLite. There were 52 actual calls across the original batch and recovery, all with known usage.

| Role / variant | n | Strict | Accepted | Grounded support | Raw unsupported support accepted | Raw ungrounded support accepted | Scored rows / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · selected (Gemma) | 20 | 16 | 19 | 5 / 5 | 0 | 0 | 20 / 0 |
| Skeptic · selected (Qwen) | 20 | 13 | 20 | 4 / 5 | 0 | 0 | 20 / 0 |

Source: [original partial freeze](evidence/prompt-iteration-v1/batches/opaque/freeze.json), [original partial results](evidence/prompt-iteration-v1/batches/opaque/results.jsonl), [original partial ledger](evidence/prompt-iteration-v1/batches/opaque/ledger.jsonl), [read-only SQLite audit counts and hashes](evidence/prompt-iteration-v1/batches/opaque/sqlite-audit.json), [recovery freeze](evidence/prompt-iteration-v1/batches/opaque-recovery/freeze.json), [recovery results](evidence/prompt-iteration-v1/batches/opaque-recovery/results.jsonl), [recovery ledger](evidence/prompt-iteration-v1/batches/opaque-recovery/ledger.jsonl), [combined score summary](evidence/prompt-iteration-v1/batches/opaque-combined/summary.json), [interruption integrity metadata](evidence/prompt-iteration-v1/batches/opaque/recovery-metadata.json).


## Held-out evaluation · 30 cases per role and arm

This is the frozen held-out batch, with 180 completed result records. The predeclared objective remains strict correctness of at least 27/30 per role, no accepted unsupported or ungrounded support, and positive recall of at least 9/10. The objective and thresholds were not changed after generation. No arm meets the strict threshold. `selected` has one incomplete analyst protocol result, one accepted unsupported and ungrounded analyst support proposal, and 7/10 positive recall for the skeptic. These held-out measurements do not promote a prompt.

| Role / arm | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · control-compact | 30 | 21 | 29 | 1 / 1 → 1 / 1 | 10 / 10 | 0 | 30 / 0 |
| Analyst · control-full | 30 | 22 | 28 | 1 / 1 → 1 / 1 | 10 / 10 | 0 | 30 / 0 |
| Analyst · selected | 30 | 23 | 27 | 1 / 1 → 1 / 1 | 10 / 10 | 1 | 30 / 0 |
| Skeptic · control-compact | 30 | 21 | 29 | 0 / 0 → 0 / 0 | 9 / 10 | 0 | 30 / 0 |
| Skeptic · control-full | 30 | 20 | 28 | 0 / 0 → 0 / 0 | 9 / 10 | 0 | 30 / 0 |
| Skeptic · selected | 30 | 20 | 28 | 0 / 0 → 0 / 0 | 7 / 10 | 0 | 30 / 0 |

Source: [held-out summary](evidence/prompt-iteration-v1/batches/heldout/summary.json), [sanitized results](evidence/prompt-iteration-v1/batches/heldout/results.jsonl), [freeze](evidence/prompt-iteration-v1/batches/heldout/freeze.json), [ledger](evidence/prompt-iteration-v1/batches/heldout/ledger.jsonl), [export hashes and scrub list](evidence/prompt-iteration-v1/batches/export-manifest.json).


## Challenge evaluation · 20 cases per role and arm

The completed challenge batch contains 80 result records. The held-out objective remains unchanged at 27/30 strict correctness per role, no accepted unsupported or ungrounded support, and positive recall of at least 9/10. That 27/30 objective is not mechanically applied to this 20-case-per-arm challenge batch; these challenge results are recorded as a separate diagnostic.

| Role / arm | n | Strict | Accepted | Raw unsafe → accepted (unsupported / ungrounded) | Grounded support | Incomplete | Calls / unknown usage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Analyst · control-full | 20 | 7 | 17 | 1 / 1 → 1 / 1 | 3 / 6 | 0 | 20 / 0 |
| Analyst · selected | 20 | 10 | 18 | 0 / 0 → 0 / 0 | 4 / 6 | 0 | 20 / 0 |
| Skeptic · control-full | 20 | 14 | 19 | 1 / 1 → 1 / 1 | 6 / 6 | 0 | 20 / 0 |
| Skeptic · selected | 20 | 14 | 19 | 0 / 0 → 0 / 0 | 6 / 6 | 0 | 20 / 0 |

Source: [challenge summary](evidence/prompt-iteration-v1/batches/challenge/summary.json), [sanitized results](evidence/prompt-iteration-v1/batches/challenge/results.jsonl), [freeze](evidence/prompt-iteration-v1/batches/challenge/freeze.json), [ledger](evidence/prompt-iteration-v1/batches/challenge/ledger.jsonl), [export hashes and scrub list](evidence/prompt-iteration-v1/batches/export-manifest.json).

## Accounting and interpretation

Across development batches 01–07, the result files contain 800 attempts and 800 recorded model calls. One call has unknown usage accounting; 36 development protocol attempts are incomplete, with the one failed call and unknown usage in development-02. The same 20-case `case_sha256` appears in all seven development freezes, so these are repeated development cases across iterations, not 800 independent cases. The original opaque batch has 40 SQLite-confirmed calls; its result prefix contains 28 rows, while 12 more original calls overlap the 12 recovery calls on the same role/case keys. The analyst case-14 ledger intent is resolved as an admitted call with a public message, although its JSONL result is absent. The held-out, challenge, and confirmation batches contain 180, 80, and 120 result records. The isolated model-backed experiment has 1,232 confirmed model calls, 1,220 result rows, 1,195 tool calls, 37 observed incomplete attempts, and one call with unknown token usage. Twelve DB-only opaque attempts have unknown protocol-completion status and are not counted as observed incomplete; one was denied by the publication gate. Development, held-out, challenge, confirmation, and opaque results remain experimental; no prompt is promoted and serving behavior is unchanged. Results vary by role and iteration; changes are not uniformly wins. All historical failures remain in place. The earlier legacy results `20/30` and `14/30` remain unchanged. The [accounting summary](evidence/prompt-iteration-v1/accounting-summary.json) separates this experiment from native room activity and records per-batch calls, tool counts, tokens, and incomplete attempts.

The native dashboard evidence covers seven unique room IDs. Their GET counts sum to 55 model admissions, 50 tool admissions, 1,802,240 reserved tokens, 490,455 recorded input tokens, 4,358 recorded output tokens, and 3 unknown-usage calls. Combined with the experiment, counters show 1,287 confirmed or admitted model calls, 1,245 tool calls, and 42,172,416 reserved tokens. Recorded input and output counters sum to 2,849,322 and 155,377; these are not exact total token use because four calls have unknown usage accounting. The older phase's 112 calls are excluded. Native activity is separate from prompt evaluation and is not evidence of prompt performance. The seven endpoints were verified with unauthenticated GETs to `/api/research/rooms/{room_id}`; counts match the [native room summary](evidence/prompt-iteration-v1/native/rooms-summary.json).

## Frozen prompt hashes

SHA-256 below is computed over each frozen prompt's `instructions` and `task` strings serialized as canonical JSON (sorted keys, compact separators, UTF-8). The linked freeze file is the source record.

| Variant | SHA-256 | Frozen source |
|---|---|---|
| generic-baseline | `f28dd8cfbccc09e57b6b12b4843bfee756c622f849e067168895c8fc2b1e80c5` | [development-01](<evidence/prompt-iteration-v1/batches/development-01/freeze.json>) |
| policy-v2 | `b85cc94d49e05679bba11e97f67526f81a56ce073364d85534402e25302027f6` | [development-01](<evidence/prompt-iteration-v1/batches/development-01/freeze.json>), [development-04-compact](<evidence/prompt-iteration-v1/batches/development-04-compact/freeze.json>) |
| format-v2 | `1916dce70af104c901a46aa39ad117916d36f0b5341d03675320c4c13af50e2c` | [development-01](<evidence/prompt-iteration-v1/batches/development-01/freeze.json>) |
| combined-v2 | `6e963ed0852a5a1adff7ff19ee8a1049c00465967f3ab68b7b051eb3888616ba` | [development-01](<evidence/prompt-iteration-v1/batches/development-01/freeze.json>), [development-02](<evidence/prompt-iteration-v1/batches/development-02/freeze.json>), [development-03](<evidence/prompt-iteration-v1/batches/development-03/freeze.json>), [development-04-compact](<evidence/prompt-iteration-v1/batches/development-04-compact/freeze.json>), [development-05](<evidence/prompt-iteration-v1/batches/development-05/freeze.json>), [development-06-compact](<evidence/prompt-iteration-v1/batches/development-06-compact/freeze.json>) |
| policy-v3 | `47df247d4239cf1136aa2d0daca11dab234519f0c106747ce4e5aafe9a427ab4` | [development-02](<evidence/prompt-iteration-v1/batches/development-02/freeze.json>) |
| combined-v3 | `23a3c0f2c1e33f4c63dab3f2695034cdf735cf7975d928b95e9c69562e7fd667` | [development-02](<evidence/prompt-iteration-v1/batches/development-02/freeze.json>) |
| combined-v4 | `5201a21014de1b806b8330472cea15f19f61c069f7c90e669dac1f114ff75f3f` | [development-03](<evidence/prompt-iteration-v1/batches/development-03/freeze.json>), [development-04-compact](<evidence/prompt-iteration-v1/batches/development-04-compact/freeze.json>) |
| combined-v5 | `44f0b232ae0e58fa81bd1e4b6b47c08ca51a0faa5b33cbc754b1f57bb3b3e142` | [development-05](<evidence/prompt-iteration-v1/batches/development-05/freeze.json>) |
| combined-v6 | `3f11719a1e759c529be87b8bc467026cee73a0cb077f65dd222609bfead0e763` | [development-05](<evidence/prompt-iteration-v1/batches/development-05/freeze.json>), [development-06-compact](<evidence/prompt-iteration-v1/batches/development-06-compact/freeze.json>) |

The earlier legacy `20/30` and `14/30` results are not included in these three batch tables and have not been edited or overwritten.
