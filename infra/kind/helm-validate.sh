#!/usr/bin/env bash
# Lint and render hcp-platform without a live cluster (CI / pre-commit).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHART="${REPO_ROOT}/infra/helm/hcp-platform"
VALUES="${CHART}/values-kind.yaml"
HELM="${HELM:-helm}"
if ! command -v "${HELM}" >/dev/null 2>&1; then
  if [[ -x "${REPO_ROOT}/.tools/helm" ]]; then
    HELM="${REPO_ROOT}/.tools/helm"
  else
    echo "helm 3 is required (or place binary at .tools/helm)" >&2
    exit 1
  fi
fi

cd "${CHART}"
"${HELM}" dependency update
"${HELM}" lint -f values.yaml -f "${VALUES}"
"${HELM}" template hcp-local . -f values.yaml -f "${VALUES}" --namespace hcp > /dev/null
echo "helm lint + template OK (${CHART})"
