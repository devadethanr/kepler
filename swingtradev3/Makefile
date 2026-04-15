COMPOSE_FILE := ../docker-compose.dev.yml
ENV_FILE := .env
DOCKER_COMPOSE := docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE)

.PHONY: dev dev-detach test test-file lint format logs logs-app logs-mcp logs-dashboard stop clean shell health login

dev:
	$(DOCKER_COMPOSE) up --build

dev-detach:
	$(DOCKER_COMPOSE) up --build -d

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
	curl -s http://localhost:8001/health | python3 -m json.tool
