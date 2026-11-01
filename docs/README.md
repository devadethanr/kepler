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

- [Research handoff and read order](plans/kepler-research-revamp/README.md) — revision 6, installed local room at `aebd42d`; Codex remains selected.
- [Activated-room review](plans/kepler-research-revamp/ROOM_REVIEW.md) — independent checks, reproducible findings and actual grounding limits.
- [Next implementation phase](plans/kepler-research-revamp/NEXT_PHASE_IMPLEMENTATION.md) and [local Codex handoff](plans/kepler-research-revamp/NEXT_PHASE_HANDOFF.md) — conversation/lifecycle fixes, claim/evidence quality and focused verification on the existing setup.
- [Local activation](plans/kepler-research-revamp/LOCAL_ACTIVATION.md) and [runbook](plans/kepler-research-revamp/RESEARCH_ROOM_RUNBOOK.md) — :8502 Research Desk, host services and supported start/stop procedure.
- [Configuration audit](plans/kepler-research-revamp/PRE_IMPLEMENTATION_AUDIT.md) — historical inventory with graph/Toolbox precedence and test-target guard remediation recorded.
- [Overall implementation plan](plans/kepler-research-revamp/IMPLEMENTATION_PLAN.md) — installed foundation plus later news, market context, forecasts and scheduled research.

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
