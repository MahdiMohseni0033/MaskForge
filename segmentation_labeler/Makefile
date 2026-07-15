.PHONY: install dev backend frontend build run test lint typecheck

install:
	uv sync --dev
	npm --prefix frontend install

backend:
	uv run uvicorn seglabeler.api:app --reload --host 127.0.0.1 --port 8000

frontend:
	npm --prefix frontend run dev

dev:
	./scripts/dev.sh

build:
	npm --prefix frontend run build

run: build
	uv run segmentation-labeler

test:
	uv run pytest
	npm --prefix frontend test -- --run

lint:
	uv run ruff check backend
	npm --prefix frontend run lint

typecheck:
	npm --prefix frontend run typecheck

