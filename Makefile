# KKB Firma İstihbarat - Makefile
# Ortak komutlar ve görevler

.PHONY: help setup dev dev-backend dev-frontend test lint build deploy clean logs

# Default target
help:
	@echo "KKB Firma İstihbarat - Available Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make setup          - Initial project setup"
	@echo "  make install        - Install all dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev            - Start full stack with Docker"
	@echo "  make dev-services   - Start only Docker services (postgres, redis, qdrant)"
	@echo "  make dev-backend    - Start backend in development mode"
	@echo "  make dev-frontend   - Start frontend in development mode"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate     - Run database migrations"
	@echo "  make db-seed        - Seed database with test data"
	@echo "  make db-reset       - Reset database (drop and recreate)"
	@echo ""
	@echo "Vector DB:"
	@echo "  make qdrant-init    - Initialize Qdrant collections"
	@echo "  make qdrant-list    - List Qdrant collections"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-backend   - Run backend tests"
	@echo "  make test-frontend  - Run frontend tests"
	@echo ""
	@echo "Linting:"
	@echo "  make lint           - Run all linters"
	@echo "  make lint-backend   - Run backend linter (ruff)"
	@echo "  make lint-frontend  - Run frontend linter (eslint)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build          - Build Docker images"
	@echo "  make deploy         - Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make logs           - View Docker logs"
	@echo "  make clean          - Clean up containers and volumes"
	@echo "  make shell-backend  - Open shell in backend container"
	@echo "  make shell-db       - Open psql shell"

# ============================================
# Setup
# ============================================

setup:
	@chmod +x scripts/*.sh
	@./scripts/setup.sh

install: install-backend install-frontend

install-backend:
	@echo "Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt

install-frontend:
	@echo "Installing frontend dependencies..."
	@cd frontend && npm install

# ============================================
# Development
# ============================================

dev:
	@docker-compose -f docker/docker-compose.yml up --build

dev-services:
	@docker-compose -f docker/docker-compose.dev.yml up -d
	@echo ""
	@echo "Services started:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6379"
	@echo "  - Qdrant: localhost:6333"
	@echo "  - pgAdmin: localhost:5050"

dev-backend:
	@cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	@cd frontend && npm run dev

stop:
	@docker-compose -f docker/docker-compose.yml down
	@docker-compose -f docker/docker-compose.dev.yml down

# ============================================
# Database
# ============================================

db-migrate:
	@cd backend && alembic upgrade head

db-seed:
	@python scripts/seed_db.py

db-reset:
	@echo "Resetting database..."
	@docker-compose -f docker/docker-compose.dev.yml down -v
	@docker-compose -f docker/docker-compose.dev.yml up -d postgres
	@sleep 5
	@echo "Database reset complete"

# ============================================
# Vector DB
# ============================================

qdrant-init:
	@python scripts/init_qdrant.py init

qdrant-list:
	@python scripts/init_qdrant.py list

# ============================================
# Testing
# ============================================

test: test-backend test-frontend

test-backend:
	@cd backend && pytest -v

test-frontend:
	@cd frontend && npm run test

# ============================================
# Linting
# ============================================

lint: lint-backend lint-frontend

lint-backend:
	@cd backend && ruff check . --fix

lint-frontend:
	@cd frontend && npm run lint

format:
	@cd backend && ruff format .
	@cd frontend && npm run format

# ============================================
# Build & Deploy
# ============================================

build:
	@docker-compose -f docker/docker-compose.yml build

deploy:
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh

# ============================================
# Utilities
# ============================================

logs:
	@docker-compose -f docker/docker-compose.yml logs -f

logs-backend:
	@docker-compose -f docker/docker-compose.yml logs -f backend

logs-worker:
	@docker-compose -f docker/docker-compose.yml logs -f celery-worker

clean:
	@echo "Cleaning up..."
	@docker-compose -f docker/docker-compose.yml down -v --remove-orphans
	@docker-compose -f docker/docker-compose.dev.yml down -v --remove-orphans
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

shell-backend:
	@docker exec -it kkb-backend /bin/bash

shell-db:
	@docker exec -it kkb-postgres-dev psql -U kkb -d firma_istihbarat

# ============================================
# Quick commands
# ============================================

up: dev-services
down: stop
restart: stop dev-services
