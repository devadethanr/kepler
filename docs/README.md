# Project Docs

This directory now separates current source-of-truth docs from historical planning artifacts.

## Current Source Of Truth

- `quickstart.md` — Docker-first local setup, auth flow, and day-one commands.
- `architecture/v2_adk_fastapi_design.md` — current runtime architecture for FastAPI, ADK, Reflex, the scheduler, and the file-backed state model.
- `architecture/implementation_plan+extended.md` — shipped decisions plus the remaining engineering roadmap.
- `progress/current-task.md` — current project status and known blockers.
- `progress/todo+extended.md` — prioritized backlog based on the code as it exists today.
- `progress/plan-progress-phase.md` — phase-by-phase implementation status without environment-specific secrets.
- `runbooks/kite-mcp-setup.md` — local Kite MCP and auth workflow.

## Historical References

These files are kept for context, not as active specifications:

- `progress/todos.md`
- `progress/upgrade.md`
- `reference/project_design.md`
- `reference/swingtradev3_design_v6.pdf`

If a historical doc conflicts with code, config, or the current architecture docs, trust the code and the current docs.

## Runtime Strategy Docs

Code-adjacent strategy material still lives under `swingtradev3/strategy/`:

- `SKILL.md`
- `research_program.md`
- `analyst_program.md`

Those files drive agent behavior and are part of runtime execution, so they are intentionally outside `docs/`.
