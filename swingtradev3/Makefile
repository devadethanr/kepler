.PHONY: dev dev-detach test test-file lint format logs logs-app logs-mcp stop clean shell health

dev:
	docker compose -f docker-compose.dev.yml up --build

dev-detach:
	docker compose -f docker-compose.dev.yml up --build -d

test:
	docker compose -f docker-compose.dev.yml exec app pytest tests/ -v

test-file:
	docker compose -f docker-compose.dev.yml exec app pytest tests/$(file) -v

lint:
	docker compose -f docker-compose.dev.yml exec app ruff check .

format:
	docker compose -f docker-compose.dev.yml exec app ruff format .

logs:
	docker compose -f docker-compose.dev.yml logs -f

logs-app:
	docker compose -f docker-compose.dev.yml logs -f app

logs-mcp:
	docker compose -f docker-compose.dev.yml logs -f kite-mcp

stop:
	docker compose -f docker-compose.dev.yml down

clean:
	docker compose -f docker-compose.dev.yml down -v --rmi local
	docker system prune -f

shell:
	docker compose -f docker-compose.dev.yml exec app bash

health:
	curl -s http://localhost:8001/health | python3 -m json.tool
