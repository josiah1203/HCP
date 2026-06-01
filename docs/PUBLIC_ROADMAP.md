# HCP public roadmap (Phase 0.5 beta)

Canonical engineering detail: [`HCP_Engineering_Plan.md`](./HCP_Engineering_Plan.md) (sync from `~/.cursor/HCP.md` / v7.1 plan).

**Beta verification:** [`PHASE_0.5.md`](./PHASE_0.5.md) · **OSS host tools:** [`OSS_HOST_DEPENDENCIES.md`](./OSS_HOST_DEPENDENCIES.md)

## Shipped in this repository (beta code)

| Area | What you get |
|------|----------------|
| **HOS / VC** | Branches, commits, diff, merge, conflict resolution, auto-complete merge |
| **HNF + scene graph** | Validation, snapshots on commit, scene graph upserts |
| **Collaboration (beta)** | Polling presence, advisory soft locks |
| **Events** | Taxonomy-aligned publisher (commits, scene graph, collaboration) |
| **Rust sidecars** | KiCad, FreeCAD, simulation runners — JSON-RPC stdio; GPL binaries not vendored |
| **`hw` CLI** | Login, branches, commits, merge, conflicts |
| **V1 storage + parsers** | Upload, PAL, KiCad parsers, Celery pipeline |
| **Regression harness** | `mutation-hook`, `roundtrip`, `drc`, `simulation-stability` via `scripts/regression/run_suite.py` |
| **Infra scaffolding** | `docker-compose`, Helm charts, kind/K8s docs (in progress per track) |

## In progress (Phase 0.5 completion)

| Item | Owner / notes |
|------|----------------|
| Host OSS subprocess bindings (`HCP_USE_HOST_OSS=1`) | KiCad/FreeCAD real export/DRC when forks on PATH |
| Import pipeline | `POST /v1/projects/{id}/import`, `hw import`, corpus &lt;5% loss gate |
| `hcp-oss/*` forks | KiCad + FreeCAD `upstream/main` + `hcp/integration` |
| `hcp-adapters/*` extract | Apache 2.0 crates; sidecars consume published adapters |
| kind + Helm data plane | Postgres, Redis, MinIO, migrate job, API smoke |
| Durability drill | Backup/restore on kind — [`DURABILITY_BETA.md`](./DURABILITY_BETA.md) |
| Org signup / invite MVP | RBAC exists; invite/accept flow E2E |
| Collaboration soak | [`scripts/collaboration_soak.py`](../scripts/collaboration_soak.py) + criteria in PHASE_0.5 |

## Operations & legal (mostly outside repo)

| Item | Where |
|------|--------|
| Terms of Service | [`docs/legal/PLACEHOLDER.md`](./legal/PLACEHOLDER.md) → external URL when live |
| Privacy Policy | Same |
| Status page | [`docs/ops/STATUS_PAGE.md`](./ops/STATUS_PAGE.md) → Better Uptime / Instatus |
| Billing | Stripe or “contact sales”; feature-flagged for beta |
| Two-week stable internal alpha | Release branch + changelog (process) |

## Explicitly out of scope (Phase 0.5)

- Runnable unified **Rust IDE shell** (separate repo; uses `docs/protocol/jsonrpc/`)
- Full **simulation cloud** and package registry
- **AI** copilots and enterprise SSO
- Complete **chrome strip** on all OSS forks (incremental on `hcp/integration`)
- Production multi-region HA (durability beta is single-cluster drill)

## Near-term after beta-open (V1 alignment)

1. Published `hcp-adapters` crates + host KiCad/FreeCAD on CI optional job
2. Import corpus in CI; roundtrip/DRC suites gate on host tools when enabled
3. Graph/search at scale; SDK + 4-view web UI per engineering plan §8–10
4. Enterprise on-prem profile (Terraform/PAL) hardening

Last updated: Phase 0.5 track C2/C5/C3 (regression drivers, ops docs, collaboration soak).
