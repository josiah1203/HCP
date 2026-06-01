# Legal (Phase 0.5 placeholder)

Hardware Cloud Platform public beta requires published Terms of Service and Privacy Policy. This monorepo does **not** host final legal text; it links to the canonical documents maintained for the product.

## Canonical documents (to be published)

| Document | Status | Location |
|----------|--------|----------|
| Terms of Service | Placeholder — publish before beta-open | External repo or `https://hcp.dev/legal/terms` (TBD) |
| Privacy Policy | Placeholder — publish before beta-open | External repo or `https://hcp.dev/legal/privacy` (TBD) |
| Data Processing Addendum (enterprise) | Post–Phase 0.5 | Sales / enterprise only |

## Engineering references

- Audit and data handling: HCP Engineering Plan §1.4 (audit log on every write; `org_id` scoping).
- Secrets: never in git; PAL `SecretsProvider` only.

## README links

When ToS and Privacy are live, add to the root `README.md`:

```markdown
- [Terms of Service](https://hcp.dev/legal/terms)
- [Privacy Policy](https://hcp.dev/legal/privacy)
```

Until then, beta participants should receive legal links out-of-band from the program owner.
