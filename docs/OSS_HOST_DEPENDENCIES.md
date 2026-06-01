# OSS host dependencies (Phase 0.5 sidecars)

v7.1 **porting** means Rust sidecar frontends that run **existing OSS engines as separate host processes**, with HNF adapter glue replacing direct file I/O at the protocol boundary. This monorepo does **not** vendor KiCad, FreeCAD, OCCT, ngspice, OpenEMS, or Elmer source trees unless explicitly added later.

## Summary table

| Tool | In-repo code | Runtime dependency | Integration status |
|------|----------------|-------------------|-------------------|
| **KiCad 8.x** | `rust/crates/kicad-sidecar`, `parser/parsers/kicad_*`, KiCad fixtures | `kicad-cli` / headless KiCad on `PATH` (not bundled) | **Protocol + stub binding** — JSON-RPC handlers, mutation→scene-graph mapping, `StubKiCadBinding` in production `build_stdio_runner()`; no subprocess to KiCad yet |
| **FreeCAD 1.x** | `rust/crates/freecad-sidecar` | `freecadcmd` or FreeCAD batch on `PATH` | **Protocol + noop bridge** — `NoopFreecadEngineBridge`; mechanical mutations map to scene graph without launching FreeCAD |
| **OCCT 7.x** | None (no OCCT crate or submodule) | Via FreeCAD build or standalone OCCT install | **Not integrated** — mechanical domain uses HNF mutation payloads only; STEP/IGES via future FreeCAD/OCCT subprocess |
| **ngspice** | `rust/crates/simulation-sidecars` bin `ngspice` | `ngspice` on `PATH` when `command` set in payload | **Subprocess runner** — default is `sh -lc printf stub-run…`; set `simulation.command` to `["ngspice", …]` for real runs |
| **OpenEMS** | `simulation-sidecars` bin `openems` | OpenEMS install on host | Same as ngspice — stub default, real via `command` override |
| **Elmer** | `simulation-sidecars` bin `elmer` | Elmer FEM solver on host | Same as ngspice — stub default, real via `command` override |

## What the repo contains vs the host

### In monorepo

- **JSON-RPC contracts:** `docs/protocol/jsonrpc/hcp-ide-sidecar.v0.json`, `hcp-sidecar-scenegraph.v0.json`
- **Rust workspace** (`rust/`): `sidecar-protocol`, `sidecar-runner`, `hnf-adapter`, `kicad-sidecar`, `freecad-sidecar`, `simulation-sidecars`
- **Parser interchange** (V1 path): Python parsers for `.kicad_sch` / `.kicad_pcb` under `parser/` — reads files uploaded to HOS; separate from live sidecar editing
- **Regression:** mutation-hook driver (`scripts/regression/mutation_hook.py`) exercises sidecars over stdio; roundtrip/DRC/simulation suite entrypoints remain skeletons

### On the host (install separately)

| Package | Typical binary | Used by |
|---------|----------------|---------|
| KiCad 8.x | `kicad-cli` | Future `KiCadSubprocessBinding` (not wired in `main` today) |
| FreeCAD 1.x | `freecadcmd` | Future `FreecadEngineBridge` implementation |
| OCCT | (inside FreeCAD or dev libs) | BRep/STEP — Phase 0 full plan, not in repo |
| ngspice | `ngspice` | `simulation-sidecars` when `command` provided |
| OpenEMS | project-specific launcher | same |
| Elmer | `ElmerSolver` / `ElmerGrid` | same |

## Subprocess paths

- **Simulation sidecars:** `SystemSubprocessRunner` runs `std::process::Command` with program/args from `SimulationConfig.command`, or the built-in stub (`sh -lc printf 'stub-run …'`).
- **KiCad / FreeCAD sidecars:** No OSS subprocess spawn in release binaries today; mutations are translated in-process to scene-graph deltas (deterministic for regression).

## Gaps for real OSS integration

1. **KiCad:** Implement `SubprocessKiCadBinding` (env e.g. `HCP_KICAD_CLI`) calling headless export/DRC/mutation APIs; keep stub for CI.
2. **FreeCAD:** Replace `NoopFreecadEngineBridge` with `freecadcmd` driver + FCStd staging.
3. **OCCT:** No direct sidecar; depend on FreeCAD/OCCT host install for STEP/BRep.
4. **Simulators:** Default discovery (`which ngspice`) behind `HCP_SIM_USE_HOST=1` optional flag; document golden corpora for simulation-stability suite.
5. **Import pipeline (v7.1 beta):** Legacy import branches + corpus testing — not implemented in API/CLI yet (see `docs/PHASE_0.5.md` gaps).

## Verify sidecars locally

```bash
source "$HOME/.cargo/env"
cd rust && cargo build -p kicad-sidecar -p freecad-sidecar -p simulation-sidecars
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4
```
