#!/usr/bin/env bash
# Build local images, load into kind, install hcp-platform Helm release.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLUSTER_NAME="${HCP_KIND_CLUSTER:-hcp-local}"
RELEASE="${HCP_HELM_RELEASE:-hcp}"
NAMESPACE="${HCP_NAMESPACE:-hcp}"
CHART="${ROOT}/infra/helm/hcp-platform"

HELM="${HELM:-helm}"
if ! command -v "${HELM}" >/dev/null 2>&1; then
  [[ -x "${ROOT}/.tools/helm" ]] && HELM="${ROOT}/.tools/helm" || {
    echo "helm 3 required" >&2
    exit 1
  }
fi

command -v docker >/dev/null 2>&1 || { echo "docker required" >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required" >&2; exit 1; }
command -v kind >/dev/null 2>&1 || { echo "kind required" >&2; exit 1; }

CTX="kind-${CLUSTER_NAME}"
kubectl config use-context "${CTX}"

echo "==> Building API and parser images"
docker build -f "${ROOT}/api/Dockerfile" -t hcp-api:local "${ROOT}"
docker build -f "${ROOT}/parser/Dockerfile" -t hcp-parser:local "${ROOT}"

echo "==> Loading images into kind"
kind load docker-image hcp-api:local --name "${CLUSTER_NAME}"
kind load docker-image hcp-parser:local --name "${CLUSTER_NAME}"

echo "==> Helm dependency update"
"${HELM}" dependency update "${CHART}"

echo "==> Installing ${RELEASE} into ${NAMESPACE}"
"${HELM}" upgrade --install "${RELEASE}" "${CHART}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  -f "${CHART}/values.yaml" \
  -f "${CHART}/values-kind.yaml" \
  --wait \
  --timeout 15m

kubectl -n "${NAMESPACE}" get pods,svc
