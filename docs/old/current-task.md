# Current Project Status

> Last Updated: April 16, 2026

## Current Runtime Shape

The codebase is currently a **FastAPI + Google ADK + Reflex** system running through Docker Compose:

- `api/main.py` starts FastAPI, creates runtime directories, starts the 24-hour scheduler, and warms heavy models in the background.
- `agents/research/pipeline.py` runs the research flow as an ADK `SequentialAgent`.
- `api/tasks/scheduler.py` drives the day-cycle, event bus, activity tracking, and research/execution triggers.
- `dashboard/` is the active Reflex UI. `dashboard_old/` is legacy.

## Implemented And Working In Code

- Research pipeline: regime -> filter -> scan -> score -> save -> knowledge graph
- Knowledge graph: markdown wiki, index, graph JSON, dashboard APIs
- Scheduler/event bus/activity manager: persisted event history, failed-event tracking, scheduler phase reporting
- Dashboard shell: Command Center, Portfolio, Research, Approvals, Knowledge Graph, Agent Activity
- Docker-first workflow via `swingtradev3/Makefile`

## Current Gaps

### High Priority

- Finish the Reflex dashboard beyond the current shell pages:
  - Trade Journal page
  - Learning page
  - richer Approvals page with live pending approvals instead of placeholder UI
- Bring the docs and naming fully in line with the current Reflex-based stack

### Medium Priority

- Fix the execution-monitor trailing test after the market-hours guard change
- Validate the full Dockerized test suite end to end with the Makefile workflow
- Complete the failed-event retry path beyond the current placeholder API response

### Low Priority

- Add API reference documentation
- Add a documented tunnel/ngrok workflow for remote dashboard access

## Validation Notes

- Dockerized validation must be run through `swingtradev3/Makefile`
- Confirmed current failure:
  - `make test-file file=tests/test_agents/test_execution_monitor.py`
- Failure reason:
  - the test expects trailing-stop logic to run unconditionally, but `agents/execution/monitor.py` now skips work outside market hours

## Useful Commands

```bash
cd swingtradev3
make dev
make dev-detach
make test
make test-file file=tests/test_api/test_scan.py
make logs-app
make logs-dashboard
```
