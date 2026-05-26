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
