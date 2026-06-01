# Fork notes — {{TOOL_NAME}}

| Field | Value |
|-------|-------|
| **Upstream** | {{UPSTREAM_URL}} |
| **Upstream license** | {{UPSTREAM_LICENSE}} |
| **HCP org repo** | `hcp-oss/{{REPO_NAME}}` |
| **Tracking branch** | `upstream/main` → upstream `{{UPSTREAM_DEFAULT_BRANCH}}` |
| **Integration branch** | `hcp/integration` |
| **Steward** | {{STEWARD_TEAM}} |

## Why this fork exists

HCP runs {{TOOL_NAME}} as a **separate host process** (headless/batch). This repo holds only:

1. Minimal patches for headless I/O and IDE chrome removal (incremental).
2. Build/run documentation for sidecar operators.
3. Automated upstream sync into `hcp/integration`.

**No** HCP proprietary code (VC, collaboration, cloud API) belongs in this repository.

## Files HCP owns vs upstream

| Area | Owner | Notes |
|------|-------|-------|
| Application chrome, wizards, marketing UI | Upstream (removed over time on `hcp/integration`) | Strip behind feature flags; see `HCP_INTEGRATION.md` |
| Headless CLI / batch entrypoint | **HCP** | Documented in `HCP_INTEGRATION.md` |
| File format parsers inside tool | Upstream | HCP uses **Apache 2.0 adapters** in `hcp-adapters/*` for HNF mapping |
| CI upstream-sync workflow | **HCP** | `.github/workflows/upstream-sync.yml` |

## Build expectations (Phase 0.5)

- Produce installable binaries on `PATH`: `{{PRIMARY_CLI}}`
- Document version pin: **{{VERSION_PIN}}**
- CI in HCP monorepo defaults to **stub sidecars**; real binaries enabled with `HCP_USE_HOST_OSS=1`

## Contact

Open issues labeled `hcp-steward` for integration questions. Platform bugs that do not require fork changes belong in the private `hcp-platform` / HCP monorepo.
