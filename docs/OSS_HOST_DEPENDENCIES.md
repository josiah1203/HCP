# OSS host dependencies (Phase 0.5 sidecars)

v7.1 **porting** means Rust sidecar frontends that run **existing OSS engines as separate host processes**, with HNF adapter glue replacing direct file I/O at the protocol boundary. This monorepo does **not** vendor KiCad, FreeCAD, OCCT, ngspice, OpenEMS, or Elmer source trees.

Fork bootstrap templates live under [`infra/oss-bootstrap/`](../infra/oss-bootstrap/). Apache adapter crates live under [`adapters/`](../adapters/) (future `hcp-adapters/*` org).

## Summary table

| Tool | In-repo code | Runtime dependency | Integration status |
|------|----------------|-------------------|-------------------|
| **KiCad 8.x** | `rust/crates/kicad-sidecar`, `adapters/crates/hnf-kicad`, `parser/parsers/kicad_*` | `kicad-cli` on `PATH` (from [`hcp-oss/kicad`](https://github.com/hcp-oss/kicad) `hcp/integration`) | **Subprocess + stub** — `SubprocessKiCadBinding` when `HCP_USE_HOST_OSS=1`; `StubKiCadBinding` default (CI) |
| **FreeCAD 1.x** | `rust/crates/freecad-sidecar`, `adapters/crates/hnf-freecad` | `freecadcmd` on `PATH` (from [`hcp-oss/freecad`](https://github.com/hcp-oss/freecad)) | **Subprocess + noop** — `SubprocessFreecadEngineBridge` when `HCP_USE_HOST_OSS=1`; `NoopFreecadEngineBridge` default |
| **OCCT 7.x** | None | Via FreeCAD build | **Not integrated** — STEP/BRep via FreeCAD subprocess |
| **ngspice** | `rust/crates/simulation-sidecars` | `ngspice` on `PATH` when `HCP_SIM_USE_HOST=1` | **Subprocess** — auto-`which` or explicit `simulation.command` |
| **OpenEMS** | same | `openems` on `PATH` when host flag set | same |
| **Elmer** | same | `ElmerSolver` on `PATH` when host flag set | same |

## Environment flags

| Variable | Default | Effect |
|----------|---------|--------|
| `HCP_USE_HOST_OSS` | `0` | `1` → KiCad/FreeCAD sidecars use host subprocess bindings |
| `HCP_KICAD_CLI` | `kicad-cli` | KiCad CLI binary path |
| `HCP_KICAD_TIMEOUT_SECS` | `120` | Reserved for long-running KiCad jobs |
| `HCP_FREECAD_CMD` | `freecadcmd` | FreeCAD batch interpreter |
| `HCP_SIM_USE_HOST` | `0` | `1` → simulation sidecars resolve `ngspice` / `openems` / `ElmerSolver` via `PATH` instead of stub `sh` |

Host subprocess attempts emit `HCP_HOST_OSS:` JSON lines on stderr for regression harnesses.

## What the repo contains vs the host

### In monorepo

- **Adapter workspace** (`adapters/`): `hnf-adapter-sdk`, `hnf-kicad`, `hnf-freecad` (mirrors `hcp-adapters/*`)
- **JSON-RPC contracts:** `docs/protocol/jsonrpc/hcp-ide-sidecar.v0.json`, `hcp-sidecar-scenegraph.v0.json`
- **Rust workspace** (`rust/`): sidecars + `hnf-adapter` (re-exports SDK for compatibility)
- **OSS bootstrap:** `infra/oss-bootstrap/` — fork docs, upstream-sync workflows, `bootstrap-repo.sh` for KiCad/FreeCAD
- **Parser interchange:** Python parsers under `parser/` — file upload path separate from live sidecars

### On the host (install separately)

| Package | Binary | Build from |
|---------|--------|------------|
| KiCad 8.x | `kicad-cli` | `hcp-oss/kicad` branch `hcp/integration` — see `infra/oss-bootstrap/kicad/bootstrap-repo.sh` |
| FreeCAD 1.x | `freecadcmd` | `hcp-oss/freecad` — see `infra/oss-bootstrap/freecad/bootstrap-repo.sh` |
| ngspice / OpenEMS / Elmer | solver binaries | Upstream or distro packages |

## Subprocess paths

- **KiCad:** `SubprocessKiCadBinding` probes `kicad-cli version`, stages under `workspaceRoot`, maps mutations in-process (headless mutation API on fork roadmap).
- **FreeCAD:** `SubprocessFreecadEngineBridge` probes `freecadcmd --version` on `hcp/project/open`.
- **Simulation:** `SystemSubprocessRunner` runs discovered or configured commands.

## CI vs local dev

| Mode | Flags | Behavior |
|------|-------|----------|
| CI (default) | unset | Stubs only — no KiCad/FreeCAD/ngspice required |
| Local host OSS | `HCP_USE_HOST_OSS=1` | KiCad + FreeCAD probes + trace events |
| Local sim | `HCP_SIM_USE_HOST=1` | Real solver binaries when on `PATH` |

Optional CI job: install KiCad/FreeCAD on runner, set flags, run `cargo test` subset.

## Verify sidecars locally

```bash
source "$HOME/.cargo/env"
cd adapters && cargo test
cd ../rust && cargo test

# Stub mode (CI default)
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4

# Host OSS (requires built forks on PATH)
export HCP_USE_HOST_OSS=1
export HCP_SIM_USE_HOST=1
cd rust && cargo test -p kicad-sidecar -p freecad-sidecar -p simulation-sidecars
```

## Remaining gaps (post Phase B)

1. Full headless mutation/export scripts on `hcp-oss/*` `hcp/integration` branches.
2. Publish `hnf-*` crates to crates.io / git tags; switch sidecars from path to versioned deps.
3. Import pipeline + roundtrip/DRC/sim-stability regression (see `docs/PHASE_0.5.md`).
