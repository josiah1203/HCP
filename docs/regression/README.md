# Fork regression harness

This doc describes the **required regression suite categories** for forked CAD sidecars (KiCad/FreeCAD) and how to run them locally and in CI.

This is **only a harness contract**: it defines entrypoints, inputs/outputs, and success criteria. It does not ship KiCad/FreeCAD fixtures here.

## Suites

### 1) Roundtrip suite

Goal: ensure import → HOS store → export → import is stable for supported formats.

- **Inputs**: a corpus directory containing tool-native projects and/or interchange exports
- **Process**:
  - Open project via sidecar
  - Export into one or more interchange formats
  - Upload artifacts to HOS
  - Re-import exported artifacts and compare normalized representations
- **Output**: JUnit XML + JSON summary

### 2) Mutation hook suite

Goal: randomized or enumerated tool mutations must produce **consistent scene graph deltas** and remain internally valid.

- **Inputs**: a seed project + mutation generator config
- **Process**:
  - Apply mutations via `hcp/document/applyMutations`
  - Ensure sidecar emits scene graph upserts (nodes/edges) that pass schema validation
- **Output**: JSON traces (seed, mutation list, observed RPC traffic) + summary

### 3) DRC correctness suite

Goal: DRC results match known-good expectations for a fixed corpus.

- **Inputs**: design corpus + expected DRC outputs (goldens)
- **Process**:
  - Invoke tool DRC (sidecar-specific)
  - Compare normalized violation sets to expected
- **Output**: diff artifacts; failures must be reproducible from saved seed inputs

### 4) Simulation stability suite

Goal: simulation results are stable across versions for known-good inputs.

- **Inputs**: circuits/assemblies + simulation configs + golden outputs
- **Process**:
  - Dispatch simulation jobs (outside this repo’s scope)
  - Compare normalized results to golden baselines
- **Output**: numeric tolerances + drift report

## Harness interfaces (this repo)

- `scripts/regression/run_suite.py`: uniform CLI wrapper for running a suite.
- `scripts/regression/{roundtrip,drc,simulation_stability,mutation_hook}.py`: suite drivers.
- `docs/protocol/jsonrpc/*.json`: protocol contracts that suites can validate against.

## Example commands

Build sidecar binaries once:

```bash
source "$HOME/.cargo/env"
cargo build -p kicad-sidecar -p freecad-sidecar --manifest-path rust/Cargo.toml
```

### Mutation hook (implemented)

Drives `hcp/ping`, `hcp/project/open`, and `hcp/document/applyMutations` over stdio JSON-RPC.
KiCad sidecar emits `HCP_TRACE:` lines for `hcp/sceneGraph/upsertNodes` / `upsertEdges`; the harness
validates schema fields and expected node types.

```bash
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 8 \
  --out out/regression/mutation_hook.json
```

### Roundtrip (best-effort)

Export fingerprint stability + re-apply mutations (KiCad scene graph). Uses bundled corpus by default:

```bash
python3 scripts/regression/run_suite.py roundtrip \
  --corpus scripts/regression/fixtures/roundtrip_corpus
```

Driver: `scripts/regression/roundtrip.py`.

### DRC (best-effort)

Derives normalized violations from KiCad pcb mutation scene traces; compares to goldens. With `HCP_USE_HOST_OSS=1`, extend to call host DRC when subprocess bindings land.

```bash
python3 scripts/regression/run_suite.py drc \
  --corpus scripts/regression/fixtures/drc_corpus \
  --goldens scripts/regression/fixtures/drc_goldens
```

Driver: `scripts/regression/drc.py`.

### Simulation stability

Runs stub (or configured) simulation subprocesses and compares normalized envelopes to goldens:

```bash
python3 scripts/regression/run_suite.py simulation-stability \
  --corpus scripts/regression/fixtures/sim_corpus \
  --goldens scripts/regression/fixtures/sim_goldens
```

Driver: `scripts/regression/simulation_stability.py`.

