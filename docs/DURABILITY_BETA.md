# Data durability (Phase 0.5 beta)

v7.1 Phase 0.5 readiness requires cloud HOS with replication, backup, and durability guarantees **confirmed** before external beta. This document records what exists in-repo vs operational verification.

## In repository today

| Layer | Location | Notes |
|-------|----------|--------|
| Postgres schema + migrations | `api/migrations/` | HOS commits, branches, merges, HNF snapshots, scene graph |
| Object storage (PAL) | `infra/pal/` | S3-compatible providers; content-addressed blobs |
| Neo4j graph | `graph/schema/` | PartGraph; optional on kind profile |
| Helm platform stack | `infra/helm/hcp-platform/` | Bitnami Postgres/Redis/MinIO, migrate job, API/parser |
| Logical Postgres backup | `infra/helm/hcp-platform/templates/backup-cronjob.yaml` | `pg_dump` to PVC on schedule |
| Restore drill | `infra/kind/restore-drill.sh` | Backup → `hcp-restore` namespace → pytest subset |
| Audit log | `api/app/services/audit.py` | Immutable audit entries on sensitive operations |

## kind / local beta targets (drill evidence)

| Metric | Phase 0.5 local target | Mechanism |
|--------|------------------------|-----------|
| **RPO** | ≤ 6 hours | CronJob `0 */6 * * *` (`values.yaml`); hourly in `values-kind.yaml` |
| **RTO** | ≤ 30 minutes | `restore-drill.sh`: logical restore + port-forward + API pytest subset |
| **Retention** | 7 days | `find /backups ... -mtime +7` in backup job |
| **Persistence** | Enabled | Bitnami `postgresql.primary.persistence` + backup PVC |

### Run restore drill

```bash
./infra/kind/create-cluster.sh
./infra/kind/install-hcp.sh
./infra/kind/restore-drill.sh
```

Success criteria:

1. `pg_dump` from source namespace produces non-empty gzip SQL.
2. Restore namespace has `alembic_version` row(s).
3. Optional: API pytest subset against restored DB (commands printed by script).

Record last drill date and operator in your ops log when run outside CI.

## v7.1 production targets (not fully verified in this repo)

- **99.99% durability SLO** for committed HOS data
- Replication and point-in-time recovery on staging/production Terraform modules
- Cross-region object store replication
- Data loss incident response runbook exercised on staging

## Recommended verification (ops)

1. Enable Postgres replication / backups per environment Terraform module (`infra/providers/`).
2. Quarterly restore into isolated staging; run full API pytest battery.
3. Document status-page incident process outside this monorepo.

## Related

- Local K8s: [`K8S_LOCAL.md`](./K8S_LOCAL.md)
- Engineering plan: `docs/HCP_Engineering_Plan.md` (durability / DR sections)
- Phase 0.5: [`PHASE_0.5.md`](./PHASE_0.5.md)
