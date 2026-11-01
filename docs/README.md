# Project Docs

This directory now separates current source-of-truth docs from historical planning artifacts.

## Current Source Of Truth

- `quickstart.md` — Docker-first local setup, auth flow, and day-one commands.
- `architecture/v2_adk_fastapi_design.md` — current runtime architecture for FastAPI, ADK, Reflex, the scheduler, and the file-backed state model.
- `architecture/implementation_plan+extended.md` — shipped decisions plus the remaining engineering roadmap.
- `architecture/live_trading_one_shot_plan.md` — the current live-execution hardening and autonomy plan based on `findings.md` and broker research.
- `architecture/agent_cognition_architecture.md` — the target Slow Brain / Fast Brain / Memory / Policy / Recovery design, with explicit agent roles.
- `architecture/agent_cognition_implementation_plan.md` — the repo-specific implementation sequence for the cognition and execution overhaul.
- `progress/current-task.md` — current project status and known blockers.
- `progress/todo+extended.md` — prioritized backlog based on the code as it exists today.
- `progress/plan-progress-phase.md` — phase-by-phase implementation status without environment-specific secrets.
- `runbooks/kite-mcp-setup.md` — local Kite MCP and auth workflow.

## Personal Kepler Research Revamp

- [Research handoff and read order](plans/kepler-research-revamp/README.md) — revision 5, Codex selected after the completed local spike reports at `8d7ddfc`; covers collaborative research rooms, local models, context/browser skills, TimesFM and live discussion UI. The implementation is planned; this documentation update does not claim it is deployed.
- [Pre-implementation configuration audit](plans/kepler-research-revamp/PRE_IMPLEMENTATION_AUDIT.md) — required reading before tests or implementation; includes a confirmed destructive graph-test target risk and the configuration migration inventory.
- [Codex implementation](plans/kepler-research-revamp/CODEX_IMPLEMENTATION.md) — selected App Server + tested local adapter architecture, external-thread collaboration and practical implementation order for the user’s own workspace.
- [Completed spike review](plans/kepler-research-revamp/SPIKE_REVIEW.md) — measured evidence and limitations; Codex is selected for implementation.
- [Next validation plan](plans/kepler-research-revamp/NEXT_VALIDATION_PLAN.md) — focused grounding and adapter checks during implementation; do not repeat the completed matrix unchanged or reopen runtime selection.
- [Original spike procedure](plans/kepler-research-revamp/INITIAL_SPIKE_PLAN.md), [initial findings](plans/kepler-research-revamp/SPIKE_FINDINGS.md) and [follow-up findings](plans/kepler-research-revamp/FOLLOW_UP_FINDINGS.md) — retain the executed experiment scope and operator-reported measurements for reproducibility.

## Historical References

These files are kept under `docs/old/` for context, not as active specifications:

- `old/todos.md`
- `old/upgrade.md`
- `old/project_design.md`
- `old/swingtradev3_design_v6.pdf`

If a historical doc conflicts with code, config, or the current architecture docs, trust the code and the current docs.

## Runtime Strategy Docs

Code-adjacent strategy material still lives under `swingtradev3/strategy/`:

- `SKILL.md`
- `research_program.md`
- `analyst_program.md`

Those files drive agent behavior and are part of runtime execution, so they are intentionally outside `docs/`.
