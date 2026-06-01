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
| Public roadmap published | **Stub** — PUBLIC_ROADMAP.md |
| Two-week stable internal alpha | **Process** — not verifiable from git |

## Out of scope for Phase 0.5

- Runnable Rust IDE shell (host uses JSON-RPC contracts in `docs/protocol/jsonrpc/`)
- Full roundtrip / DRC / simulation-stability regression drivers (harness stubs remain)
- Production deployment hardening beyond existing Terraform/Helm scaffolding

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

# Optional: mutation-hook suite (builds sidecars first)
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4
```

## Repository

**Canonical remote:** `git@github.com:josiah1203/HCP.git`  
Local clones may use a folder name such as `HCP_working`; treat that directory as the same monorepo.
