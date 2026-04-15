# swingtradev3 Quickstart

This project is run from Docker via the `swingtradev3/Makefile`. Use the Makefile commands instead of running tests or services directly on the host.

## Prerequisites

1. Docker and Docker Compose
2. Zerodha Kite Connect credentials
3. NVIDIA NIM API key
4. Tavily API key
5. Optional: Firecrawl, Groq, Gemini, Telegram credentials

## 1. Configure the app

Run all local commands from `swingtradev3/`:

```bash
cd swingtradev3
cp .env.example .env
```

Fill `.env` with the credentials you actually use, then review `config.yaml` for trading mode, capital, and risk settings. The default mode should stay `paper` until the full workflow has been validated.

## 2. Start the local stack

```bash
make dev-detach
```

The dev stack currently exposes:

- FastAPI API: `http://localhost:8001`
- Reflex frontend: `http://localhost:8502`
- Reflex backend: `http://localhost:8002`
- Kite MCP sidecar: `http://localhost:8081`

Use `make logs-app`, `make logs-dashboard`, or `make logs-mcp` if a service does not come up cleanly.

## 3. Authenticate Kite

```bash
make login
```

Open the printed Kite login URL, complete the browser flow, and paste the final redirected URL back into the terminal. The session is persisted under `swingtradev3/context/auth/kite_session.json`.

## 4. Use the system

Open `http://localhost:8502` and use the current dashboard pages:

- Command Center
- Portfolio
- Research
- Approvals
- Knowledge Graph
- Agent Activity

The research pipeline can be triggered from the Research page or through `POST /scan`. Approved trades flow through `/approvals/{ticker}/yes`, which triggers the ADK order agent in the background.

## 5. Validate and debug

All validation runs in Docker:

```bash
make test
make test-file file=tests/test_api/test_scan.py
```

At the time of this refresh, `tests/test_agents/test_execution_monitor.py` is a known failing test because the execution monitor now skips work outside market hours and the test has not been updated for that guard.

## Safety Notes

- Keep `trading.mode: paper` until the full order and GTT flow is validated in market hours.
- `context/`, `logs/`, and `reports/` contain runtime state; review changes there carefully before committing.
- Telegram should currently be treated as a notifications-first channel. The dashboard and API are the primary control plane.
