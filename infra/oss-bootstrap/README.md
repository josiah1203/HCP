# hcp-oss fork bootstrap (Phase 0.5)

Templates and scripts to create **`hcp-oss/kicad`** and **`hcp-oss/freecad`** without vendoring GPL sources into the HCP monorepo.

## Layout

| Path | Purpose |
|------|---------|
| [`templates/`](templates/) | Per-repo `FORK_NOTES.md`, `HCP_INTEGRATION.md`, `UPSTREAM_SYNC.md` |
| [`kicad/`](kicad/) | KiCad upstream-sync workflow + `bootstrap-repo.sh` |
| [`freecad/`](freecad/) | FreeCAD upstream-sync workflow + `bootstrap-repo.sh` |

## Branch model

Each fork maintains:

- **`upstream/main`** — tracks upstream release branch only (force-pushed or merged from upstream remote).
- **`hcp/integration`** — HCP-owned headless entrypoints, build docs, incremental chrome strip.

## Quick start (copy-paste)

Replace `YOUR_GITHUB_ORG` with `hcp-oss` (or your org) and run from a clean directory **outside** this monorepo:

```bash
export HCP_OSS_ORG=YOUR_GITHUB_ORG
bash /path/to/HCP/infra/oss-bootstrap/kicad/bootstrap-repo.sh
bash /path/to/HCP/infra/oss-bootstrap/freecad/bootstrap-repo.sh
```

Scripts create a local mirror, add steward docs from templates, push branches, and print GitHub workflow install steps.

## License boundary

GPL/LGPL code lives only in `hcp-oss/*`. The platform monorepo consumes **built binaries** on `PATH` (`kicad-cli`, `freecadcmd`) via Rust sidecars — see [`docs/OSS_HOST_DEPENDENCIES.md`](../../docs/OSS_HOST_DEPENDENCIES.md).
