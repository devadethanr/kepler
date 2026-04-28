# Repository Guidelines

## Project Structure & Module Organization
Core application code lives in `swingtradev3/`. Key areas are `api/` for FastAPI routes and background tasks, `agents/` for research/execution workflows, `data/`, `risk/`, `paper/`, and `tools/` for market, risk, and execution logic, and `dashboard/` for the Reflex UI. Tests live in `swingtradev3/tests/` with focused suites such as `test_api/`, `test_agents/`, and `test_evaluation/`. Keep product docs in `docs/`; keep strategy markdown in `swingtradev3/strategy/`. Treat `dashboard_old/` as legacy unless a change explicitly targets it.

## Build, Test, and Development Commands
Run commands from `swingtradev3/` so the local `Makefile` paths resolve correctly.

- `make dev`: build and start the dev stack in the foreground.
- `make dev-detach`: start FastAPI, dashboard, and `kite-mcp` in the background.
- `make test`: run the full `pytest` suite inside the app container.
- `make test-file file=tests/test_api/test_scan.py`: run one test module.
- `make lint`: run `ruff check .`
- `make format`: run `ruff format .`
- `make login`: launch Kite auth inside the app container.

## Coding Style & Naming Conventions
Target Python 3.12. Use 4-space indentation, type-aware Python, and keep lines within Ruff’s 100-character limit. Use `snake_case` for modules, functions, and files, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for constants. Follow the repository split described in `CLAUDE.md`: keep trading logic and operator-facing procedures in `swingtradev3/strategy/*.md`, and keep Python focused on execution.

## Testing Guidelines
The project uses `pytest` with `pytest-asyncio` (`asyncio_mode = auto`). Name tests `test_*.py` and group them by subsystem under `swingtradev3/tests/`. Prefer focused regression tests near the affected area, and cover mode-sensitive behavior (`backtest`, `paper`, `live`) when changing execution, risk, or API flow.

## Commit & Pull Request Guidelines
Recent history uses short lowercase subjects such as `updated` and `phase 4 completed`. Keep commits concise, but make them more specific and imperative when possible, for example `api: tighten approval validation`. PRs should include a clear summary, affected runtime mode(s), test commands run, and screenshots for dashboard changes. Link related docs or issues when changing strategy, config, or operator workflows.

## Security & Configuration Tips
Secrets belong in `swingtradev3/.env`; start from `swingtradev3/.env.example` and never commit filled credentials. Review changes under `swingtradev3/context/` carefully, since many JSON files are runtime state and can change incidentally. Do not commit generated data under `swingtradev3/context/daily/`, `swingtradev3/context/research/`, `swingtradev3/reports/`, or `swingtradev3/.backtest_cache/`.
