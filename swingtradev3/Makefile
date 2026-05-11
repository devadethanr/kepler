COMPOSE_FILE := ../docker-compose.dev.yml
ENV_FILE := .env
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)
DOCKER_COMPOSE_MEMORY := $(DOCKER_COMPOSE) --profile memory

.PHONY: dev dev-detach worker-up worker-smoke test test-file lint format logs logs-app logs-worker logs-mcp logs-dashboard logs-memory logs-memgraph logs-memgraph-lab memgraph-shell memgraph-snapshot stop clean shell health login phase0-check phase0-reconcile-state phase3-check phase6-check phase7-check db-upgrade

define RUN_PYTEST_ISOLATED
	@was_running=$$($(DOCKER_COMPOSE) ps --status running --services worker 2>/dev/null | grep -c '^worker$$' || true); \
	restore_worker() { \
		if [ "$$was_running" -gt 0 ]; then \
			$(DOCKER_COMPOSE) up -d worker >/dev/null; \
		fi; \
	}; \
	trap restore_worker EXIT; \
	if [ "$$was_running" -gt 0 ]; then \
		$(DOCKER_COMPOSE) stop worker; \
	fi; \
	status=0; \
	$(DOCKER_COMPOSE) exec -T app pytest $(1) -v || status=$$?; \
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

lint:
	$(DOCKER_COMPOSE) exec app ruff check .

format:
	$(DOCKER_COMPOSE) exec app ruff format .

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

memgraph-shell:
	$(DOCKER_COMPOSE_MEMORY) exec memgraph mgconsole

memgraph-snapshot:
	printf 'CREATE SNAPSHOT;\n' | $(DOCKER_COMPOSE_MEMORY) exec -T memgraph mgconsole

stop:
	$(DOCKER_COMPOSE_MEMORY) down

clean:
	$(DOCKER_COMPOSE_MEMORY) down -v --rmi local
	docker system prune -f

shell:
	$(DOCKER_COMPOSE) exec app bash

health:
	$(DOCKER_COMPOSE) exec app sh -lc 'curl -s -H "X-API-Key: $$FASTAPI_API_KEY" http://localhost:8000/health | python3 -m json.tool'

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
