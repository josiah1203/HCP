# Artifact Taxonomy

Hardware artifacts in HCP are classified along **three independent axes**. Downstream services use only canonical fields on `ParsedOutput` and `object_type`, never raw extensions alone.

## Axes

| Axis | Field(s) | Values (examples) | Meaning |
|------|-----------|-------------------|---------|
| **Domain** | `domain`, `file_type`, `object_type` | `electrical`, `mechanical`, `manufacturing`, `firmware`, `document` | What engineering discipline the artifact belongs to |
| **Vendor / tool** | `source_tool`, `tool_name` | `KiCad`, `SolidWorks`, `Altium`, `Fusion360` | Which application produced the bytes |
| **Representation** | `representation` | `native`, `interchange`, `derived` | Whether the file is proprietary native, neutral export, or platform-derived |

`source_format` is the file extension (e.g. `.kicad_pcb`, `.step`, `.gbr`) — not the same as representation.

## Representation rules

| Pattern | `representation` | Notes |
|---------|------------------|-------|
| `.kicad_pcb`, `.kicad_sch`, `.sldprt`, `.SchDoc`, `.f3d` | `native` | Tool-specific; may need plugin or converter in V2 |
| `.step`, `.stp`, `.stl`, Gerber/drill, BOM CSV/XLSX | `interchange` | Parsed by core PrAL parsers in V1 |
| Re-upload after converter (STEP from SolidWorks export) | `derived` | Links to native via `source_assets` / graph `DERIVED_FROM` (Phase C) |

## Domain × vendor × preferred interchange

| Domain | Native examples | Preferred interchange for V1 parse | Core parser |
|--------|-----------------|-----------------------------------|-------------|
| Electrical | KiCad `.kicad_pcb`, Altium `.SchDoc` | Gerber, ODB++, BOM CSV | KiCad*, Gerber, BOM |
| Mechanical | SolidWorks `.sldprt`, Fusion `.f3d` | STEP, STL | StepParser |
| Manufacturing | CAM-specific | Gerber, drill, pick-place CSV | GerberParser, BOM |
| Firmware | `.elf`, `.hex`, `.uf2` | (binary is canonical) | FirmwareStore |
| Document | `.pdf` | PDF | PDFStore |

\* KiCad native formats are open and supported in core, not plugins.

## Upload inference (API)

When upload form metadata is omitted, infer:

- `domain` from extension + optional `source_tool` (see `api/app/services/object_types.py` — owned by API agent).
- `representation` from extension per table above.
- `source_format` from `Path(filename).suffix.lower()`.

Parser worker passes through persisted `source_tool` / `domain` / `representation` when present on the `versions` row (Alembic migration pending).

## Capabilities

`capabilities` on `ParsedOutput` advertises what downstream may consume without inspecting nested dicts:

| Capability | When set |
|------------|----------|
| `has_bom` | `bom_rows` non-empty |
| `has_geometry` | `mechanical` or board dimensions present |
| `has_gerber_stack` | `gerber` metadata present |
| `has_components` | `components` non-empty |
| `has_firmware` | `firmware` block present |

## Release bundles

Multi-file uploads use `manifest.json` at bundle root (see plan `manifest-schema.json`). Each member carries its own `domain` and `role`; relationships are applied via graph link API, not parser registry.
