# Hardware Cloud Platform (HCP)

Cloud-native, API-first system of record for hardware artifacts. V1 delivers the **Hardware Object Store (HOS)**: immutable versions, auto-parse, PartGraph, search, SDKs, and multi-tenant isolation.

**Canonical repository:** [github.com/josiah1203/HCP](https://github.com/josiah1203/HCP) (`git@github.com:josiah1203/HCP.git`). Local checkouts may use a different directory name (e.g. `HCP_working`). Phase 0.5 beta scope and verification commands: [`docs/PHASE_0.5.md`](docs/PHASE_0.5.md).

## Quick start

Requires **Docker Desktop** (or Docker Engine + Compose v2) and Python 3.11 for local tests.

```bash
cp .env.example .env
make up          # Postgres, Redis, MinIO, API (with migrations), parser worker
curl http://localhost:8000/health   # expect {"status":"ok",...}
make down        # stop stack
```

If `make up` fails, check `docker compose ps` and `docker compose logs api`. First boot runs Alembic migrations inside the API container.

### Local tests (no full stack)

```bash
pip install -r api/requirements-dev.txt -r infra/pal/requirements.txt -r infra/pal/requirements-dev.txt
make test
make test-integration   # uses docker-compose.test.yml on ports 5433/6380/9002
```

### Pre-commit

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # gitleaks + ruff + check_secrets.sh
```

### Dev upload (requires seeded org — run `make seed` after stack is up)

```bash
curl -X POST http://localhost:8000/v1/objects/upload \
  -H "Authorization: Bearer dev-token" \
  -F "file=@path/to/board.kicad_pcb" \
  -F "project_id=<PROJECT_UUID>" \
  -F "name=Flight Controller PCB"
```

## Monorepo layout

| Path | Service |
|------|---------|
| `api/` | FastAPI `/v1/*` |
| `parser/` | Celery parsers |
| `graph/` | Neo4j Cypher migrations |
| `infra/pal/` | Provider Abstraction Layer |
| `infra/providers/` | Terraform (AWS stubs, on-prem) |
| `infra/envs/dev/` | Dev Terraform workspace (on-prem modules) |
| `infra/helm/` | Kubernetes charts (`hcp-api`, `hcp-platform`) |
| `sdk/`, `web/`, `actions/` | Clients & UI (later phases) |

## Docs

Engineering plan: `docs/HCP_Engineering_Plan.md` (sync from canonical spec).

Phase 0.5 beta: [`docs/PHASE_0.5.md`](docs/PHASE_0.5.md), [`docs/OSS_HOST_DEPENDENCIES.md`](docs/OSS_HOST_DEPENDENCIES.md), [`docs/PUBLIC_ROADMAP.md`](docs/PUBLIC_ROADMAP.md). Legal/status stubs: [`docs/legal/PLACEHOLDER.md`](docs/legal/PLACEHOLDER.md), [`docs/ops/STATUS_PAGE.md`](docs/ops/STATUS_PAGE.md).

Phase 1 gate: upload via PAL, SHA-256 dedup, JWT/API keys, RBAC, audit log, `docker-compose` local stack.
