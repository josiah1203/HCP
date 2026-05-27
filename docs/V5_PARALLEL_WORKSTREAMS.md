# V5 parallel workstreams (IDE + Version Control)

V5 introduces new workstreams (IDE shell, fork integration contracts, and a “Git-like” hardware version-control backend). To keep iteration fast and reduce cross-talk, run each workstream in its own git worktree, and use additive `make v5-verify-<id>` targets.

## Setup

```bash
./scripts/v2-worktree.sh create-v5 ide
cd ../HCP_working-v5-ide
git switch -c feat/hcp-v5-ide-extension-host-scaffold
make v5-verify-ide
```

List or remove worktrees:

```bash
./scripts/v2-worktree.sh list-v5
./scripts/v2-worktree.sh remove-v5 ide
```

## Parallel verification matrix

The `v5-verify-*` targets are intentionally **lightweight** and **additive**. If a workstream isn’t implemented yet, the verify target should **skip and succeed** with a message.

| Command | Safe concurrent? | Notes |
|---------|------------------|-------|
| `make v5-verify-hos` | Yes | Intended to cover server-side VCS/commit graph work as it lands |
| `make v5-verify-events` | Yes | Event stream scaffolding (initially a no-op) |
| `make v5-verify-scene` | Yes | Scene graph scaffolding (initially a no-op) |
| `make v5-verify-fork` | Yes | Protocol/contracts + harness scaffolding (initially a no-op) |
| `make v5-verify-ide` | Yes | Reuses existing web lint hooks when present |
| `make v5-verify-marketplace` | Yes | Marketplace scaffolding (initially a no-op) |
| `make v5-verify-registry` | Yes | Registry scaffolding (initially a no-op) |
| `make v5-verify-cli` | Yes | CLI scaffolding (initially a no-op) |
| `make v5-verify-parallel` | Yes | Runs a small subset with `-j` |

## Relationship to V2

- V2 work continues to use `make v2-verify-<id>` and `docs/V2_PARALLEL_WORKSTREAMS.md`.
- V5 verification targets are separate to avoid forcing v5 assumptions onto existing v2 mechanics.

