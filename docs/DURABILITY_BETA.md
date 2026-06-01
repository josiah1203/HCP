# Data durability (Phase 0.5 beta)

v7.1 Phase 0.5 readiness requires cloud HOS with replication, backup, and durability guarantees **confirmed** before external beta. This document records what exists in-repo vs what remains operational verification.

## In repository today

| Layer | Location | Notes |
|-------|----------|--------|
| Postgres schema + migrations | `api/migrations/` | HOS commits, branches, merges, HNF snapshots, scene graph |
| Object storage (PAL) | `infra/pal/` | S3-compatible providers; content-addressed blobs |
| Neo4j graph | `graph/schema/` | PartGraph; backup story in infra plan |
| Helm / Terraform scaffolding | `infra/helm/`, `infra/providers/` | Deploy templates; not a substitute for DR drill |
| Audit log | `api/app/services/audit.py` | Immutable audit entries on sensitive operations |

## v7.1 targets (not fully verified in this repo)

- **99.99% durability SLO** for committed HOS data
- Replication and point-in-time recovery tested on staging/production
- **Data loss incident response runbook** exercised (see engineering plan § disaster recovery)

## Recommended verification (ops)

1. Enable Postgres replication / backups per environment Terraform module.
2. Run restore drill: restore DB + object store snapshot into isolated env; run API pytest battery against restored data.
3. Document RPO/RTO and status-page incident process outside this monorepo.

## Related

- Engineering plan: durability and disaster recovery sections in `HCP_Engineering_Plan_v7.1.md`
- Phase 0.5 scope: [`PHASE_0.5.md`](./PHASE_0.5.md)
