# Phase 0.5 (public beta) readiness

Phase 0.5 delivers a **server-ready** platform for hardware version control, collaboration, events, scene graph snapshots, OSS tool sidecars (Rust runners), and a minimal `hw` CLI—without shipping a full Rust IDE shell (developed separately).

Canonical engineering spec: `~/.cursor/HCP.md`. Detailed sidecar port plan: `.cursor/plans/hcp-phase05-beta_411f672c.plan.md`.

**OSS vs host:** [OSS_HOST_DEPENDENCIES.md](./OSS_HOST_DEPENDENCIES.md) — sidecars are in-repo; KiCad/FreeCAD/simulator **binaries are not vendored**.

**Public roadmap stub:** [PUBLIC_ROADMAP.md](./PUBLIC_ROADMAP.md). **Durability beta notes:** [DURABILITY_BETA.md](./DURABILITY_BETA.md).

## Beta scope (in repo)

| Area | Location | Status |
|------|----------|--------|
| HNF documents + validation | `api/app/services/hnf.py`, `api/tests/test_hnf.py` | Integrated |
| HOS version control (branches, commits, diff, merge) | `api/app/services/hos_version_control.py`, `api/tests/test_hos_version_control.py` | Integrated |
| Merge conflicts + resolve + **auto-complete merge** when all resolved | `POST /v1/hos/conflicts/{id}/resolve` | Integrated |
| Object snapshots on commits | `api/tests/test_hos_object_snapshots.py` | Integrated |
| Scene graph + snapshots | `api/app/services/scene_graph.py`, `api/tests/test_scene_graph.py` | Integrated |
| Collaboration (presence, locks) | `api/tests/test_collaboration.py` | Integrated |
| Event stream | `api/app/services/events.py`, `api/tests/test_events.py` | Integrated |
| Rust sidecars (protocol, runner, KiCad/FreeCAD/sim stubs) | `rust/crates/*` | Integrated |
| Mutation-hook regression driver | `scripts/regression/run_suite.py`, `scripts/regression/mutation_hook.py` | Integrated |
| Roundtrip / DRC / simulation-stability regression | `scripts/regression/roundtrip.py`, `drc.py`, `simulation_stability.py` | Integrated (best-effort; stub sidecars) |
| `hw` CLI (login, branches, commits, merge, conflicts) | `cli/hw/` | Integrated |

## Phase 0.5 completion (audit estimate)

**~62% of v7.1 Phase 0.5 readiness criteria** have in-repo or test-covered implementations. Remaining work is mostly ops/product (billing, ToS, status page), host OSS subprocess wiring, import corpus, and durability drills.

| Criterion (v7.1 § Phase 0.5 Readiness) | Status |
|----------------------------------------|--------|
| HOS VC + collaboration + events + scene graph | Done (API + tests) |
| Rust sidecar protocol seam + mutation-hook regression | Done |
| `hw` CLI for VC operations | Done |
| OSS engines run as host subprocesses (not vendored) | **Partial** — sim subprocess infra yes; KiCad/FreeCAD still stub/noop in default binaries |
| Import pipeline (KiCad/FreeCAD corpus, import branches) | **Not started** (API/CLI) |
| Org signup / invite / roles E2E | **Partial** — org-scoped RBAC in API; no signup/invite flow |
| Cloud durability confirmed + DR runbook tested | **Docs only** — see DURABILITY_BETA.md |
| Billing, ToS, privacy, status page | **Out of repo** |
| Public roadmap published | **Expanded** — PUBLIC_ROADMAP.md |
| Legal / status page | **Stubs** — docs/legal/PLACEHOLDER.md, docs/ops/STATUS_PAGE.md |
| Collaboration stress (2-user soak) | **Documented** — see below |
| Two-week stable internal alpha | **Process** — not verifiable from git |

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
  curl -sf -X POST "$HCP_API_URL/v1/collaboration/presence" \
    -H "Authorization: Bearer $HCP_TOKEN_A" \
    -H "Content-Type: application/json" \
    -d "{\"projectId\":\"$PROJECT_ID\",\"status\":\"active\"}" >/dev/null
  curl -sf -X POST "$HCP_API_URL/v1/collaboration/locks" \
    -H "Authorization: Bearer $HCP_TOKEN_A" \
    -H "Content-Type: application/json" \
    -d "{\"projectId\":\"$PROJECT_ID\",\"resourceId\":\"doc/main\",\"ttlSeconds\":30}" >/dev/null
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
- Production deployment hardening beyond existing Terraform/Helm scaffolding
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
  api/tests/test_v1_endpoints.py -q

# CLI + regression unit tests
PYTHONPATH=api:.. python3 -m pytest cli/tests scripts/regression/tests -q

# Regression suites (roundtrip / drc / sim use bundled fixtures)
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
```

## Repository

**Canonical remote:** `git@github.com:josiah1203/HCP.git`  
Local clones may use a folder name such as `HCP_working`; treat that directory as the same monorepo.
