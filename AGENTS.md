# HCP — parallel V2 agents

Use multiple Cursor subagents (or cloud agents) on **separate git worktrees** so each workstream can run its own build and tests without blocking the others.

Canonical spec: `~/.cursor/HCP.md`. V2 scope (deferred from V1): `/v2/` API, PrAL plugins + converters, proprietary parser sidecars, graph `DERIVED_FROM`, SDK/UI versioning.

## Before starting a V2 agent

```bash
# From repo root — one worktree per workstream (sibling directory)
./scripts/v2-worktree.sh create <workstream>
cd ../HCP_working-v2-<workstream>
git checkout -b feat/hcp-v2-<workstream>-<short-desc>
```

## Workstreams

| ID | Subagent | Owns | Verify (parallel-safe) |
|----|----------|------|-------------------------|
| `api` | `hcp-backend` | `api/app/routers/v2/`, `/v2` mount, OpenAPI tags | `make v2-verify-api` |
| `parser` | `hcp-parser` | `parser/pral/`, plugins, converters | `make v2-verify-parser` |
| `graph` | `hcp-graph` | `graph/`, graph API services | `make v2-verify-graph` |
| `pal` | `hcp-infra` | `infra/pal/`, PAL providers | `make v2-verify-pal` |
| `infra` | `hcp-infra` | `.github/workflows/`, Terraform, Helm | `make v2-verify-infra` |
| `frontend` | `hcp-frontend` | `web/`, `sdk/`, `actions/hcp-upload/` | `make v2-verify-frontend` |

Run several verifies at once from the **same** clone (unit tests and image builds only):

```bash
make v2-verify-parallel
```

Do **not** run `make test-integration` from two agents on the same host at once (fixed ports `5433`, `6380`, `9002`). One integration runner per machine, or use isolated compose project names (see `docs/V2_PARALLEL_WORKSTREAMS.md`).

## V5 workstreams (IDE + version control planning)

V5 introduces new parallel workstreams (IDE extension host + fork integration contracts + version-control backend). Keep them isolated via worktrees so they can iterate independently without blocking the existing V2 work.

### Before starting a V5 agent

```bash
# From repo root — one worktree per workstream (sibling directory)
./scripts/v2-worktree.sh create-v5 <workstream>
cd ../HCP_working-v5-<workstream>
git checkout -b feat/hcp-v5-<workstream>-<short-desc>
```

### Workstreams

| ID | Subagent | Owns (initially) | Verify (parallel-safe) |
|----|----------|------------------|-------------------------|
| `hos` | `hcp-backend` | API + DB for commit graph/merge/conflicts (v5 “HOS version graph”) | `make v5-verify-hos` |
| `events` | `hcp-engineer` | event stream primitives + triggers | `make v5-verify-events` |
| `scene` | `hcp-engineer` | scene graph service + snapshot artifacts | `make v5-verify-scene` |
| `fork` | `hcp-engineer` | protocol/contracts + regression harness stubs | `make v5-verify-fork` |
| `ide` | `hcp-frontend` | IDE extension host + VCS UI scaffolding (monorepo side) | `make v5-verify-ide` |
| `marketplace` | `hcp-engineer` | plugin marketplace backend/runtime surfaces | `make v5-verify-marketplace` |
| `registry` | `hcp-engineer` | package registry backend surfaces | `make v5-verify-registry` |
| `cli` | `hcp-engineer` | CLI `hw` scaffolding | `make v5-verify-cli` |

Run the v5 “lightweight verify” targets in parallel from one clone:

```bash
make v5-verify-parallel
```

Notes:
- `v5-verify-*` targets are **additive** and should stay fast. If a workstream directory or test harness doesn’t exist yet, the target should **skip and succeed** with a message (to support planning without breaking CI).
- Keep using `v2-verify-*` for current V2 implementation work; do not retrofit v5 expectations onto V2 targets.

## Agent prompts (copy into Task / subagent)

### API V2 (`api`)

```
Work in api/ only. Scaffold /v2/ (router package, version prefix, OpenAPI tag "v2").
Do not break /v1/ contracts. Run: make v2-verify-api
Branch: feat/hcp-v2-api-<desc>
```

### Parser V2 (`parser`)

```
Work in parser/pral/ only. Implement converter interface (docs/parser-plugins.md),
add plugin stubs under parser/pral/plugins/, wire registry. Run: make v2-verify-parser
Branch: feat/hcp-v2-parser-<desc>
```

### Graph V2 (`graph`)

```
Work in graph/ and graph-related api services. DERIVED_FROM / derived artifact edges per ADR-003.
Run: make v2-verify-graph
Branch: feat/hcp-v2-graph-<desc>
```

### PAL (`pal`)

```
Work in infra/pal/ only. Provider tests and V2 storage hooks as needed.
Run: make v2-verify-pal
Branch: feat/hcp-v2-pal-<desc>
```

### Infra / CI (`infra`)

```
Work in .github/workflows/, infra/providers/, infra/helm/. Split or extend CI for parallel
v2-verify-* jobs. Run: make v2-verify-infra
Branch: feat/hcp-v2-infra-<desc>
```

### Frontend / SDK V2 (`frontend`)

```
Work in web/, sdk/, actions/hcp-upload/. Client versioning for future /v2/ API.
Run: make v2-verify-frontend
Branch: feat/hcp-v2-frontend-<desc>
```

## Coordinator

For cross-cutting V2 design (ADRs, schema 1.1, phase gates), use `hcp-tech-lead` in read-only review — not parallel implementation.

## Cursor Cloud specific instructions

### Services overview

The full dev stack runs via `docker compose up -d --build` (aliased as `make up`). Services: Postgres 15, Redis 7, MinIO (S3-compatible), Neo4j 5, OpenSearch 2.11, API (FastAPI), parser worker (Celery), graph worker (Celery). See `docker-compose.yml` and the README for details.

### Running tests and lint

- **Lint:** `make lint` (runs `ruff check` + `ruff format --check` on `api/`, `parser/`, `infra/pal/`).
- **Unit tests:** `make test` runs API tests then PAL tests. API tests require `PYTHONPATH` to include the repo root, `api/`, and `graph/` directories (set `PYTHONPATH=/workspace:/workspace/api:/workspace/graph`). PAL tests need `PYTHONPATH=/workspace`.
- **Integration tests:** `make test-integration` uses `docker-compose.test.yml` on ports `5433/6380/9002` — do not run concurrently with the main stack on overlapping ports.
- All Python code targets **Python 3.11**. Use `python3.11` explicitly (the system default may be 3.12).

### Gotchas

- The `cryptography` package must be installed in the Python 3.11 user site (not the system site-packages for 3.12), otherwise `python-jose` will crash with `_cffi_backend` import errors. Fix: `python3.11 -m pip install --force-reinstall --user cryptography`.
- Docker must be installed and running before `make up`. In Cloud Agent VMs, Docker needs `fuse-overlayfs` storage driver and `iptables-legacy` to work inside the nested container environment.
- After `make up`, seed dev data with `make seed` (runs `scripts/seed_dev.py`). Dev credentials: `admin@dev.hcp` / `devpassword`.
- The API health check is at `GET /health`. Full OpenAPI docs at `http://localhost:8000/docs`.
