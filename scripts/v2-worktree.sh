#!/usr/bin/env bash
# Manage git worktrees for parallel V2 subagents (one branch/build per workstream).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VALID_IDS=(api parser graph pal infra frontend)

if ! git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: $ROOT is not a git repository (git init required for worktrees)" >&2
  exit 1
fi

usage() {
  cat <<'EOF'
Usage:
  scripts/v2-worktree.sh create <workstream>   # api|parser|graph|pal|infra|frontend
  scripts/v2-worktree.sh list
  scripts/v2-worktree.sh remove <workstream>

Creates ../HCP_working-v2-<workstream> linked worktree on branch feat/hcp-v2-<workstream>-worktree.
EOF
}

valid_id() {
  local id="$1"
  for v in "${VALID_IDS[@]}"; do
    [[ "$v" == "$id" ]] && return 0
  done
  return 1
}

cmd="${1:-}"
id="${2:-}"

case "$cmd" in
  create)
    if [[ -z "$id" ]] || ! valid_id "$id"; then
      echo "error: workstream must be one of: ${VALID_IDS[*]}" >&2
      exit 1
    fi
    dest="$(dirname "$ROOT")/HCP_working-v2-${id}"
    branch="feat/hcp-v2-${id}-worktree"
    if [[ -d "$dest" ]]; then
      echo "worktree already exists: $dest"
      exit 0
    fi
    cd "$ROOT"
    if git rev-parse --verify "$branch" >/dev/null 2>&1; then
      git worktree add "$dest" "$branch"
    else
      git worktree add -b "$branch" "$dest" HEAD
    fi
    echo "Created $dest on branch $branch"
    echo "Verify: cd $dest && make v2-verify-${id}"
    ;;
  list)
    cd "$ROOT"
    git worktree list
    ;;
  remove)
    if [[ -z "$id" ]] || ! valid_id "$id"; then
      echo "error: workstream must be one of: ${VALID_IDS[*]}" >&2
      exit 1
    fi
    dest="$(dirname "$ROOT")/HCP_working-v2-${id}"
    cd "$ROOT"
    if [[ -d "$dest" ]]; then
      git worktree remove "$dest" --force 2>/dev/null || git worktree remove "$dest"
      echo "Removed worktree $dest"
    else
      echo "No worktree at $dest"
    fi
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "error: unknown command $cmd" >&2
    usage
    exit 1
    ;;
esac
