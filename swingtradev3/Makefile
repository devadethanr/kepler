COMPOSE_FILE := ../docker-compose.dev.yml
ENV_FILE := .env
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)
DOCKER_COMPOSE_MEMORY := $(DOCKER_COMPOSE) --profile memory
DOCKER_COMPOSE_TEST := $(DOCKER_COMPOSE) --profile test

.PHONY: dev dev-detach worker-up worker-smoke test test-file test-memgraph lint lint-fix format dashboard-test dashboard-lint dashboard-build logs logs-app logs-worker logs-mcp logs-dashboard logs-memory logs-memgraph logs-memgraph-lab logs-toolbox toolbox-health local-llm-install local-llm-uninstall local-llm-start local-llm-stop local-llm-logs local-llm-health phase12-smoke phase13-llm-smoke phase13-smoke phase14-smoke memgraph-shell memgraph-snapshot pre-soak-audit pre-soak-backup pre-soak-reset stop clean shell health login phase0-check phase0-reconcile-state phase3-check phase6-check phase7-check db-upgrade

define RUN_PYTEST_ISOLATED
	@set -e; \
	restore_tests() { \
		$(DOCKER_COMPOSE_TEST) rm -sf app-test memgraph-test db-test >/dev/null 2>&1 || true; \
	}; \
	trap restore_tests EXIT; \
	$(DOCKER_COMPOSE_TEST) up -d db-test memgraph-test app-test; \
	$(DOCKER_COMPOSE_TEST) exec -T app-test python -c \
		'from memory.db import ensure_database_ready; ensure_database_ready()'; \
	test_graph_id=$$($(DOCKER_COMPOSE_TEST) ps -q memgraph-test); \
	test_graph_ip=$$(docker inspect --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$$test_graph_id"); \
	test_graph_network=$$(docker inspect --format '{{range $$name, $$network := .NetworkSettings.Networks}}{{$$name}}{{end}}' "$$test_graph_id"); \
	test_app_id=$$($(DOCKER_COMPOSE_TEST) ps -q app-test); \
	test_app_network=$$(docker inspect --format '{{range $$name, $$network := .NetworkSettings.Networks}}{{$$name}}{{end}}' "$$test_app_id"); \
	[ "$$test_graph_network" = "$$test_app_network" ]; \
	[ "$$(docker network inspect --format '{{.Internal}}' "$$test_graph_network")" = true ]; \
	[ "$$(docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' "$$test_graph_id")" = memgraph-test ]; \
	status=0; \
	$(DOCKER_COMPOSE_TEST) exec -T -e MEMGRAPH_TEST_EXPECTED_ADDRESS="$$test_graph_ip:7687" app-test pytest $(1) -v || status=$$?; \
	exit $$status
endef

dev:
	$(DOCKER_COMPOSE_MEMORY) up --build

dev-detach:
	$(DOCKER_COMPOSE_MEMORY) up --build -d

worker-up:
	$(DOCKER_COMPOSE) up -d worker

worker-smoke:
	$(DOCKER_COMPOSE) exec app sh -lc 'timeout 10 python -m execution.worker || test $$? -eq 124'

login:
	$(DOCKER_COMPOSE) exec -it app python -m auth.kite.login

test:
	$(call RUN_PYTEST_ISOLATED,tests/)

test-file:
	$(call RUN_PYTEST_ISOLATED,$(file))

.PHONY: test-memgraph
test-memgraph:
	$(call RUN_PYTEST_ISOLATED,tests/test_context_graph/test_repository.py -m memgraph_destructive)

lint:
	$(DOCKER_COMPOSE) exec app ruff check .

lint-fix:
	$(DOCKER_COMPOSE) exec app ruff check . --fix

format:
	$(DOCKER_COMPOSE) exec app ruff format .

dashboard-test:
	$(DOCKER_COMPOSE) exec -T dashboard npm test

dashboard-lint:
	$(DOCKER_COMPOSE) exec -T dashboard npm run lint

dashboard-build:
	$(DOCKER_COMPOSE) exec -T dashboard npm run build

logs:
	$(DOCKER_COMPOSE_MEMORY) logs -f

logs-app:
	$(DOCKER_COMPOSE) logs -f app

logs-worker:
	$(DOCKER_COMPOSE) logs -f worker

logs-mcp:
	$(DOCKER_COMPOSE) logs -f kite-mcp

logs-dashboard:
	$(DOCKER_COMPOSE) logs -f dashboard

logs-memory:
	$(DOCKER_COMPOSE_MEMORY) logs -f memgraph memgraph-lab

logs-memgraph:
	$(DOCKER_COMPOSE_MEMORY) logs -f memgraph

logs-memgraph-lab:
	$(DOCKER_COMPOSE_MEMORY) logs -f memgraph-lab

logs-toolbox:
	$(DOCKER_COMPOSE_MEMORY) logs -f toolbox

toolbox-health:
	$(DOCKER_COMPOSE) exec -T app python -c "import urllib.request; urllib.request.urlopen('http://toolbox:5000/api/toolset', timeout=3).read()"

local-llm-start:
	@if systemctl --user cat swingtradev3-llama.service >/dev/null 2>&1; then \
		systemctl --user start swingtradev3-llama.service; \
	else \
		bash ops/start_local_llm.sh; \
	fi

local-llm-stop:
	@if systemctl --user cat swingtradev3-llama.service >/dev/null 2>&1; then \
		systemctl --user stop swingtradev3-llama.service; \
	else \
		bash ops/stop_local_llm.sh; \
	fi

local-llm-logs:
	@if systemctl --user cat swingtradev3-llama.service >/dev/null 2>&1; then \
		journalctl --user -u swingtradev3-llama.service -f; \
	else \
		tail -f $${LLAMA_CPP_LOG_FILE:-/tmp/swingtradev3-llama.log}; \
	fi

local-llm-install:
	bash ops/stop_local_llm.sh
	install -Dm644 ops/systemd/swingtradev3-llama.service \
		$${HOME}/.config/systemd/user/swingtradev3-llama.service
	systemctl --user daemon-reload
	systemctl --user enable --now swingtradev3-llama.service

local-llm-uninstall:
	-systemctl --user disable --now swingtradev3-llama.service
	rm -f $${HOME}/.config/systemd/user/swingtradev3-llama.service
	systemctl --user daemon-reload

local-llm-health:
	$(DOCKER_COMPOSE) exec -T app python -m ops.local_llm_smoke --health-only

phase12-smoke:
	$(DOCKER_COMPOSE) exec -T db psql -U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-swingtradev3} -c '\dv *_view'
	$(DOCKER_COMPOSE) exec -T app python -m ops.phase12_smoke

phase13-llm-smoke:
	$(DOCKER_COMPOSE) exec -T app python -m ops.local_llm_smoke

phase13-smoke:
	$(DOCKER_COMPOSE) exec -T app python -m ops.phase13_smoke

phase14-smoke:
	$(DOCKER_COMPOSE) exec -T app python -m ops.phase14_smoke

memgraph-shell:
	$(DOCKER_COMPOSE_MEMORY) exec memgraph mgconsole

memgraph-snapshot:
	printf 'CREATE SNAPSHOT;\n' | $(DOCKER_COMPOSE_MEMORY) exec -T memgraph mgconsole

pre-soak-audit:
	$(DOCKER_COMPOSE) exec -T app python -m ops.pre_soak_cleanup

pre-soak-backup:
	@stamp=$$(date +%Y%m%d_%H%M%S); \
	backup_dir="reports/backups/pre_soak_$$stamp"; \
	mkdir -p "$$backup_dir"; \
	$(DOCKER_COMPOSE) exec -T db pg_dump \
		-U $${POSTGRES_USER:-postgres} -d $${POSTGRES_DB:-swingtradev3} -Fc \
		> "$$backup_dir/postgres.dump"; \
	printf 'CREATE SNAPSHOT;\n' | $(DOCKER_COMPOSE_MEMORY) exec -T memgraph mgconsole >/dev/null; \
	snapshot=$$($(DOCKER_COMPOSE_MEMORY) exec -T memgraph sh -lc \
		"find /var/lib/memgraph/snapshots -maxdepth 1 -type f | sort | tail -n 1"); \
	docker cp "swingtradev3-memgraph:$$snapshot" "$$backup_dir/memgraph.snapshot" >/dev/null; \
	echo "Backup written to $$backup_dir"

pre-soak-reset: pre-soak-backup
	@if [ "$(confirm)" != "RESET-PRE-SOAK" ]; then \
		echo "Refusing reset. Run: make pre-soak-reset confirm=RESET-PRE-SOAK"; \
		exit 1; \
	fi
	@was_running=$$($(DOCKER_COMPOSE) ps --status running --services worker | grep -c '^worker$$' || true); \
	if [ "$$was_running" -gt 0 ]; then $(DOCKER_COMPOSE) stop worker; fi; \
	restore_worker() { \
		if [ "$$was_running" -gt 0 ]; then $(DOCKER_COMPOSE) up -d worker >/dev/null; fi; \
	}; \
	trap restore_worker EXIT; \
	$(DOCKER_COMPOSE) exec -T app python -m ops.pre_soak_cleanup \
		--apply --confirm RESET-PRE-SOAK

stop:
	$(DOCKER_COMPOSE_MEMORY) down

clean:
	$(DOCKER_COMPOSE_MEMORY) down -v --rmi local
	docker system prune -f

shell:
	$(DOCKER_COMPOSE) exec app bash

health:
	$(DOCKER_COMPOSE) exec app sh -lc 'curl --max-time 5 -fsS -H "X-API-Key: $$FASTAPI_API_KEY" http://localhost:8000/health | python3 -m json.tool'

phase0-check:
	$(DOCKER_COMPOSE) exec app python -m ops.phase0_check

phase0-reconcile-state:
	$(DOCKER_COMPOSE) exec app python -m ops.reconcile_local_state

phase3-check:
	$(DOCKER_COMPOSE) exec app python -m ops.phase3_check

phase6-check:
	$(DOCKER_COMPOSE) exec app python -m ops.phase6_check

phase7-check:
	$(DOCKER_COMPOSE) exec app python -m ops.phase7_check

db-upgrade:
	$(DOCKER_COMPOSE) exec app alembic upgrade head

# Opt-in host research processes, independent of trading services.
# KEPLER_RESEARCH_CONFIG and a host-reachable DATABASE_URL must be set explicitly.
RESEARCH_PYTHON ?= $(if $(wildcard $(HOME)/.local/state/kepler-rooms/venv/bin/python),$(HOME)/.local/state/kepler-rooms/venv/bin/python,python)
.PHONY: research-api research-worker research-models
research-api:
	$(RESEARCH_PYTHON) -m uvicorn research_room.server:app --host 127.0.0.1 --port 18012

research-worker:
	$(RESEARCH_PYTHON) -m research_room.worker

research-models:
	$(RESEARCH_PYTHON) -m research_room.models

.PHONY: research-start research-stop research-status
research-start:
	$(RESEARCH_PYTHON) -m ops.research_services start

research-stop:
	$(RESEARCH_PYTHON) -m ops.research_services stop

research-status:
	$(RESEARCH_PYTHON) -m ops.research_services status
