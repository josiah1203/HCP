#!/usr/bin/env bash
# Durability beta: logical backup from cluster Postgres -> restore in hcp-restore namespace.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLUSTER_NAME="${HCP_KIND_CLUSTER:-hcp-local}"
SOURCE_NS="${HCP_NAMESPACE:-hcp}"
RESTORE_NS="${HCP_RESTORE_NAMESPACE:-hcp-restore}"
CTX="kind-${CLUSTER_NAME}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$(mktemp -t hcp-pg-XXXXXX.sql.gz)"

kubectl config use-context "${CTX}"

PG_POD="$(kubectl -n "${SOURCE_NS}" get pods -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')"
[[ -n "${PG_POD}" ]] || { echo "Postgres pod not found in ${SOURCE_NS}" >&2; exit 1; }

echo "==> Backup from ${SOURCE_NS}/${PG_POD}"
kubectl -n "${SOURCE_NS}" exec "${PG_POD}" -- bash -c \
  'PGPASSWORD="${POSTGRES_PASSWORD:-hcp}" pg_dump -U hcp -d hcp --no-owner --no-acl' | gzip -c > "${BACKUP_FILE}"
SIZE="$(wc -c < "${BACKUP_FILE}" | tr -d ' ')"
echo "Wrote ${BACKUP_FILE} (${SIZE} bytes)"
[[ "${SIZE}" -gt 100 ]] || { echo "Backup too small" >&2; exit 2; }

kubectl create namespace "${RESTORE_NS}" --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${RESTORE_NS}" delete pod hcp-restore-pg --ignore-not-found
kubectl -n "${RESTORE_NS}" run hcp-restore-pg \
  --image=postgres:15-alpine \
  --env="POSTGRES_USER=hcp" \
  --env="POSTGRES_PASSWORD=hcp" \
  --env="POSTGRES_DB=hcp" \
  --restart=Never \
  --command -- sleep infinity
kubectl -n "${RESTORE_NS}" wait --for=condition=Ready pod/hcp-restore-pg --timeout=120s

kubectl -n "${RESTORE_NS}" exec hcp-restore-pg -- psql -U hcp -d postgres -c "DROP DATABASE IF EXISTS hcp;"
kubectl -n "${RESTORE_NS}" exec hcp-restore-pg -- psql -U hcp -d postgres -c "CREATE DATABASE hcp;"
kubectl -n "${RESTORE_NS}" cp "${BACKUP_FILE}" "hcp-restore-pg:/tmp/restore.sql.gz"
kubectl -n "${RESTORE_NS}" exec hcp-restore-pg -- sh -c 'gunzip -c /tmp/restore.sql.gz | psql -U hcp -d hcp'

ROW_COUNT="$(kubectl -n "${RESTORE_NS}" exec hcp-restore-pg -- \
  psql -U hcp -d hcp -tAc "SELECT COUNT(*) FROM alembic_version;" 2>/dev/null || echo 0)"
echo "alembic_version rows: ${ROW_COUNT}"
[[ "${ROW_COUNT}" -ge 1 ]] || { echo "Restore drill FAILED: missing alembic_version" >&2; exit 3; }

rm -f "${BACKUP_FILE}"

echo "==> Restore drill OK (${TIMESTAMP})"
echo "Optional API verify:"
echo "  kubectl -n ${RESTORE_NS} port-forward pod/hcp-restore-pg 5433:5432"
echo "  DATABASE_URL=postgresql+psycopg2://hcp:hcp@127.0.0.1:5433/hcp"
echo "  cd ${ROOT}/api && PYTHONPATH=.. pytest tests/test_hos_version_control.py -q --maxfail=1"
