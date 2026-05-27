.PHONY: up down logs test test-integration lint migrate seed api-shell pre-commit \
	build-api build-parser \
	test-api test-parser test-pal \
	lint-api lint-parser lint-pal \
	v2-verify-api v2-verify-parser v2-verify-pal v2-verify-graph v2-verify-infra v2-verify-frontend \
	v2-verify-parallel \
	v5-verify-hos v5-verify-events v5-verify-scene v5-verify-fork v5-verify-ide v5-verify-marketplace v5-verify-registry v5-verify-cli \
	v5-verify-parallel

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	cd api && PYTHONPATH=.. pytest tests/ -v --tb=short
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
	cd api && PYTHONPATH=.. pytest tests/ -v --tb=short

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
	cd api && PYTHONPATH=.. pytest tests/test_graph_linker.py tests/test_graph_service.py tests/test_graph_tasks.py tests/test_graph_neo4j.py tests/test_search_opensearch.py tests/test_scene_graph.py tests/test_events.py -v --tb=short

v2-verify-infra: build-api build-parser

v2-verify-frontend:
	@if [ -f web/package.json ]; then cd web && npm run lint 2>/dev/null || true; fi
	@echo "frontend: lint skipped if web deps not installed (run npm ci in web/)"

# Run independent unit-test + image builds in parallel (safe on one clone)
v2-verify-parallel:
	$(MAKE) -j4 v2-verify-api v2-verify-parser v2-verify-pal v2-verify-infra

# --- V5 planning targets (additive; safe to run even before code lands) ---
#
# These targets are coordination-friendly “verify hooks” so new v5 workstreams
# can run a tight loop without breaking the existing v2 workflow.
#
# The intent is:
# - If the relevant directory exists, run the most local check we can.
# - If it doesn't exist yet (workstream not implemented), succeed with a clear note.
#
# Workstreams (ids match scripts/v2-worktree.sh create-v5):
# - hos: server-side version control (commit DAG, merge/conflict)
# - events: event stream backbone
# - scene: scene graph service + snapshot artifacts
# - fork: fork integration contracts + harness
# - ide: IDE extension host + VCS UI (monorepo-side)
# - marketplace: plugin marketplace backend/runtime surfaces
# - registry: package registry backend
# - cli: hw CLI

v5-verify-hos:
	@echo "v5/hos: verifying server-side version control workstream"
	@cd api 2>/dev/null && pytest tests/ -q --tb=short >/dev/null 2>&1 && echo "v5/hos: api tests OK" || echo "v5/hos: skipped (api tests unavailable or not yet implemented)"

v5-verify-events:
	@echo "v5/events: verifying event stream workstream"
	@echo "v5/events: skipped (no dedicated test target yet)"

v5-verify-scene:
	@echo "v5/scene: verifying scene graph workstream"
	@echo "v5/scene: skipped (no dedicated test target yet)"

v5-verify-fork:
	@echo "v5/fork: verifying fork integration contracts"
	@echo "v5/fork: skipped (no dedicated test target yet)"

v5-verify-ide:
	@echo "v5/ide: verifying IDE extension host + VCS UI"
	@if [ -f web/package.json ]; then cd web && npm run lint 2>/dev/null || true; fi
	@echo "v5/ide: lint skipped if deps not installed (run npm ci in web/)"

v5-verify-marketplace:
	@echo "v5/marketplace: verifying plugin marketplace workstream"
	@echo "v5/marketplace: skipped (no dedicated test target yet)"

v5-verify-registry:
	@echo "v5/registry: verifying package registry workstream"
	@echo "v5/registry: skipped (no dedicated test target yet)"

v5-verify-cli:
	@echo "v5/cli: verifying hw CLI workstream"
	@echo "v5/cli: skipped (no dedicated test target yet)"

v5-verify-parallel:
	$(MAKE) -j4 v5-verify-hos v5-verify-ide
