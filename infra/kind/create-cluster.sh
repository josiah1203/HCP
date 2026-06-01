#!/usr/bin/env bash
# Create local kind cluster for HCP (see docs/K8S_LOCAL.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLUSTER_NAME="${HCP_KIND_CLUSTER:-hcp-local}"
CONFIG="${SCRIPT_DIR}/kind-config.yaml"

command -v kind >/dev/null 2>&1 || {
  echo "kind is required: https://kind.sigs.k8s.io/docs/user/quick-start/#installation" >&2
  exit 1
}
command -v kubectl >/dev/null 2>&1 || {
  echo "kubectl is required" >&2
  exit 2
}

if kind get clusters 2>/dev/null | grep -qx "${CLUSTER_NAME}"; then
  echo "kind cluster '${CLUSTER_NAME}' already exists; skipping create"
else
  kind create cluster --name "${CLUSTER_NAME}" --config "${CONFIG}"
fi

kubectl cluster-info --context "kind-${CLUSTER_NAME}"
echo "Context: kind-${CLUSTER_NAME}"
