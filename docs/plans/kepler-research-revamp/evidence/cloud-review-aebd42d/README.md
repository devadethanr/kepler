# Independent cloud review evidence

Reviewed source: `aebd42d164e48882284c30e3d995eb562d212162`, 1 November 2026. These are new review artifacts, not reconstructed logs from the user's PC.

- `validation.json`: repeated checks, skips, evidence-hash comparisons and limits.
- `probe-results.json`: concrete actual-helper/store results and a committed public-transcript example.
- `review_probes.py.txt`: source used for those temporary SQLite/dummy-file probes.
- `grounding-recalculation.json`: all 120 saved rows recomputed using the existing declared gold function and evaluator. No new inference; not independent proof of unambiguous labels.
- `manifest.json`: file hashes for this review bundle.

The probe deliberately asserts the **observed bugs at aebd42d**. It is a historical reproduction, not a future passing regression suite. A fix should add meaningful regression checks with the corrected expectation, not preserve the bug so this script keeps passing.

The cloud environment used Python 3.12 in an isolated `/tmp` virtual environment installed from `swingtradev3/research_room/requirements-host.lock`. Frontend dependencies were already present; no project lockfile was changed.

Safe backend/reproduction commands, from `swingtradev3/`, with that environment active:

```bash
env DATABASE_URL=sqlite:////tmp/kepler-review-aebd42d-unused.db MEMGRAPH_URI=bolt://127.0.0.1:9 MEMGRAPH_TEST_ACK= FASTAPI_API_KEY=review-local-only python -m pytest tests/test_research_room -q
env DATABASE_URL=sqlite:////tmp/kepler-review-aebd42d-unused.db MEMGRAPH_URI=bolt://127.0.0.1:9 MEMGRAPH_TEST_ACK= PYTHONPATH=. python ../docs/plans/kepler-research-revamp/evidence/cloud-review-aebd42d/review_probes.py.txt
```

Do not replace the sentinel database/graph with the user's real endpoints to make skipped tests run. Use the independently verified disposable launcher for actual Postgres/graph checks.

Frontend commands, from `swingtradev3-dashboard/`:

```bash
npm test
npm run lint
npm run build -- --outDir /tmp/kepler-review-aebd42d-dashboard
```

Ruff checked all 27 Python paths from `git diff --name-only beaa5df..aebd42d`. The review made no model requests, visited no user-PC dashboard, started no app/broker/database/graph service and changed no application source.
