COMPOSE_FILE := ../docker-compose.dev.yml

.PHONY: dev dev-detach test test-file lint format logs logs-app logs-mcp stop clean shell health login

dev:
	docker compose -f $(COMPOSE_FILE) up --build

dev-detach:
	docker compose -f $(COMPOSE_FILE) up --build -d

login:
	docker compose -f $(COMPOSE_FILE) exec -it app python -m auth.kite.login

test:
	docker compose -f $(COMPOSE_FILE) exec app pytest tests/ -v

test-file:
	docker compose -f $(COMPOSE_FILE) exec app pytest tests/$(file) -v

lint:
	docker compose -f $(COMPOSE_FILE) exec app ruff check .

format:
	docker compose -f $(COMPOSE_FILE) exec app ruff format .

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

logs-app:
	docker compose -f $(COMPOSE_FILE) logs -f app

logs-mcp:
	docker compose -f $(COMPOSE_FILE) logs -f kite-mcp

stop:
	docker compose -f $(COMPOSE_FILE) down

clean:
	docker compose -f $(COMPOSE_FILE) down -v --rmi local
	docker system prune -f

shell:
	docker compose -f $(COMPOSE_FILE) exec app bash

health:
	curl -s http://localhost:8001/health | python3 -m json.tool
