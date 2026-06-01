# Phase 0.5 (public beta) readiness

Phase 0.5 delivers a **server-ready** platform for hardware version control, collaboration, events, scene graph snapshots, OSS tool sidecars (Rust runners), and a minimal `hw` CLI—without shipping a full Rust IDE shell (developed separately).

Canonical engineering spec: `~/.cursor/HCP.md`. Detailed sidecar port plan: `.cursor/plans/hcp-phase05-beta_411f672c.plan.md`.

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
