# Fork regression harness (skeleton)

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
- `scripts/regression/suites/*.py`: suite drivers (thin adapters).
- `docs/protocol/jsonrpc/*.json`: protocol contracts that suites can validate against.

## Example commands (skeleton)

```bash
python3 scripts/regression/run_suite.py roundtrip --corpus path/to/corpus
python3 scripts/regression/run_suite.py mutation-hook --seed path/to/project --mutations 100
python3 scripts/regression/run_suite.py drc --corpus path/to/corpus --goldens path/to/goldens
python3 scripts/regression/run_suite.py simulation-stability --corpus path/to/corpus --goldens path/to/goldens
```

