# ADR-003: Parser Abstraction Layer and Vendor Agnosticism

**Status:** Accepted  
**Date:** 2026-05-25  
**Owners:** Parser (PX), Tech Lead (TL)

## Context

HCP stores hardware artifacts from many EDA/CAD/CAM tools. Extension-only routing (`parser/registry.py`) works for open formats (KiCad, STEP, Gerber, BOM CSV) but couples behavior to filenames, not semantic domain or vendor. Downstream services (graph, search, SDK, web) must never depend on proprietary SDKs or vendor-specific JSON shapes.

PAL already abstracts cloud storage; parsers need the same boundary for ingest.

## Decision

Introduce **Parser Abstraction Layer (PrAL)** under `parser/pral/`:

1. **One canonical contract** — all parsers and plugins emit `ParsedOutput` schema version 1.1+ (see `parser/schema.py`). Unknown fields are ignored by graph auto-linker.
2. **Capability router** — resolve parser by priority: `source_tool` + extension → magic-byte sniff → extension map → `RawStore` fallback.
3. **Core parsers** — interchange-first parsers in `parser/pral/core/` (KiCad, STEP, Gerber, BOM, firmware, PDF, raw).
4. **Optional plugins** — proprietary vendors (SolidWorks, Autodesk, Altium) as sidecar plugins in `parser/pral/plugins/`, declared via `plugin.yaml`, never imported by `api/`.
5. **Converter path (V2)** — plugins without direct parse use `Converter` to produce neutral bytes (STEP/Gerber/BOM), then core parsers run on derived artifacts.

Parse failure never blocks storage or download (`parse_status = failed`, raw unchanged, 3× retry).

## Consequences

### Positive

- API and graph depend only on `ParsedOutput` + `object_type`, not vendor SDKs.
- Teams can upload native files today; interchange exports get full parse; stubs document V2 plugin contract.
- Additive schema 1.1 fields (`domain`, `representation`, `source_tool`, `capabilities`, `source_assets`) align with upload metadata and future `DERIVED_FROM` graph edges.

### Negative

- Two-level registry (PrAL + legacy `parser/registry.py` shim) until all imports migrate.
- Sidecar plugins add operational complexity (containers, queues `hcp.parse.plugin.{id}`).

## Alternatives considered

| Alternative | Rejected because |
|-------------|------------------|
| Per-vendor JSON blobs in Postgres | Forks downstream contracts; breaks search/graph |
| Vendor SDKs in `api/` | Violates §1.4; security and deploy coupling |
| Extension-only forever | Cannot route `.sldprt` / `.SchDoc` without false positives |

## References

- `docs/artifact-taxonomy.md` — domain vs vendor vs representation
- `docs/parser-plugins.md` — plugin contract and sidecar deployment
- HCP §7.2 ParsedOutput, §9 parser failure semantics, §1.3 V2 proprietary parsers
