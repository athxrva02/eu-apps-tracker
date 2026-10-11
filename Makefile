.PHONY: install migrate seed dev worker check build demo start
start:
	./start-local.sh
install:
	python3.12 -m venv .venv
	.venv/bin/pip install --require-hashes -r requirements-dev.lock
	npm --prefix frontend ci
migrate:
	PYTHONPATH=backend .venv/bin/alembic upgrade head
seed:
	PYTHONPATH=backend .venv/bin/python -m app.demo seed
dev:
	PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
worker:
	PYTHONPATH=backend .venv/bin/python -m app.worker
check:
	.venv/bin/ruff check backend tests scripts
	.venv/bin/ruff format --check backend tests scripts
	.venv/bin/pytest -q
	npm --prefix frontend run check
	npm --prefix frontend run format:check
	npm --prefix frontend test
build:
	npm --prefix frontend run build
demo:
	docker compose up --build
