# Independent review of ae7d45f

2 November 2026, Asia/Kolkata. These are new cloud checks, not reconstructed user-PC logs. See [POST_TUNING_REVIEW.md](../../POST_TUNING_REVIEW.md).

- `validation.json`: tests/skips, artifact integrity and scope.
- `confirmation-recalculation.json`: offline replay of all 120 saved final proposals through the actual publication gateway and scorer, with zero score mismatches.
- `recalculate_confirmation.py.txt`: the replay source. It creates temporary SQLite and uses supplied saved proposals; it does not call models, browsers, graph or broker services. It checks the declared evaluator/gateway behavior, not independent semantic gold truth.
- `source-reachability.json`: one bounded public request per configured NSE/SEBI/RBI feed, plus current date-helper output. No raw feed bodies, private data or provider-state mutation.
- `source_probe.py.txt`: the three-request probe source; rerunning makes new network observations which need not match the saved response.
- `date_parser_probe.py.txt`: repeats only the actual helper against saved public date strings, without network or news/app imports.
- `manifest.json`: hashes for this review bundle.

Backend command from `swingtradev3/`, using the isolated review Python 3.12 environment installed from `research_room/requirements-host.lock`:

```bash
env DATABASE_URL=sqlite:////tmp/kepler-review-ae7d45f-unused.db MEMGRAPH_URI=bolt://127.0.0.1:9 MEMGRAPH_TEST_ACK= FASTAPI_API_KEY=review-local-only python -m pytest -q -p no:cacheprovider tests/test_research_room
env DATABASE_URL=sqlite:////tmp/kepler-review-ae7d45f-unused.db MEMGRAPH_URI=bolt://127.0.0.1:9 MEMGRAPH_TEST_ACK= PYTHONPATH=. python ../docs/plans/kepler-research-revamp/evidence/cloud-review-ae7d45f/recalculate_confirmation.py.txt
python ../docs/plans/kepler-research-revamp/evidence/cloud-review-ae7d45f/date_parser_probe.py.txt
```

Keep the sentinel endpoints. Use only verified disposable infrastructure for actual Postgres/graph tests; the user-PC 125-test result was not reproduced here.

Frontend: `npm test`, `npm run lint`, `npm run build -- --outDir /tmp/kepler-review-ae7d45f-dashboard`. Ruff checked the 24 changed Python application/test paths from `git diff --name-only 3bc6876..ae7d45f`. Existing project lockfiles/dependencies and served dashboard output were not changed.
