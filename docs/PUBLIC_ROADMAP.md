# HCP public roadmap (Phase 0.5 beta)

This stub satisfies the v7.1 Phase 0.5 requirement to publish what is and is not built. Canonical engineering detail: `~/Desktop/HCP_Engineering_Plan_v7.1.md` (or synced `docs/HCP_Engineering_Plan.md`).

## Available now (this repository)

- **HOS / cross-domain version control (API):** branches, commits, diff, merge, conflict resolution with auto-complete merge when all conflicts resolved
- **HNF documents:** validation, snapshots on commit, scene graph + snapshots
- **Collaboration (beta):** polling presence, advisory soft locks
- **Event stream:** taxonomy-aligned publisher for commits, scene graph, collaboration
- **Rust OSS sidecars (protocol seam):** KiCad, FreeCAD, ngspice/OpenEMS/Elmer runners — JSON-RPC over stdio; host OSS binaries not vendored (see [OSS_HOST_DEPENDENCIES.md](./OSS_HOST_DEPENDENCIES.md))
- **`hw` CLI:** login, branches, commits, merge, conflicts
- **V1 storage + parsers:** upload, PAL, KiCad file parsers, Celery parse pipeline

## In progress / partial

- **OSS engine subprocess integration:** sidecars run; KiCad/FreeCAD use in-process stubs until host tools are wired
- **Regression:** mutation-hook suite implemented; roundtrip, DRC, simulation-stability drivers are contract-only
- **Import from legacy formats:** KiCad 6/7/8 and FreeCAD import branches per v7.1 — not yet end-to-end in API/CLI

## Not in Phase 0.5 (communicated out of scope)

- Runnable unified Rust IDE shell (developed separately; uses `docs/protocol/jsonrpc/`)
- Full simulation dispatch cloud, package registry, AI layer
- Enterprise SSO, on-prem production hardening beyond existing Terraform/Helm scaffolding
- Billing, ToS, and public status page (operational; not in this monorepo)

## Near-term priorities (post–Phase 0.5 code)

1. Host-tool subprocess bindings for KiCad and FreeCAD sidecars
2. Import pipeline + corpus-tested loss rate (&lt; 5% per v7.1 gate)
3. Cloud HOS durability verification and runbooks
4. Org signup/invite E2E and billing flow (product/ops)

Last updated: coordinated with Phase 0.5 audit (see `docs/PHASE_0.5.md`).
