# HCP Engineering Plan

The canonical engineering specification for the currently-implemented phases lives at `~/.cursor/HCP.md` (v1.0).

V5 (IDE + Version Control / fork integration) planning is tracked as a separate coordination effort and introduces additional workstreams and verify hooks (see `AGENTS.md`, `docs/V5_PARALLEL_WORKSTREAMS.md`, and `make v5-verify-*`).

This repository implements **V1 — Hardware Object Store (HOS)** per that document.

## Current implementation status

| Phase | Status |
|-------|--------|
| 1 — Storage Core | **Partial** — immutable upload/dedup, lifecycle states, JWT + API keys, RBAC, audit log, bundle ingest (`manifest.json`), search facets; PAL on-prem + AWS S3 stub |
| 2 — Parser | **Partial** — Celery worker, KiCad/BOM/Gerber/STEP/Raw parsers, parse-never-blocks-storage; PrAL plugin stubs (V2 path) |
| 3 — Graph | **Partial** — Neo4j schema + auto-linker, object-level links, `DERIVED_FROM` edges, BOM diff API; OpenSearch/indexing not production-ready |
| 4 — SDK / CLI | **Partial** — Python + TypeScript SDKs, GitHub `hcp-upload` action; no published packages |
| 5 — Web UI | **Partial** — four views (upload, object, graph, search), auth context; not full WCAG/perf gate |
| 6 — Infra / CI | **Partial** — Terraform provider modules, Helm charts, GitHub Actions lint/test/build; no prod deploy gate |

**V1 product framing:** see [V1_MVP_SCOPE.md](./V1_MVP_SCOPE.md) — *S3 + PLM-lite versioning for hardware files* (not full Git).

**V1.5+ roadmap:** see [V1_5_HARDWAREGIT.md](./V1_5_HARDWAREGIT.md) — HardwareGit (diff/merge, branches) deferred until bundle + BOM/board diff primitives land.
