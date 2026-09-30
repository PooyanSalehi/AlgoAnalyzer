# AlgoAnalyzer — developer task runner
.PHONY: help install dev-backend dev-frontend test test-backend test-frontend build docker-up docker-down clean

help:            ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install:         ## Install backend + frontend dependencies
	cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
	cd frontend && npm install

dev-backend:     ## Run the FastAPI backend with auto-reload (port 8000)
	cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:    ## Run the Vite dev server (port 5173, proxies /api)
	cd frontend && npm run dev

test: test-backend test-frontend  ## Run the entire test suite

test-backend:    ## Backend unit & integration tests (pytest)
	cd backend && .venv/bin/python -m pytest ../tests

test-frontend:   ## Frontend unit tests (vitest)
	cd frontend && npm run test

build:           ## Production build of the frontend
	cd frontend && npm run build

docker-up:       ## Start the full stack with Docker (frontend on :3000)
	docker compose up --build

docker-down:     ## Stop the Docker stack
	docker compose down

clean:           ## Remove build/dev artifacts
	rm -rf frontend/dist backend/.venv backend/algodata.db backend/test_algodata.db $(find . -name __pycache__ -type d 2>/dev/null)
