#!/usr/bin/env bash
# Pre-commit helper: block obvious secret patterns in staged files.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PATTERNS=(
  'AKIA[0-9A-Z]{16}'
  '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'
  'password\s*=\s*["\x27][^"\x27]{8,}'
  'api[_-]?key\s*=\s*["\x27][^"\x27]{16,}'
  'secret[_-]?key\s*=\s*["\x27][^"\x27]{16,}'
)

EXCLUDES=(
  ':!*.example'
  ':!*.md'
  ':!scripts/check_secrets.sh'
  ':!.env.example'
  ':!docker-compose.yml'
  ':!docker-compose.test.yml'
)

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  FILES=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
  if [[ -z "${FILES}" ]]; then
    exit 0
  fi
  SEARCH_CMD=(git grep -nE -I)
  for ex in "${EXCLUDES[@]}"; do
    SEARCH_CMD+=("$ex")
  done
else
  SEARCH_CMD=(grep -rnE --exclude-dir=.git --exclude='*.md')
fi

FOUND=0
for pattern in "${PATTERNS[@]}"; do
  if [[ -n "${FILES:-}" ]]; then
    while IFS= read -r f; do
      [[ -f "$f" ]] || continue
      if grep -nE "$pattern" "$f" 2>/dev/null | grep -vE 'dev-only|hcpsecret|example|placeholder|test-secret'; then
        echo "check_secrets: possible secret in $f (pattern: $pattern)" >&2
        FOUND=1
      fi
    done <<< "$FILES"
  else
    if grep -rnE "$pattern" api parser infra sdk web actions scripts \
      --exclude-dir=__pycache__ --exclude-dir=node_modules \
      --exclude='*.md' --exclude='.env.example' 2>/dev/null \
      | grep -vE 'dev-only|hcpsecret|example|placeholder|test-secret'; then
      FOUND=1
    fi
  fi
done

if [[ "$FOUND" -ne 0 ]]; then
  echo "check_secrets: failed — remove secrets or use env/SecretsProvider" >&2
  exit 1
fi

exit 0
