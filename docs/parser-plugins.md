# Parser Plugins (PrAL)

Optional vendor parsers live under `parser/pral/plugins/`. The core platform **never** imports SolidWorks, Autodesk, or Altium libraries.

## Layout

```
parser/pral/
  interfaces/parser_plugin.py   # contract
  interfaces/converter.py     # native → interchange (V2)
  registry.py                 # routing
  core/                       # built-in parsers
  plugins/
    <plugin_id>/
      plugin.yaml
      parser.py               # stub or full implementation
```

## plugin.yaml

```yaml
id: stub_solidworks
vendor: Dassault Systèmes
domains: [mechanical]
extensions: [.sldprt, .sldasm, .slddrw]
requires_sidecar: true
output_capabilities: [has_geometry]
source_tools: [SolidWorks]
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique plugin id; queue `hcp.parse.plugin.{id}` when sidecar |
| `vendor` | yes | Display name |
| `domains` | yes | Taxonomy domains this plugin handles |
| `extensions` | yes | Lowercase extensions including dot |
| `requires_sidecar` | yes | If true, parse runs out-of-process |
| `output_capabilities` | yes | Declared `ParsedOutput.capabilities` |
| `source_tools` | yes | Router keys for explicit `source_tool` match |

## Parser plugin contract

Implement `ParserPlugin` from `parser/pral/interfaces/parser_plugin.py`:

```python
def parse(self, file_bytes: bytes, context: ParseContext) -> ParsedOutput:
    ...
```

- Must return valid `ParsedOutput` (Pydantic); never raise for user data errors — use `errors` / `warnings`.
- Set `schema_version` to `1.1`, populate `domain`, `representation`, `source_tool`, `source_format` when known.
- On sidecar failure, worker sets `parse_status = failed`; raw file unchanged.

## Sidecar deployment pattern

For `requires_sidecar: true`:

1. **Isolated container** with vendor runtime (license-bound).
2. **Transport** — HTTP or Unix socket from parser worker, or Celery queue `hcp.parse.plugin.{id}`.
3. **Request** — `{ version_id, storage_key, filename, source_tool }`; worker already downloaded bytes for core parsers; sidecar may re-fetch from signed URL.
4. **Response** — JSON matching `ParsedOutput` 1.1; worker uploads `parsed/output.json` as today.
5. **No shared filesystem** with API — only PAL storage keys.

V1 ships **stubs** (`stub_solidworks`, `stub_altium`, `stub_autodesk`) that document the contract and return `parse_status`-compatible output with `errors` explaining sidecar requirement.

## Converter path (V2)

When direct parse is unavailable:

1. Plugin `Converter.convert(native_bytes) -> ConvertResult` with interchange bytes + target extension.
2. API or worker stores derived artifact as new version with `representation=derived`.
3. PrAL routes derived file to `StepParser` / `GerberParser` / `BOMParser`.
4. `source_assets` links native URI to derived URI for graph `DERIVED_FROM`.

## Enabling plugins

Per-org feature flags (`provider_config` / `org_features` JSONB) — V2. CI runs stub plugins without proprietary SDKs.

## Testing

- Contract test: plugin output validates against `ParsedOutput` 1.1.
- Routing test: `source_tool=SolidWorks` + `.sldprt` → stub plugin before extension-only STEP route.
- Sidecar tests: optional CI job with mock HTTP server.
