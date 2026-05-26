# V1.5+ roadmap — HardwareGit

**HardwareGit** is the V1.5+ product line: Git-inspired workflows for hardware data (branches, merge, solid bundle diffs). It is **out of V1 MVP** scope; this document captures prerequisites and sequencing only.

## Prerequisites (build before branches/merge)

| Primitive | Status (V1) | V1.5 target |
|-----------|---------------|-------------|
| **Immutable versions + manifest bundles** | ZIP ingest + `manifest.json` schema 1.0 | Manifest schema 1.1: derived artifacts, stronger validation |
| **BOM diff** | `GET /v1/bom/{id}/diff/{a}/{b}` (row-level added/removed/changed) | Stable diff keys, qty/ref-des normalization |
| **Board / assembly diff** | Not started | Netlist/PCB semantic diff (KiCad interchange) |
| **DERIVED_FROM edges** | Graph schema + bundle relationships | Auto-link from converter outputs (PrAL) |
| **Bundle graph** | Object-level CONTAINS/USES from manifest | Full release graph + “what changed in this bundle” view |

## Proposed V1.5 phases (docs only)

1. **Diff layer** — BOM diff hardening, board diff spike, bundle-level change summary (no branches).
2. **Merge semantics (read-only)** — suggest merge resolutions for BOM rows; human-approved apply (still no branch heads).
3. **Branches** — named refs on projects, fast-forward only at first; three-way merge later.
4. **HardwareGit UX** — SDK/CLI + web flows for compare → review → promote.

## Non-goals until primitives land

- Do not ship branch/merge APIs without BOM + bundle diff reliability and derived-artifact lineage.
- Do not implement proprietary CAD merge; interchange and manifest-driven bundles only.

## Related ADRs / specs

- [ADR-003 — Parser abstraction layer](./ADR/ADR-003-parser-abstraction-layer.md) — converters and derived artifacts
- [manifest-schema.json](./manifest-schema.json) — bundle contract
- [artifact-taxonomy.md](./artifact-taxonomy.md) — domain, representation, lifecycle
