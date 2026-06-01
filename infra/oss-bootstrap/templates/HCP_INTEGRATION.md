# HCP integration — {{TOOL_NAME}}

How the Hardware Cloud Platform attaches to this fork **without** linking GPL code into proprietary services.

## Runtime contract

| Env var | Default | Role |
|---------|---------|------|
| `HCP_USE_HOST_OSS` | `0` | When `1`, HCP sidecars spawn host binaries from this fork |
| `HCP_KICAD_CLI` | `kicad-cli` | KiCad only — override CLI path |
| `HCP_FREECAD_CMD` | `freecadcmd` | FreeCAD only — override batch interpreter |

Sidecar JSON-RPC (stdio today; gRPC on fork builds long-term) → **hnf-adapter crates** (`hcp-adapters/*`) → subprocess → **this fork's binaries**.

## Phase 0.5 scope (realistic)

1. **Ship** documented headless/batch entry on `hcp/integration` (even if full chrome strip is ongoing).
2. **Document** which subsystems HCP will patch (I/O layer, plugin load path, env defaults).
3. **Do not** block beta on complete UI removal — use feature flags and incremental PRs.

## Headless entrypoint (steward checklist)

- [ ] Build recipe produces `{{PRIMARY_CLI}}` on Linux/macOS CI
- [ ] Smoke: version command exits 0 in Docker image used by HCP dev
- [ ] Export path documented for roundtrip regression (format: {{EXPORT_FORMATS}})
- [ ] DRC/batch hooks identified (KiCad: `kicad-cli drc`; FreeCAD: macro via `freecadcmd -c`)

## Adapter boundary (Apache 2.0)

Scene-graph mapping and HNF mutations live in:

- `hcp-adapters/hnf-adapter-sdk`
- `hcp-adapters/hnf-{{ADAPTER_SUFFIX}}`

This fork must **not** import HCP platform crates. Adapters run in the HCP monorepo / `hcp-platform` and speak file formats + JSON-RPC only.

## Local dev loop

```bash
# Build fork (project-specific — fill in after bootstrap)
# export PATH="$PWD/build/bin:$PATH"
export HCP_USE_HOST_OSS=1
cd /path/to/HCP/rust && cargo test -p kicad-sidecar -p freecad-sidecar
```

## Verification

From HCP monorepo:

```bash
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4
```

With host OSS: set `HCP_USE_HOST_OSS=1` and ensure `{{PRIMARY_CLI}}` is on `PATH`.
