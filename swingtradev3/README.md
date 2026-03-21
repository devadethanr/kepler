# swingtradev3

Autonomous swing-trading research and execution system for Indian equities.

This repository follows the v6 design document and is organized around:

- `research_agent` for nightly scanning and morning briefing
- `execution_agent` for approvals, entries, GTT lifecycle, and reconciliation
- shared `backtest`, `paper`, and `live` adapters behind `trading.mode`

## Quick start

1. Create `swingtradev3/.env` from `.env.example`.
2. Review and update `swingtradev3/config.yaml`.
3. Install dependencies from `swingtradev3/requirements.txt`.
4. Run tests with `python -m pytest -q swingtradev3/tests`.
5. Start a backtest with `python -m swingtradev3.main --mode backtest`.

## Docker

The recommended deployment is `docker compose` with two services:

- `app`: the Python swingtradev3 runtime
- `kite-mcp`: the Go-based Kite MCP sidecar

Bring it up with:

```bash
docker compose up --build -d
```

Notes:

- `swingtradev3/.env` is injected at runtime for both services
- `config.yaml`, `strategy/`, `context/`, `logs/`, and `reports/` are mounted into the Python app
- `.backtest_cache` is kept in a named Docker volume
- the `kite-mcp` service builds the real Zerodha server from source using `Dockerfile.kite-mcp`
- override `KITE_MCP_REF` in `docker-compose.yml` if you want a different tag or branch
- `kite-mcp` publishes port `8080` to the host so the local Zerodha login redirect can return to the self-hosted server

### Kite login

Use the official Kite Connect request-token flow for the app login:

1. Set your Zerodha app redirect URL to a URL you can copy from after login.
2. Start the stack with `docker compose up --build -d`.
3. Run `docker compose exec app python -m swingtradev3.auth.kite.login`.
4. Open the printed Kite login URL in your browser and complete the authorization.
5. Copy the final redirected URL from the browser address bar and paste it into the helper.
6. The helper exchanges `request_token` in code, verifies `profile()`, and stores the session in `swingtradev3/context/auth/kite_session.json`.

The browser step is manual. The `request_token -> access_token` exchange is done in code.

## Current status

Implemented:

- normalized config and typed models
- file-backed state contracts under `context/`
- indicator engine and shared paper execution core
- risk engine, simulated GTT handling, and order adapter layer
- LLM client/router/prompt scaffolding
- research and execution agent scaffolding
- trade review, stats, lesson generation, and Docker deployment files
- initial tests for config, indicators, risk, simulator behavior, and reconciliation

Current stage:

- the package skeleton and runtime wiring are in place
- container-first deployment for app + MCP is now defined
- paper/backtest-safe execution paths exist

Known gaps:

- live Kite data/order/GTT adapters now route toward self-hosted MCP, but argument mapping may still need refinement against your exact broker workflow
- Telegram and some external data providers currently degrade to adapter stubs or logging-only behavior
- backtest replay is scaffolded, but not yet a full historical replay engine
- the full test suite was not completed in this environment because `pytest` was unavailable on path and the longer validation run was interrupted
