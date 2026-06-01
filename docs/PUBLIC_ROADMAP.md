# HCP public roadmap (Phase 0.5 beta)

Canonical engineering detail: [`HCP_Engineering_Plan.md`](./HCP_Engineering_Plan.md) (sync from `~/.cursor/HCP.md` / v7.1 plan).

**Beta verification:** [`PHASE_0.5.md`](./PHASE_0.5.md) (sign-off 2026-06-01, tag `phase-0.5-beta-rc1`) · **OSS host tools:** [`OSS_HOST_DEPENDENCIES.md`](./OSS_HOST_DEPENDENCIES.md) · **Local K8s:** [`K8S_LOCAL.md`](./K8S_LOCAL.md)

## Shipped in this repository (beta code)

| Area | What you get |
|------|----------------|
| **HOS / VC** | Branches, commits, diff, merge, conflict resolution, auto-complete merge |
| **HNF + scene graph** | Validation, snapshots on commit, scene graph upserts |
| **Collaboration (beta)** | Polling presence, advisory soft locks |
| **Events** | Taxonomy-aligned publisher (commits, scene graph, collaboration) |
| **Import pipeline** | `POST /v1/projects/{id}/import`, `hw import`, `import/<format>/<ts>` branches, &lt;5% loss gate in tests |
| **Org invites (MVP)** | Register org, invite, accept, RBAC roles — see `api/tests/test_org_invites.py` |
| **Rust sidecars + adapters** | KiCad, FreeCAD, simulation runners; `adapters/crates/*`; host subprocess when `HCP_USE_HOST_OSS=1` |
| **`hw` CLI** | Login, branches, commits, merge, conflicts, import |
| **V1 storage + parsers** | Upload, PAL, KiCad parsers, Celery pipeline |
| **Regression harness** | `mutation-hook`, `roundtrip`, `drc`, `simulation-stability` via `scripts/regression/run_suite.py` |
| **kind + Helm data plane** | Bitnami Postgres/Redis/MinIO, migrate job, backup CronJob, `infra/kind/*.sh`, `helm-validate.sh` |
| **OSS fork bootstrap** | `infra/oss-bootstrap/` templates and `bootstrap-repo.sh` (no GPL in monorepo) |
| **Durability beta (scripts)** | Logical backup CronJob + `restore-drill.sh` — see [`DURABILITY_BETA.md`](./DURABILITY_BETA.md) |

## In progress (before public beta-open)

| Item | Notes |
|------|--------|
| **Live `hcp-oss/*` forks** | Run bootstrap scripts; steward `upstream/main` + `hcp/integration` on GitHub |
| **Published `hcp-adapters` crates** | Monorepo `adapters/` ready; crates.io or tagged git releases pending |
| **Host OSS CI job** | Optional runner with KiCad/FreeCAD + `HCP_USE_HOST_OSS=1` for roundtrip/DRC goldens |
| **Restore drill evidence** | Execute `infra/kind/restore-drill.sh`; log date in ops |
| **Collaboration soak on staging** | [`scripts/collaboration_soak.py`](../scripts/collaboration_soak.py) + criteria in PHASE_0.5 |
| **Two-week internal alpha** | Release branch + changelog (process) |

## Operations & legal (mostly outside repo)

| Item | Where |
|------|--------|
| Terms of Service | [`docs/legal/PLACEHOLDER.md`](./legal/PLACEHOLDER.md) → external URL when live |
| Privacy Policy | Same |
| Status page | [`docs/ops/STATUS_PAGE.md`](./ops/STATUS_PAGE.md) → Better Uptime / Instatus |
| Billing | Stripe or “contact sales”; feature-flagged for beta |

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

Last updated: Phase 0.5 sign-off (`docs(phase05): beta readiness checklist and sign-off`).
