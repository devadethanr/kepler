# Retained research prompt candidates

These are prompt documents, not separate executable agents. They remain experimental:
the installed analyst/skeptic threads still use `research_room/codex.py:INSTRUCTIONS`.
The final 30-case confirmation missed the 27/30 objective, so no candidate is active.

| Files | Retained profile / experiment | Purpose |
|---|---|---|
| [evidence-agent.md](evidence-agent.md), [contract-agent.md](contract-agent.md) | Qwen / skeptic, `combined-v7`, full packets | Evidence policy plus single-claim assessment instructions. |
| [evidence-analyst.md](evidence-analyst.md), [contract-analyst.md](contract-analyst.md) | Gemma / analyst, `combined-v2`, full packets | Evidence policy plus single-claim assessment instructions. |

`evidence-*.md` defines how a participant treats evidence, uncertainty and scope.
`contract-*.md` defines the evaluation's exact single-claim output. The latter tells
the model to copy a supplied claim and publish to `room` with `position=question`;
it must not be installed as an open-ended discussion prompt.

The four retained files were renamed byte-for-byte on 2 November 2026:

| Historical filename | Current filename |
|---|---|
| `evidence-v7.md` | `evidence-agent.md` |
| `contract-v7.md` | `contract-agent.md` |
| `evidence-v2.md` | `evidence-analyst.md` |
| `contract-v2.md` | `contract-analyst.md` |

Experiment selectors retain their original names. The loader resolves old filenames
for historical selection hashes and recovery checks. Frozen evidence/source snapshots
retain the original filenames and bytes. Other versioned files remain available for
reproducing unsuccessful candidates; they are not additional selected agents.

See [work history](../../../docs/plans/kepler-research-revamp/WORK_HISTORY.md),
[measured findings](../../../docs/plans/kepler-research-revamp/PROMPT_TUNING_FINDINGS.md)
and [all results](../../../docs/plans/kepler-research-revamp/PROMPT_TUNING_RESULTS.md).
