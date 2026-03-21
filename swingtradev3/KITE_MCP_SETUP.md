# Kite MCP Setup

This file records the working self-hosted Kite MCP setup and the auth tweaks used in this repo.

## Services

- `app`: Python runtime for `swingtradev3`
- `kite-mcp`: self-hosted Zerodha `kite-mcp-server`

The Docker stack is defined in [docker-compose.yml](/home/devadethanr/projects/kepler/docker-compose.yml).

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
- host port publish: `8080:8080`

Why `8080:8080` matters:
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

Use the official Kite login helper:

```bash
docker compose exec app python -m swingtradev3.auth.kite.login
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
- LTP
- instrument token lookup
- historical candles
- order placement
- GTT placement / modification / deletion

Key files:

- [client.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/client.py)
- [login.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/login.py)
- [session_store.py](/home/devadethanr/projects/kepler/swingtradev3/auth/kite/session_store.py)

## Commands

Bring up the stack:

```bash
docker compose up --build -d
```

Run the auth helper:

```bash
docker compose exec app python -m swingtradev3.auth.kite.login
```

Run the auth tests inside Docker:

```bash
docker compose exec app python -m pytest -q swingtradev3/tests/test_kite_auth.py
```

Check MCP logs:

```bash
docker compose logs --tail=160 kite-mcp
```

## Practical Notes

- The status page at `http://localhost:8080/` only proves the HTTP server responded. It does not prove Kite auth completed.
- The persisted session file is the app’s live auth source of truth right now.
- If the session expires, rerun the auth helper and overwrite the saved session.
