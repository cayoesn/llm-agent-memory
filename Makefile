.PHONY: help install run api test coverage lint format docker-up docker-down logs migrate-up migrate-down migrate-revision benchmark

DC = docker compose
VENV = .venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip
ALEMBIC = $(VENV)/Scripts/alembic

help:
	@echo "Agent Memory Engine Makefile"
	@echo "  make install           - cria a virtualenv e instala dependencias"
	@echo "  make run               - sobe a API localmente com reload"
	@echo "  make api               - alias para make run"
	@echo "  make test              - executa a suite de testes"
	@echo "  make coverage          - gera coverage em terminal, HTML e XML"
	@echo "  make lint              - roda ruff e mypy"
	@echo "  make format            - formata o codigo com black e ruff --fix"
	@echo "  make docker-up         - sobe a stack Docker completa"
	@echo "  make docker-down       - derruba a stack Docker"
	@echo "  make logs              - acompanha logs da stack"
	@echo "  make migrate-up        - aplica migrations pendentes"
	@echo "  make migrate-down      - faz downgrade da ultima migration"
	@echo "  make migrate-revision  - gera uma nova migration com autogenerate"
	@echo "  make benchmark         - executa o benchmark simples de latencia"

install:
	python -m venv $(VENV)
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.interfaces.http.main:app --reload --host 0.0.0.0 --port 8000

api: run

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html:tests/coverage_html --cov-report=xml:tests/coverage.xml

lint:
	$(PYTHON) -m ruff check app tests benchmarks
	$(PYTHON) -m mypy app

format:
	$(PYTHON) -m black app tests benchmarks
	$(PYTHON) -m ruff check app tests benchmarks --fix

docker-up:
	$(DC) up -d --build

docker-down:
	$(DC) down

logs:
	$(DC) logs -f

migrate-up:
	$(ALEMBIC) upgrade head

migrate-down:
	$(ALEMBIC) downgrade -1

migrate-revision:
	$(ALEMBIC) revision --autogenerate -m "new_migration"

benchmark:
	$(PYTHON) benchmarks/latency_bench.py
