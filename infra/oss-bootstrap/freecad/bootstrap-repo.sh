#!/usr/bin/env bash
# Bootstrap hcp-oss/freecad from upstream (run OUTSIDE the HCP monorepo).
set -euo pipefail

HCP_OSS_ORG="${HCP_OSS_ORG:-hcp-oss}"
REPO_NAME="freecad"
UPSTREAM_URL="https://github.com/FreeCAD/FreeCAD.git"
UPSTREAM_BRANCH="${UPSTREAM_BRANCH:-main}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$(cd "${SCRIPT_DIR}/../templates" && pwd)"
WORK_DIR="${WORK_DIR:-$(mktemp -d)}"

echo "==> Bootstrap ${HCP_OSS_ORG}/${REPO_NAME} in ${WORK_DIR}"

if [[ ! -d "${WORK_DIR}/${REPO_NAME}/.git" ]]; then
  git clone --depth 1 --branch "${UPSTREAM_BRANCH}" "${UPSTREAM_URL}" "${WORK_DIR}/${REPO_NAME}"
fi

cd "${WORK_DIR}/${REPO_NAME}"
git remote rename origin upstream 2>/dev/null || true
git remote add origin "git@github.com:${HCP_OSS_ORG}/${REPO_NAME}.git" 2>/dev/null || \
  git remote set-url origin "git@github.com:${HCP_OSS_ORG}/${REPO_NAME}.git"

render_template() {
  local src="$1" dest="$2"
  sed \
    -e "s|{{TOOL_NAME}}|FreeCAD 1.x|g" \
    -e "s|{{REPO_NAME}}|${REPO_NAME}|g" \
    -e "s|{{UPSTREAM_URL}}|${UPSTREAM_URL}|g" \
    -e "s|{{UPSTREAM_LICENSE}}|LGPL-2.1+|g" \
    -e "s|{{UPSTREAM_DEFAULT_BRANCH}}|${UPSTREAM_BRANCH}|g" \
    -e "s|{{UPSTREAM_GIT_URL}}|${UPSTREAM_URL}|g" \
    -e "s|{{STEWARD_TEAM}}|hcp-oss-stewards|g" \
    -e "s|{{PRIMARY_CLI}}|freecadcmd|g" \
    -e "s|{{VERSION_PIN}}|1.0.x|g" \
    -e "s|{{ADAPTER_SUFFIX}}|freecad|g" \
    -e "s|{{EXPORT_FORMATS}}|STEP, BREP, FCStd|g" \
    "${src}" > "${dest}"
}

render_template "${TEMPLATE_DIR}/FORK_NOTES.md" FORK_NOTES.md
render_template "${TEMPLATE_DIR}/HCP_INTEGRATION.md" HCP_INTEGRATION.md
render_template "${TEMPLATE_DIR}/UPSTREAM_SYNC.md" UPSTREAM_SYNC.md

mkdir -p .github/workflows
cp "${SCRIPT_DIR}/.github/workflows/upstream-sync.yml" .github/workflows/upstream-sync.yml

git add FORK_NOTES.md HCP_INTEGRATION.md UPSTREAM_SYNC.md .github/workflows/upstream-sync.yml
git commit -m "docs(hcp): steward templates and upstream-sync workflow" || true

git branch -M upstream/main "${UPSTREAM_BRANCH}" 2>/dev/null || git checkout -b upstream/main
git checkout -b hcp/integration 2>/dev/null || git checkout hcp/integration

echo ""
echo "Next steps:"
echo "  1. Create empty GitHub repo: https://github.com/orgs/${HCP_OSS_ORG}/repositories/new → ${REPO_NAME}"
echo "  2. git push -u origin upstream/main"
echo "  3. git push -u origin hcp/integration"
echo "  4. Enable GitHub Actions on the repo for weekly upstream-sync PRs"
echo ""
echo "Local tree: ${WORK_DIR}/${REPO_NAME}"
