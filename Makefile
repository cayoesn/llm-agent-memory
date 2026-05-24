.PHONY: install run test coverage lint format docker-up docker-down logs migrate-up migrate-down

VENV = .venv
PYTHON = $(VENV)/Scripts/python
PIP = $(VENV)/Scripts/pip

install:
	python -m venv $(VENV)
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.interfaces.http.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest

coverage:
	$(PYTHON) -m pytest --cov=app --cov-report=term-missing --cov-report=html:tests/coverage_html --cov-report=xml:tests/coverage.xml

lint:
	$(PYTHON) -m ruff check app
	$(PYTHON) -m mypy app

format:
	$(PYTHON) -m black app
	$(PYTHON) -m ruff check app --fix

docker-up:
	docker compose up -d

docker-down:
	docker compose down

logs:
	docker compose logs -f

migrate-up:
	$(VENV)/Scripts/alembic upgrade head

migrate-down:
	$(VENV)/Scripts/alembic revision --autogenerate -m "new_migration"
