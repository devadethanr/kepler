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

- [Current handoff/read order](plans/kepler-research-revamp/README.md) — revision 7 after `ae7d45f`; room/UI repaired, Codex installed, tuning candidates inactive.
- [Post-tuning review](plans/kepler-research-revamp/POST_TUNING_REVIEW.md) — confirmation replay, tests, source diagnostics and actual limits.
- [Fresh-source implementation](plans/kepler-research-revamp/FRESH_SOURCE_IMPLEMENTATION.md) and [local Codex handoff](plans/kepler-research-revamp/FRESH_SOURCE_HANDOFF.md) — active next scope.
- [Work history](plans/kepler-research-revamp/WORK_HISTORY.md), [prompt results](plans/kepler-research-revamp/PROMPT_TUNING_RESULTS.md) and [phase findings](plans/kepler-research-revamp/NEXT_PHASE_FINDINGS.md) — completed work and frozen evidence.
- [Runbook](plans/kepler-research-revamp/RESEARCH_ROOM_RUNBOOK.md) and [reboot checks](plans/kepler-research-revamp/REBOOT_BROWSER_CHECKS.md) — :8502 Research Desk and supported local services.
- [Overall plan](plans/kepler-research-revamp/IMPLEMENTATION_PLAN.md) — later GIFT/Singapore, informational TimesFM, scheduled rooms and harness improvements.

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
