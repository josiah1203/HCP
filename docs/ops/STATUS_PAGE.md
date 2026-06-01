# Status page (Phase 0.5)

Public beta requires a customer-visible status page for API and core dependencies. HCP does not embed a status UI in this monorepo.

## Recommended providers

| Provider | Use case |
|----------|----------|
| [Better Stack](https://betterstack.com/status) (Better Uptime) | Uptime checks + branded status page |
| [Instatus](https://instatus.com) | Incident communication + components |
| [Statuspage (Atlassian)](https://www.atlassian.com/software/statuspage) | Enterprise-style components |

## Minimum components for Phase 0.5

1. **HCP API** — `GET /health` on production and staging
2. **Postgres (HOS)** — dependency for all write paths
3. **Object storage (PAL / MinIO or cloud)** — uploads and artifact reads
4. **Redis** — Celery broker (parse pipeline)
5. **Optional:** Neo4j / OpenSearch when enabled in the deployment profile

## Incident process (stub)

1. Detect via synthetic check or on-call alert
2. Post *Investigating* on the status page
3. Link to `docs/DURABILITY_BETA.md` runbooks for restore drills (internal)
4. Resolve and post *Resolved* with short root-cause summary

## Link from README

After the page is created:

```markdown
**Status:** https://status.hcp.dev (example)
```

Update [PUBLIC_ROADMAP.md](../PUBLIC_ROADMAP.md) when the URL is live.
