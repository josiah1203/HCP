# V1 MVP scope — PLM-lite for hardware files

HCP V1 is **not** HardwareGit. It is **immutable object storage with PLM-lite versioning** for hardware artifacts: think **S3 + audit + lifecycle + interchange parsers**, not Git branches and merge.

## What V1 delivers

| Capability | Description |
|------------|-------------|
| **Immutable versions** | Every upload creates a new version; content-addressed dedup; no in-place overwrite |
| **Org-scoped tenancy** | All queries and storage paths filtered by `org_id` |
| **Auth & audit** | JWT + API keys, RBAC, audit log on writes |
| **Lifecycle** | Draft → released → obsolete (and related states) on versions |
| **Interchange parsers** | KiCad, BOM CSV, Gerber, STEP, Raw — parse failures never block storage |
| **Bundle ingest** | ZIP + `manifest.json` (schema 1.0) for multi-file releases with relationship hints |
| **PartGraph (lite)** | Neo4j links (USES, CONTAINS, DERIVED_FROM, etc.) and BOM diff between versions |
| **Search** | Postgres-backed search with domain/source-tool facets |
| **PAL** | Provider abstraction for storage/secrets/queue (on-prem MinIO + AWS stub) |

## Explicit non-goals (V1)

- Branching, merging, or three-way conflict resolution
- Real-time co-editing or browser CAD
- Proprietary native CAD parsers (SolidWorks, Altium, etc.) — interchange only
- Full PLM workflow (ECO gates, ERP sync, supplier portals)
- Marketplace, SimCompute, AI copilots

## Mental model for users

1. **Upload** a file or release bundle → get version `N`.
2. **Track** who changed what via audit + immutable history.
3. **Parse** asynchronously into structured BOM/graph hints.
4. **Compare** BOM lines across versions (`GET /v1/bom/{id}/diff/{a}/{b}`).
5. **Link** related objects in PartGraph for traceability.

For Git-like semantics (branches, merge, bundle diffs), see [V1_5_HARDWAREGIT.md](./V1_5_HARDWAREGIT.md).
