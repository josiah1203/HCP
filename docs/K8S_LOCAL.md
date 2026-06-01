# Local Kubernetes (kind) for HCP

Run HCP on a local [kind](https://kind.sigs.k8s.io/) cluster with the `hcp-platform` umbrella chart: Bitnami PostgreSQL, Redis, MinIO, Alembic migrate job, API, and optional parser worker.

## Prerequisites

| Tool | Notes |
|------|--------|
| Docker | kind node images, image builds |
| kind | `brew install kind` |
| kubectl | Cluster access |
| helm 3 | `helm dependency update` for Bitnami charts |

## Quick start

```bash
chmod +x infra/kind/*.sh
./infra/kind/create-cluster.sh
./infra/kind/install-hcp.sh
kubectl -n hcp get pods -w
```

kind maps host port **8000** to NodePort **30080** (see `infra/kind/kind-config.yaml`).

## Validate charts (no cluster)

```bash
./infra/kind/helm-validate.sh
```

Or manually:

```bash
helm dependency update infra/helm/hcp-platform
helm lint infra/helm/hcp-platform -f infra/helm/hcp-platform/values.yaml -f infra/helm/hcp-platform/values-kind.yaml
helm template hcp infra/helm/hcp-platform -n hcp \
  -f infra/helm/hcp-platform/values.yaml \
  -f infra/helm/hcp-platform/values-kind.yaml
```

## Smoke checks

```bash
curl -sf http://127.0.0.1:8000/health
kubectl -n hcp logs job/hcp-migrate
```

Port-forward alternative:

```bash
kubectl -n hcp port-forward svc/hcp-hcp-api 8000:8000
curl -sf http://127.0.0.1:8000/health
```

## Migrations

Helm runs `alembic upgrade head` on install/upgrade (`hcp-migrate` job). Manual re-run:

```bash
helm upgrade hcp infra/helm/hcp-platform -n hcp \
  -f infra/helm/hcp-platform/values.yaml \
  -f infra/helm/hcp-platform/values-kind.yaml
```

Against port-forwarded Postgres:

```bash
kubectl -n hcp port-forward svc/postgres 5432:5432
export DATABASE_URL=postgresql+psycopg2://hcp:hcp@127.0.0.1:5432/hcp
make migrate
```

## Seed dev data

```bash
export HCP_API_URL=http://127.0.0.1:8000
make seed
```

## Tests against cluster DB

```bash
kubectl -n hcp port-forward svc/postgres 5432:5432
export DATABASE_URL=postgresql+psycopg2://hcp:hcp@127.0.0.1:5432/hcp
cd api && PYTHONPATH=.. pytest tests/test_hos_version_control.py tests/test_events.py -q --maxfail=3
```

## In-cluster DNS

| Service | DNS | Port |
|---------|-----|------|
| Postgres | `postgres.hcp.svc.cluster.local` | 5432 |
| Redis | `redis-master.hcp.svc.cluster.local` | 6379 |
| MinIO | `minio.hcp.svc.cluster.local` | 9000 |
| API | `hcp-hcp-api.hcp.svc.cluster.local` | 8000 |

Credentials: Secret `hcp-credentials` (dev defaults; change for non-local).

## Durability drill

```bash
./infra/kind/restore-drill.sh
```

See [`DURABILITY_BETA.md`](./DURABILITY_BETA.md) for RPO/RTO targets.

## Teardown

```bash
helm uninstall hcp -n hcp
./infra/kind/destroy-cluster.sh
```

## Troubleshooting

| Symptom | Check |
|---------|--------|
| ImagePullBackOff | Re-run `install-hcp.sh` (`kind load docker-image`) |
| Migrate failed | `kubectl -n hcp logs job/hcp-migrate` |
| MinIO bucket missing | `kubectl -n hcp logs job/hcp-minio-init` |
| API not ready | Postgres + migrate job completed first |
