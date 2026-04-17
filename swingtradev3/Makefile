COMPOSE_FILE := ../docker-compose.dev.yml
ENV_FILE := .env
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

.PHONY: dev dev-detach worker-up worker-smoke test test-file lint format logs logs-app logs-worker logs-mcp logs-dashboard stop clean shell health login phase0-check phase0-reconcile-state phase3-check db-upgrade

dev:
	$(DOCKER_COMPOSE) up --build

dev-detach:
	$(DOCKER_COMPOSE) up --build -d

worker-up:
	$(DOCKER_COMPOSE) up -d worker

worker-smoke:
	$(DOCKER_COMPOSE) exec app sh -lc 'timeout 10 python -m execution.worker || test $$? -eq 124'

login:
	$(DOCKER_COMPOSE) exec -it app python -m auth.kite.login

test:
	$(DOCKER_COMPOSE) exec app pytest tests/ -v

test-file:
	$(DOCKER_COMPOSE) exec app pytest $(file) -v

lint:
	$(DOCKER_COMPOSE) exec app ruff check .

format:
	$(DOCKER_COMPOSE) exec app ruff format .

logs:
	$(DOCKER_COMPOSE) logs -f

logs-app:
	$(DOCKER_COMPOSE) logs -f app

logs-worker:
	$(DOCKER_COMPOSE) logs -f worker

logs-mcp:
	$(DOCKER_COMPOSE) logs -f kite-mcp

logs-dashboard:
	$(DOCKER_COMPOSE) logs -f dashboard

stop:
	$(DOCKER_COMPOSE) down

clean:
	$(DOCKER_COMPOSE) down -v --rmi local
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

db-upgrade:
	$(DOCKER_COMPOSE) exec app alembic upgrade head
