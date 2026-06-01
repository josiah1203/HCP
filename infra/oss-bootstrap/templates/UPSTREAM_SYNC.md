# Upstream sync runbook — {{TOOL_NAME}}

## Remotes

```bash
git remote add upstream {{UPSTREAM_GIT_URL}}
git fetch upstream
```

## Branches

| Branch | Purpose |
|--------|---------|
| `upstream/main` | Mirror of upstream `{{UPSTREAM_DEFAULT_BRANCH}}` (fast-forward only from automation) |
| `hcp/integration` | HCP patches; receives weekly merge PRs from `upstream/main` |

## Automated sync (preferred)

GitHub Actions workflow: [`.github/workflows/upstream-sync.yml`](../.github/workflows/upstream-sync.yml)

- Schedule: weekly (Monday 06:00 UTC)
- Opens PR: `upstream/main` → `hcp/integration`
- Label: `upstream-sync`
- Requires steward review before merge

## Manual sync

```bash
git checkout upstream/main
git fetch upstream
git merge --ff-only upstream/{{UPSTREAM_DEFAULT_BRANCH}}

git checkout hcp/integration
git merge upstream/main
# resolve conflicts; run upstream test subset + HCP headless smoke
git push origin hcp/integration
```

## Conflict policy

1. Prefer **upstream behavior** for core tool logic.
2. Prefer **HCP commits** for headless entry, chrome flags, and packaging only.
3. Escalate license/header changes to steward + legal review.

## Post-merge checklist

- [ ] Version string bumped in `FORK_NOTES.md` if needed
- [ ] Headless smoke script green
- [ ] Notify `#hcp-oss-stewards` with PR link
