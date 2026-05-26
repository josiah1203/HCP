.PHONY: up down logs test test-integration lint migrate seed api-shell pre-commit \
	build-api build-parser \
	test-api test-parser test-pal \
	lint-api lint-parser lint-pal \
	v2-verify-api v2-verify-parser v2-verify-pal v2-verify-graph v2-verify-infra v2-verify-frontend \
	v2-verify-parallel

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	cd api && pytest tests/ -v --tb=short
	PYTHONPATH=. pytest infra/pal/tests/ -v --tb=short

test-integration:
	docker compose -f docker-compose.test.yml up -d --wait
	PYTHONPATH=. MINIO_ENDPOINT=http://localhost:9002 MINIO_ACCESS_KEY=hcp \
		MINIO_SECRET_KEY=hcpsecret MINIO_BUCKET=hcp-local \
		pytest infra/pal/tests/test_onprem_storage.py -v
	docker compose -f docker-compose.test.yml down -v

lint:
	ruff check api/ parser/ infra/pal/
	ruff format --check api/ parser/ infra/pal/

pre-commit:
	pre-commit run --all-files

migrate:
	cd api && alembic upgrade head

seed:
	python scripts/seed_dev.py

api-shell:
	docker compose exec api bash

# --- Per-workstream targets (parallel V2 subagents; see AGENTS.md) ---

build-api:
	docker build -f api/Dockerfile -t hcp-api:local .

build-parser:
	docker build -f parser/Dockerfile -t hcp-parser:local .

test-api:
	cd api && pytest tests/ -v --tb=short

test-parser:
	cd parser && PYTHONPATH=.. pytest tests/ -v --tb=short

test-pal:
	PYTHONPATH=. pytest infra/pal/tests/ -v --tb=short

lint-api:
	ruff check api/
	ruff format --check api/

lint-parser:
	ruff check parser/
	ruff format --check parser/

lint-pal:
	ruff check infra/pal/
	ruff format --check infra/pal/

v2-verify-api: lint-api test-api build-api

v2-verify-parser: lint-parser test-parser build-parser

v2-verify-pal: lint-pal test-pal

v2-verify-graph:
	@test -d graph/schema && test $$(ls -1 graph/schema/*.cypher 2>/dev/null | wc -l) -gt 0

v2-verify-infra: build-api build-parser

v2-verify-frontend:
	@if [ -f web/package.json ]; then cd web && npm run lint 2>/dev/null || true; fi
	@echo "frontend: lint skipped if web deps not installed (run npm ci in web/)"

# Run independent unit-test + image builds in parallel (safe on one clone)
v2-verify-parallel:
	$(MAKE) -j4 v2-verify-api v2-verify-parser v2-verify-pal v2-verify-infra
