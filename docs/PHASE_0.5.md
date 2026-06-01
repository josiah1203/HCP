# Phase 0.5 (public beta) readiness

Phase 0.5 delivers a **server-ready** platform for hardware version control, collaboration, events, scene graph snapshots, OSS tool sidecars (Rust runners), and a minimal `hw` CLI—without shipping a full Rust IDE shell (developed separately).

Canonical engineering spec: `~/.cursor/HCP.md`. Detailed sidecar port plan: `.cursor/plans/hcp-phase05-beta_411f672c.plan.md`.

**OSS vs host:** [OSS_HOST_DEPENDENCIES.md](./OSS_HOST_DEPENDENCIES.md) — sidecars are in-repo; KiCad/FreeCAD/simulator **binaries are not vendored**.

**Public roadmap:** [PUBLIC_ROADMAP.md](./PUBLIC_ROADMAP.md). **Durability beta notes:** [DURABILITY_BETA.md](./DURABILITY_BETA.md). **Local K8s:** [K8S_LOCAL.md](./K8S_LOCAL.md).

## Phase 0.5 sign-off (2026-06-01)

| Field | Value |
|-------|--------|
| **Commit** | [`222218b`](https://github.com/josiah1203/HCP/commit/222218b7ad632249f0bfb2b6039799e8d5818be7) (`main`) |
| **Tag** | `phase-0.5-beta-rc1` (annotated; see git tag list) |
| **Readiness estimate** | **~82%** of in-repo v7.1 Phase 0.5 criteria; **~68%** including external ops gates for true beta-open |

### Test battery (Phase D — executed on sign-off)

| Suite | Command / path | Result |
|-------|----------------|--------|
| Rust sidecars | `cd rust && cargo test` | **23 passed** |
| API beta battery | `api/tests/test_hnf.py`, `test_hos_*.py`, `test_scene_graph.py`, `test_collaboration.py`, `test_events.py`, `test_import_pipeline.py`, `test_org_invites.py`, `test_v1_endpoints.py` | **32 passed**, 1 skipped |
| CLI | `cli/tests` | **17 passed** |
| Regression unit | `scripts/regression/tests` | **12 passed** |
| Mutation-hook driver | `scripts/regression/run_suite.py mutation-hook --mutations 4` | **pass** |
| Helm validate | `infra/kind/helm-validate.sh` | **pass** (lint + template) |

**Totals:** 84 pytest cases passed (1 skipped) + 23 Rust tests + mutation-hook + helm validate.

Parallel tracks merged on `main` (evidence commits): [`dd2f3ff`](https://github.com/josiah1203/HCP/commit/dd2f3ff) (OSS/adapters/subprocess), [`222218b`](https://github.com/josiah1203/HCP/commit/222218b) (kind/Helm/durability), [`94935bf`](https://github.com/josiah1203/HCP/commit/94935bf)/[`bc41544`](https://github.com/josiah1203/HCP/commit/bc41544) (import + org invites), [`6217c4b`](https://github.com/josiah1203/HCP/commit/6217c4b)/[`b9fce6b`](https://github.com/josiah1203/HCP/commit/b9fce6b)/[`a51acee`](https://github.com/josiah1203/HCP/commit/a51acee) (regression + ops).

## Beta scope (in repo)

| Area | Location | Status |
|------|----------|--------|
| HNF documents + validation | `api/app/services/hnf.py`, `api/tests/test_hnf.py` | Done |
| HOS version control (branches, commits, diff, merge) | `api/app/services/hos_version_control.py`, `api/tests/test_hos_version_control.py` | Done |
| Merge conflicts + resolve + **auto-complete merge** | `POST /v1/hos/conflicts/{id}/resolve` | Done |
| Object snapshots on commits | `api/tests/test_hos_object_snapshots.py` | Done |
| Scene graph + snapshots | `api/app/services/scene_graph.py`, `api/tests/test_scene_graph.py` | Done |
| Collaboration (presence, locks) | `api/tests/test_collaboration.py` | Done |
| Event stream | `api/app/services/events.py`, `api/tests/test_events.py` | Done |
| Import pipeline + loss gate | `api/app/services/import_pipeline.py`, `api/tests/test_import_pipeline.py`, `cli/hw/` import | Done |
| Org invite MVP | `api/tests/test_org_invites.py` | Done |
| Rust sidecars + host subprocess seam | `rust/crates/*`, `adapters/crates/*` | Done (CI default: stubs) |
| Mutation-hook / roundtrip / DRC / sim regression | `scripts/regression/` | Done (best-effort without host OSS) |
| `hw` CLI (login, branches, commits, merge, conflicts, import) | `cli/hw/` | Done |
| kind + Helm data plane | `infra/kind/`, `infra/helm/hcp-platform/` | Done (chart validate in CI path) |
| Postgres backup + restore drill scripts | `infra/helm/hcp-platform/templates/backup-cronjob.yaml`, `infra/kind/restore-drill.sh` | Partial — scripted, drill not re-run at sign-off |
| OSS fork bootstrap (no GPL in monorepo) | `infra/oss-bootstrap/` | Partial — templates/scripts; external `hcp-oss/*` repos operator-owned |
| Adapter workspace (Apache 2.0) | `adapters/crates/hnf-adapter-sdk`, `hnf-kicad`, `hnf-freecad` | Partial — in monorepo; not yet on crates.io |

## v7.1 Phase 0.5 readiness checklist

| Criterion | Status | Evidence |
|-----------|--------|----------|
| HOS VC + collaboration + events + scene graph | **Done** | API services + tests above; commits through `b6dd0d2` |
| Rust sidecar protocol + mutation-hook regression | **Done** | `rust/crates/sidecar-protocol`, `scripts/regression/mutation_hook.py`; `d1ff3d2` |
| `hw` CLI for VC (+ import) | **Done** | `cli/hw/`, `cli/tests/test_hw_cli.py` |
| OSS engines as host subprocesses (not vendored) | **Partial** | `SubprocessKiCadBinding`, `SubprocessFreecadEngineBridge` — [`dd2f3ff`](https://github.com/josiah1203/HCP/commit/dd2f3ff), [`docs/OSS_HOST_DEPENDENCIES.md`](./OSS_HOST_DEPENDENCIES.md); default CI remains stub/noop |
| `hcp-oss/kicad` + `hcp-oss/freecad` forks live | **Blocked** (external) | Bootstrap: `infra/oss-bootstrap/` — repos must exist on GitHub org; not verified at sign-off |
| `hcp-adapters/*` published crates | **Partial** | `adapters/` workspace in monorepo; publish to crates.io / git tags still ops |
| Import pipeline + corpus &lt;5% loss | **Done** | `api/tests/test_import_pipeline.py` (`loss_ratio < 0.05`); [`94935bf`](https://github.com/josiah1203/HCP/commit/94935bf) |
| Org signup / invite / roles E2E | **Done** | `api/tests/test_org_invites.py`; [`94935bf`](https://github.com/josiah1203/HCP/commit/94935bf) |
| kind: API + Postgres + Redis + MinIO + migrate | **Done** (automation) | [`222218b`](https://github.com/josiah1203/HCP/commit/222218b), [`docs/K8S_LOCAL.md`](./K8S_LOCAL.md), `helm-validate.sh` green |
| Restore drill executed once | **Partial** | `infra/kind/restore-drill.sh`, [`docs/DURABILITY_BETA.md`](./DURABILITY_BETA.md) — not re-executed during sign-off run |
| Roundtrip / DRC / simulation-stability regression | **Partial** | Drivers in `scripts/regression/` — [`6217c4b`](https://github.com/josiah1203/HCP/commit/6217c4b); full fidelity needs `HCP_USE_HOST_OSS=1` + binaries |
| Public roadmap + out-of-scope list | **Done** | [`PUBLIC_ROADMAP.md`](./PUBLIC_ROADMAP.md) |
| Billing, counsel-approved ToS, live status page | **Blocked** (external) | [`docs/legal/PLACEHOLDER.md`](./legal/PLACEHOLDER.md), [`docs/ops/STATUS_PAGE.md`](./ops/STATUS_PAGE.md) |
| Collaboration stress soak (2 users) | **Partial** | [`scripts/collaboration_soak.py`](../scripts/collaboration_soak.py), criteria below — no staging soak log attached |
| Two-week stable internal alpha | **Blocked** (process) | Release branch discipline; not verifiable from git |

## Remaining gaps for true beta-open

1. **Create and steward** `hcp-oss/kicad` and `hcp-oss/freecad` on GitHub (`infra/oss-bootstrap/*/bootstrap-repo.sh`).
2. **Publish** `hnf-adapter-sdk`, `hnf-kicad`, `hnf-freecad` (crates.io or versioned git) and pin HCP releases to them.
3. **Run** `infra/kind/restore-drill.sh` once; record RPO/RTO date in ops log ([`DURABILITY_BETA.md`](./DURABILITY_BETA.md)).
4. **Run** collaboration soak on staging; attach summary to release notes.
5. **External ops:** billing, ToS/privacy counsel sign-off, status page URL in README.
6. **Optional CI job** with `HCP_USE_HOST_OSS=1` on a runner with KiCad/FreeCAD installed.
7. **Two-week** internal alpha stability window before public invite.

## Collaboration stress gate (C3 — soak test)

Phase 0.5 requires evidence that **two concurrent users** can share presence and locks without wedging the API. Full 4-hour wall-clock soaks are optional for CI; use an **accelerated soak** with equivalent RPC volume.

### Pass criteria

| Check | Threshold |
|-------|-----------|
| Presence heartbeat success rate | ≥ 99% over soak window |
| Lock acquire / release pairs | 100% paired (no orphaned locks in DB) |
| Conflict rate | Documented; no unhandled 5xx |
| API p99 (presence + lock endpoints) | &lt; 500 ms on staging hardware |

### Accelerated soak script (manual / staging)

Run against a staging API with two test users (`user-a`, `user-b`) and a shared `projectId`:

```bash
# Terminal A — user A presence + lock cycle (repeat for N minutes or use `watch`)
export HCP_API_URL=https://staging.example HCP_TOKEN_A=... PROJECT_ID=...

for i in $(seq 1 1200); do
  curl -sf -X POST "$HCP_API_URL/v1/collaboration/presence/heartbeat" \
    -H "Authorization: Bearer $HCP_TOKEN_A" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"$PROJECT_ID\",\"session_id\":\"soak-a\",\"resource_path\":\"doc/main\"}" >/dev/null
  curl -sf -X POST "$HCP_API_URL/v1/collaboration/locks/acquire" \
    -H "Authorization: Bearer $HCP_TOKEN_A" \
    -H "Content-Type: application/json" \
    -d "{\"project_id\":\"$PROJECT_ID\",\"resource_path\":\"doc/main\",\"session_id\":\"soak-a\",\"ttl_seconds\":30}" >/dev/null
  sleep 2
done
```

```bash
# Terminal B — user B (offset timing to maximize overlap)
export HCP_TOKEN_B=...
# Same loop with TOKEN_B; alternate resourceId every 10 iterations to test contention
```

**Record:** start/end time, request count, failures from logs, and Postgres row count for `collaboration_locks` (should return to zero after releases). Attach summary to the Phase 0.5 sign-off PR.

**Python helper (accelerated):** `scripts/collaboration_soak.py` — same endpoints with configurable `--iterations` and p95 check:

```bash
export HCP_API_URL=http://localhost:8000 HCP_PROJECT_ID=<uuid> HCP_TOKEN=dev-token
python3 scripts/collaboration_soak.py --iterations 120 --interval-s 1 --p95-limit-ms 500
```

k6/Locust scripts under `scripts/load/` may replace the shell loop later; until then use the helper or the curl procedure above.

## Out of scope for Phase 0.5

- Runnable Rust IDE shell (host uses JSON-RPC contracts in `docs/protocol/jsonrpc/`)
- Production multi-region HA beyond single-cluster durability beta
- Hosted status page and counsel-approved ToS (tracked via ops stubs; external publish required)

## Verify locally

```bash
# Rust sidecars
source "$HOME/.cargo/env" && cd rust && cargo test

# API (focused beta battery)
cd /path/to/HCP_working
PYTHONPATH=api:.. python3 -m pytest \
  api/tests/test_hnf.py \
  api/tests/test_hos_version_control.py \
  api/tests/test_hos_object_snapshots.py \
  api/tests/test_scene_graph.py \
  api/tests/test_collaboration.py \
  api/tests/test_events.py \
  api/tests/test_import_pipeline.py \
  api/tests/test_org_invites.py \
  api/tests/test_v1_endpoints.py -q

# CLI + regression unit tests
PYTHONPATH=api:.. python3 -m pytest cli/tests scripts/regression/tests -q

# Regression suites
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4
python3 scripts/regression/run_suite.py roundtrip \
  --corpus scripts/regression/fixtures/roundtrip_corpus
python3 scripts/regression/run_suite.py drc \
  --corpus scripts/regression/fixtures/drc_corpus \
  --goldens scripts/regression/fixtures/drc_goldens
python3 scripts/regression/run_suite.py simulation-stability \
  --corpus scripts/regression/fixtures/sim_corpus \
  --goldens scripts/regression/fixtures/sim_goldens

# Helm (no cluster)
./infra/kind/helm-validate.sh
```

## Repository

**Canonical remote:** `git@github.com:josiah1203/HCP.git`  
Local clones may use a folder name such as `HCP_working`; treat that directory as the same monorepo.
