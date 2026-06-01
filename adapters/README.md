# HNF adapters (Phase 0.5 split prep)

Apache 2.0 crates mirroring the future **`hcp-adapters`** GitHub org. Published path for extraction:

| Crate | Future repo |
|-------|-------------|
| `hnf-adapter-sdk` | `hcp-adapters/hnf-adapter-sdk` |
| `hnf-kicad` | `hcp-adapters/hnf-kicad` |
| `hnf-freecad` | `hcp-adapters/hnf-freecad` |

HCP sidecars in `rust/crates/*-sidecar` depend on these via **path** until `v0.1.0` tags land on crates.io or git.

```bash
cd adapters && cargo test
cd ../rust && cargo test
```
