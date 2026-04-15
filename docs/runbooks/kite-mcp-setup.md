# Kite MCP Setup

This file records the working self-hosted Kite MCP setup and the auth flow currently used by this repo.

## Services

- `app`: FastAPI + ADK runtime for `swingtradev3`
- `kite-mcp`: self-hosted Zerodha `kite-mcp-server`

Local development is normally started from `swingtradev3/` through the Makefile, which targets [docker-compose.dev.yml](/home/devadethanr/projects/kepler/docker-compose.dev.yml).
The production-oriented compose file remains [docker-compose.yml](/home/devadethanr/projects/kepler/docker-compose.yml).

## Why Self-Hosted MCP

The hosted Zerodha MCP service disables some sensitive trading operations.
This project uses the self-hosted server so the full trading tool surface is available.

Upstream repo:
- https://github.com/zerodha/kite-mcp-server

## Docker Setup

The MCP sidecar is built from source using [Dockerfile.kite-mcp](/home/devadethanr/projects/kepler/Dockerfile.kite-mcp).

Important runtime settings:

- `APP_MODE=http`
- `APP_PORT=8080`
- `APP_HOST=0.0.0.0`
- dev host port publish: `8081:8080`
- prod host port publish: `8080:8080`

Why host port publishing matters:
- Zerodha redirects the browser back to a local URL after login
- without publishing the port, the host browser cannot reach the self-hosted MCP container

## Env Requirements

Set these in `swingtradev3/.env`:

- `KITE_API_KEY`
- `KITE_API_SECRET`
- `KITE_MCP_URL=http://kite-mcp:8080/mcp`

## What We Learned About Auth

The MCP server itself was healthy and exposed all tools, but the MCP-native login path was not reliable enough for this project.

Observed behavior:

- browser redirect to `http://localhost:8080/` reached the MCP status page
- the MCP session stayed alive
- repeated `get_profile` calls still failed with `Invalid api_key or access_token`

So the final approach is:

- browser login remains manual
- `request_token -> access_token` exchange is handled by our Python code
- the resulting Kite session is saved locally

## Final Working Auth Flow

Use the current repository workflow:

```bash
cd swingtradev3
make login
```

Steps:

1. Open the printed Kite login URL.
2. Complete login and authorization in the browser.
3. Copy the final redirected URL from the browser address bar.
4. Paste that full URL into the terminal helper.

The helper:

- extracts `request_token`
- calls Kite `generate_session`
- verifies `profile()`
- saves the session at `swingtradev3/context/auth/kite_session.json`

You can also paste only the raw `request_token`.

## Direct Kite Session Usage

The app now prefers the persisted direct Kite session for live access, with MCP still available as a fallback path.

Direct session-backed helpers now cover:

- profile
- holdings
- positions
- GTT listing
- order placement path wiring
- instrument token lookup
- historical candles path wiring
- GTT placement / modification / deletion path wiring

Key files:

- [client.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/client.py)
- [login.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/login.py)
- [session_store.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/session_store.py)

## Commands

Bring up the dev stack:

```bash
cd swingtradev3
make dev-detach
```

Run the auth helper:

```bash
cd swingtradev3
make login
```

Run tests through the repository workflow:

```bash
cd swingtradev3
make test
```

Check service logs:

```bash
cd swingtradev3
make logs-mcp
```

## Practical Notes

- In the dev stack, the local MCP status page is `http://localhost:8081/`. In the production compose file it is `http://localhost:8080/`.
- The status page only proves the HTTP server responded. It does not prove Kite auth completed.
- The persisted session file is the app’s live auth source of truth right now.
- If the session expires, rerun the auth helper and overwrite the saved session.
