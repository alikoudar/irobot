.PHONY: help build up down restart logs ps clean migrate init-db test lint format

help:
	@echo "IroBot - Makefile commands"
	@echo ""
	@echo "Docker commands:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make restart     - Restart all services"
	@echo "  make logs        - Show logs for all services"
	@echo "  make ps          - Show running containers"
	@echo "  make clean       - Remove all containers and volumes"
	@echo ""
	@echo "Database commands:"
	@echo "  make migrate     - Run Alembic migrations"
	@echo "  make init-db     - Initialize database with admin user"
	@echo ""
	@echo "Development commands:"
	@echo "  make test        - Run tests"
	@echo "  make lint        - Run linters"
	@echo "  make format      - Format code"

build:
	docker-compose build

up:
	docker-compose up -d
	@echo "✅ All services started"
	@echo "Frontend: http://localhost"
	@echo "Backend API: http://localhost/api"
	@echo "API Docs: http://localhost/api/docs"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

ps:
	docker compose ps --format "table {{.Name}}\t{{.Ports}}\t{{.Service}}\t{{.State}}\t{{.Health}}" | sed -E 's/, \[.*\][^ ]*//g'

clean:
	docker-compose down -v
	@echo "✅ All containers and volumes removed"

migrate:
	docker-compose exec backend alembic upgrade head
	@echo "✅ Database migrations applied"

init-db:
	docker-compose exec backend python scripts/init_db.py
	@echo "✅ Database initialized with admin user"

test:
	docker-compose exec backend pytest tests/ -v --cov=app

lint:
	docker-compose exec backend flake8 app/
	docker-compose exec backend mypy app/

format:
	docker-compose exec backend black app/
	docker-compose exec backend isort app/