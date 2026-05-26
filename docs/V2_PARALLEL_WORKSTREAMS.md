# V2 parallel workstreams

HCP V1 is in flight; V2 adds breaking API surface (`/v2/`), PrAL proprietary plugins + converters, and graph edges for derived artifacts. Multiple agents should not share one working tree while running builds.

## Why worktrees

- Avoid merge conflicts when two agents edit different areas simultaneously.
- Each workstream has its own branch and `make v2-verify-<id>` loop.
- Parent coordinator can launch up to six background subagents (see `AGENTS.md`).

## Setup

Requires a git repository at the project root (`git init` or clone).

```bash
./scripts/v2-worktree.sh create parser
cd ../HCP_working-v2-parser
git switch -c feat/hcp-v2-parser-converter-stub
make v2-verify-parser
```

List or remove worktrees:

```bash
./scripts/v2-worktree.sh list
./scripts/v2-worktree.sh remove parser
```

## Parallel verification matrix

| Command | Safe concurrent? | Notes |
|---------|------------------|-------|
| `make v2-verify-api` | Yes | Unit tests; optional Docker build |
| `make v2-verify-parser` | Yes | No compose |
| `make v2-verify-pal` | Yes | PAL unit tests only |
| `make v2-verify-graph` | Yes | Schema/migration checks until Neo4j tests land |
| `make v2-verify-infra` | Yes | `docker build` only |
| `make v2-verify-frontend` | Yes | Lint/typecheck when web deps installed |
| `make v2-verify-parallel` | Yes | Runs api + parser + pal + infra image builds with `-j` |
| `make test-integration` | **No** (same host) | Binds 5433, 6380, 9002 |

## Launching subagents in Cursor

Use the Task tool with `run_in_background: true`, one agent per row in `AGENTS.md`, each prompt including:

1. Worktree path (after `v2-worktree.sh create`)
2. Owned paths only
3. `make v2-verify-<id>` before reporting done

Example coordinator batch (six parallel builds):

- `hcp-backend` + `make v2-verify-api`
- `hcp-parser` + `make v2-verify-parser`
- `hcp-graph` + `make v2-verify-graph`
- `hcp-infra` + `make v2-verify-pal`
- `hcp-infra` + `make v2-verify-infra`
- `hcp-frontend` + `make v2-verify-frontend`

## V2 scope reference

| Area | V2 item | Doc |
|------|---------|-----|
| API | `/v2/` routes, contract breaks | HCP §1.4 #8 |
| Parser | Plugins, `Converter`, sidecars | ADR-003, `docs/parser-plugins.md` |
| Graph | `DERIVED_FROM`, derived versions | ADR-003 consequences |
| Out of V1 | SolidWorks/Altium parsers, PDF OCR | HCP §1.3 |
