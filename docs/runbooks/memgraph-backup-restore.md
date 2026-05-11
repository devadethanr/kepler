# Memgraph Backup And Restore Runbook

This runbook covers the local development Memgraph stack only. Postgres remains the
execution source of truth; Memgraph stores context, research, and learning memory.
Trading safety must not depend on Memgraph availability.

## Services

Run commands from `swingtradev3/`.

- `make dev` and `make dev-detach` start the Compose `memory` profile.
- `memgraph` uses `memgraph/memgraph-mage:latest`.
- `memgraph-lab` uses `memgraph/lab:latest`.
- Bolt: `localhost:${MEMGRAPH_BOLT_PORT:-7687}`
- Lab: `http://localhost:${MEMGRAPH_LAB_PORT:-3000}`
- Monitoring/log WebSocket: `localhost:${MEMGRAPH_MONITORING_PORT:-7444}`

Useful targets:

```bash
make logs-memory
make logs-memgraph
make logs-memgraph-lab
make memgraph-shell
make memgraph-snapshot
```

Optional `.env` overrides:

```bash
MEMGRAPH_BOLT_PORT=7687
MEMGRAPH_MONITORING_PORT=7444
MEMGRAPH_LAB_PORT=3000
MEMGRAPH_LOG_LEVEL=INFO
MEMGRAPH_MEMORY_LIMIT_MIB=2048
MEMGRAPH_SNAPSHOT_INTERVAL_SEC=300
```

## Backup Snapshot

Create a point-in-time snapshot:

```bash
make memgraph-snapshot
```

Copy the newest snapshot out of the container:

```bash
mkdir -p ../backups/memgraph
container_id=$(docker compose -f ../docker-compose.dev.yml --env-file .env --profile memory ps -q memgraph)
snapshot_path=$(docker compose -f ../docker-compose.dev.yml --env-file .env --profile memory exec -T memgraph sh -lc 'find /var/lib/memgraph/snapshots -type f | sort | tail -1')
docker cp "${container_id}:${snapshot_path}" "../backups/memgraph/$(basename "${snapshot_path}")"
```

If `snapshot_path` is empty, check `make logs-memgraph` and rerun `make memgraph-snapshot`.

## Logical Dump

For a portable development export, use Memgraph Lab's Import & Export screen and export
a CYPHERL dump. From the shell, `DUMP DATABASE;` can also be run in `make memgraph-shell`.

## Restore Snapshot

Restoring a snapshot replaces the current Memgraph graph. It does not change Postgres.

1. Start the memory profile:

```bash
make dev-detach
```

2. Copy the snapshot into the container:

```bash
container_id=$(docker compose -f ../docker-compose.dev.yml --env-file .env --profile memory ps -q memgraph)
docker cp ../backups/memgraph/<snapshot-file> "${container_id}:/tmp/restore.snapshot"
```

3. Recover the snapshot:

```bash
printf 'RECOVER SNAPSHOT "/tmp/restore.snapshot" FORCE;\n' \
  | docker compose -f ../docker-compose.dev.yml --env-file .env --profile memory exec -T memgraph mgconsole
```

4. Verify:

```bash
printf 'MATCH (n) RETURN count(n) AS nodes;\n' \
  | docker compose -f ../docker-compose.dev.yml --env-file .env --profile memory exec -T memgraph mgconsole
```

## Failure Boundary

If Memgraph backup or restore fails, keep live execution controls on Postgres and the
worker path only. The acceptable degradation is less historical research context, not
blocked reconciliation, order placement, flattening, or kill switches.

