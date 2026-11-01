Follow-up: [NEXT_PHASE_FINDINGS.md](NEXT_PHASE_FINDINGS.md) supersedes the original UI/lifecycle limits below and records the current source and checks. Serving profiles remain unchanged.

# Normal personal Kepler app: research room activated

1 November 2026, follow-up to the first-room implementation. “Production API” in the earlier report meant the user's normally running Kepler backend; it was not a separate commercial deployment or an approval requirement. The user authorized activating and testing the normal personal setup.

**Research Desk now runs at http://localhost:8502 with the normal Kepler Postgres database.** The normal API was recreated to load the new code. The trading worker, broker MCP, graph and database were not restarted. Research model/API/worker processes remain running for use.

## Connected path

```text
Existing dashboard :8502
  → existing API :8001 /research (existing API-key authentication)
  → owner-only Unix socket shared through the existing logs mount
  → host research API
  → normal Postgres room history + native research worker
  → pinned Codex adapter / Gemma E4B and Qwen3.5-9B services
```

`api/routes/research_proxy.py` forwards JSON, status/error responses and SSE with `Last-Event-ID`; it does not grant additional tools or broker authority. The Unix socket is mode 0600 and is not a LAN HTTP endpoint. The host API refuses to replace an ordinary file or another live socket. API-key checks remain enforced at both ends; an unauthenticated request to the normal API returns 403, and an unavailable host service returns 503.

`research_room/host_api.py` owns the socket, including cleanup/restart. `ops/research_services.py` prepares private configuration/environment files using the existing app's connection settings. Keys/passwords are not command-line arguments or output, and none of those environment files are committed. The pinned binaries/weights, context/output settings and resource floors are unchanged.

Models and host API use transient user services. The worker uses a transient managed **scope**. Actual normal-path testing found that Ubuntu's user-namespace policy denies `bwrap` UID mapping when launched by the user's systemd service manager, while the existing IDE context permits the tested sandbox. A scope inherits the working caller context. The launcher probes namespace creation before starting it. **No AppArmor profile, kernel setting, host privilege or sandbox restriction was disabled.** If starting from a different terminal fails the probe, use the working IDE terminal rather than weakening the sandbox.

## Start, inspect and stop

The normal Docker stack must be running. From `swingtradev3/`:

```bash
make research-start
make research-status
make research-stop
```

The Makefile uses the retained `~/.local/state/kepler-rooms/venv/bin/python` automatically when available; `RESEARCH_PYTHON=/path/to/python` remains configurable. Starting an already running research stack is idempotent. Stopping affects only these research units, not trading/protection:

- `kepler-research-api.service`
- `kepler-research-models.service`
- `kepler-research-worker.scope`

These transient units are not boot activation. After reboot, start them from the working IDE terminal. Configuration lives at `~/.local/state/kepler-rooms/local.json`; private service environments and worker logs are in the same state directory. Host worker/model binaries are not expected to execute inside the Docker API container.

Normal API code/environment changes can be activated independently with `docker compose -f ../docker-compose.dev.yml --env-file .env up -d --no-deps app`. The existing source mount and installed `httpx` dependency sufficed here; an image rebuild was unnecessary. No broader trading rollout was performed.

## Normal-path verification

Private run: `~/.local/state/kepler-rooms/activation-20261101T180935/`. Declared ceiling: 60 model requests, no model downloads. Actual admitted model requests: **30**, including cancellation; no fresh engine/grounding benchmark was run.

| Check | Observed result |
|---|---|
| Normal dashboard/API | `/api/research/health` at :8502 and `/research/health` at :8001 both report the two actual pinned models ready. The host API uses the same normal Postgres database, not the earlier disposable preview. |
| Start from UI | Created the research question with the normal Research Desk form. Both models retrieved actual repository files and queried the current graph. The project-target graph result was honestly empty. |
| Live discussion | `room:a8e4f66c-88c1-4a91-badf-afde3ef778fd`: four actual public messages, observed arriving while the room was running; terminal **disagreement**; 12 model requests / 12 tool actions. Reload restored the same history. |
| Browser through normal worker | `room:29667b06-edbb-4a77-a3ab-03b7f6595f3d`: both native Codex models discovered/loaded the complete pinned skill and successfully executed actual isolated browser reads of SEBI. Four public messages arrived live; terminal **disagreement**; 16 model requests / 16 tool actions. Unsupported later browser requests were denied, not silently completed. |
| Cancel from UI | `room:44d39d73-894f-422d-81f1-88808f780b2f`: clicked Cancel during two active model requests; terminal **cancelled** after about 6.94 seconds. Two admitted model requests; no tool action executed. |
| Backend restart | Restarted only the host research API. The normal dashboard/API returned identical immutable event IDs afterward. Cursor replay after sequence 33 returned the same 32 subsequent events without duplication. Socket remained 0600. |
| Early failed attempt | `room:8d52aaa0-4efa-4c48-ba23-d4e4511355bb` failed before any model/tool admission because of the service-manager namespace restriction. It remains in history. Scope launch fixed that actual integration problem. |
| Automated checks | **89 focused backend/graph tests passed**, including the five new real Unix-transport/auth/SSE/error and socket/configuration checks. Changed Python files pass Ruff and `git diff --check`. The existing 16 frontend tests/type/build results remain valid; no frontend source was changed in this activation. |

The active system's database was backed up privately before activation. Operator controls, block/kill-switch state, DDPI/POA and open-incident values were compared before/after and remained unchanged. The broker worker's container identity/start time remained unchanged. Only the normal API container was recreated; its usual startup projected existing durable state. All tracked/untracked work and newer runtime JSON were retained; no reset, clean, commit or push occurred. The existing event-log prefix was preserved.

The older isolated preview API/UI were retired after the normal app was verified. Its saved artifacts/database backup remain available; :18513 is no longer the entry point. Use **:8502 → Research Desk**.

## Remaining limits

Service activation does not repair model reasoning. The prior source-scoped extraction accuracy gate remains failed, and these rooms preserve disagreement rather than proving financial correctness. Excerpts/IDs are validated separately from agent interpretation. Manual approval remains required for live entries. No broker migration, token refresh, order action, forecast authority, driver change or unsafe graph fixture was introduced. Browser capability remains bounded public HTML/DOM reading, not unrestricted authenticated navigation.
