.PHONY: setup up down logs test test-unit test-integration test-e2e lint format migrate shell build

setup:
	pip install -r backend/requirements-dev.txt
	pre-commit install

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

shell:
	docker compose exec backend /bin/bash

migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

test:
	docker compose exec backend pytest tests/ -v

test-unit:
	docker compose exec backend pytest tests/unit -v

test-integration:
	docker compose exec backend pytest tests/integration -v

test-e2e:
	docker compose exec backend pytest tests/e2e -v

lint:
	docker compose exec backend ruff check .
	docker compose exec backend black --check .

format:
	docker compose exec backend black .
	docker compose exec backend ruff check --fix .
