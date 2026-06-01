# Import corpus (Phase 0.5)

Golden fixtures for the project import pipeline (`POST /v1/projects/{id}/import`) and regression gates.

## Loss gate

Imports must preserve **≥ 95%** of counted design elements (symbol / net / sheet counts from KiCad parsers):

```
loss_ratio = max(0, (source_elements - imported_elements) / source_elements)
```

CI fails when `loss_ratio >= 0.05` on the corpus subset exercised in `api/tests/test_import_pipeline.py`.

## Layout

| Path | Description |
|------|-------------|
| `minimal/kicad_sch/` | Minimal schematic with two symbols (stub) |
| `minimal/kicad_zip/` | Zip archive layout for multi-file imports |

Add real KiCad projects under `kicad/` as they are cleared for redistribution. Do not commit GPL project sources without license review.

## Running locally

```bash
cd api && PYTHONPATH=.. pytest tests/test_import_pipeline.py -q
hw import --project-id <uuid> --format kicad --file tests/fixtures/import_corpus/minimal/design.kicad_sch --json
```
