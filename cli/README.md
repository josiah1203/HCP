# `hw` — HCP hardware CLI (Phase 0.5 beta)

Minimal command-line client for HOS version control. Maps to `/v1/hos/*` APIs via the Python SDK.

## Setup

```bash
pip install -e sdk/python
pip install -e cli
```

## Authentication

Use an API key or bearer token from the environment:

```bash
export HCP_API_URL=https://api.hcp.local
export HCP_API_KEY=hcp_your_key
# or
export HCP_ACCESS_TOKEN=eyJ...
```

Or log in interactively:

```bash
hw auth login --email you@example.com --password '***' --api-url https://api.hcp.local
```

## Examples

```bash
hw branch create --project-id <uuid> --name feature --json
hw branch list --project-id <uuid> --json
hw commit create --project-id <uuid> --branch-id <uuid> --message "init" --json
hw diff --project-id <uuid> --from <commit> --to <commit> --json
hw merge --project-id <uuid> --target <branch> --source <branch> --json
hw conflicts list --merge-id <uuid> --project-id <uuid> --json
hw conflicts resolve --conflict-id <uuid> --project-id <uuid> --resolution '{"take":"ours"}' --json
```

## Regression (sidecars)

```bash
source $HOME/.cargo/env
cargo build -p kicad-sidecar -p freecad-sidecar --manifest-path rust/Cargo.toml
python3 scripts/regression/run_suite.py mutation-hook \
  --seed scripts/regression/fixtures/minimal_seed.json \
  --mutations 4
```
