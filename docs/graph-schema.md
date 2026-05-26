# HCP PartGraph — Neo4j Schema

Canonical reference for the Hardware Cloud Platform graph layer (HCP §10). All schema changes are versioned Cypher scripts under `graph/schema/` — no ad-hoc DDL. V2 adds derived-artifact edges per [ADR-003](ADR/ADR-003-parser-abstraction-layer.md).

## Node labels

| Label | Key properties | Org-scoped | Description |
|-------|----------------|------------|-------------|
| `Org` | `org_id`, `name` | — | Tenant root |
| `Project` | `project_id`, `org_id`, `name` | Yes | Project container |
| `HardwareObject` | `object_id`, `org_id`, `name`, `type` | Yes | Logical artifact identity |
| `Version` | `version_id`, `object_id`, `org_id`, `version_num`, `state` | Yes | Immutable version snapshot |
| `Part` | `mpn`, `manufacturer`, `lifecycle` | No | Canonical part (shared across orgs) |
| `Supplier` | `name`, `country` | No | Supplier identity |
| `Firmware` | `version_id`, `object_id`, `org_id`, `format`, `target_arch` | Yes | Firmware artifact |
| `Requirement` | `req_id`, `org_id`, `identifier`, `title` | Yes | Product requirement |

## Relationship types

| From | Type | To | Created by |
|------|------|-----|------------|
| `Project` | `CONTAINS` | `HardwareObject` | Object creation / auto-linker |
| `HardwareObject` | `HAS_VERSION` | `Version` | Upload / auto-linker |
| `Version` | `SUPERSEDES` | `Version` | New upload / auto-linker |
| `Version` | `USES` | `Part` | Parser / auto-linker (BOM, PCB) |
| `Part` | `SOURCED_FROM` | `Supplier` | Octopart enrichment |
| `Firmware` | `TARGETS` | `HardwareObject` | Manual `POST /v1/graph/link` |
| `Version` | `VALIDATES` | `Requirement` | Manual |
| `Version` | `CONTAINS` | `HardwareObject` | Manual |
| `HardwareObject` | `SATISFIES` | `Requirement` | Manual |
| `Version` | `DERIVED_FROM` | `Version` | Upload (`representation=derived`) / bundle manifest |
| `HardwareObject` | `REPRESENTS` | `HardwareObject` | Manual / bundle manifest |

## Derived artifacts (V2 / ADR-003)

PrAL converters and bundle manifests produce **derived** versions that must link back to a parent version without coupling graph code to vendor SDKs. Only canonical upload fields (`representation`, `derived_from_version_id`, `source_assets`) drive edges.

### `DERIVED_FROM` (version lineage)

| Property | Rule |
|----------|------|
| Direction | `(child:Version)-[:DERIVED_FROM]->(parent:Version)` |
| Trigger | Child `representation = derived` and `derived_from_version_id` set at upload |
| Tenancy | `child.org_id = parent.org_id`; service layer must filter both ends with `$org_id` |
| Idempotency | `MERGE` on `parse_complete` in `graph.tasks.auto_link_version` |
| vs `SUPERSEDES` | `SUPERSEDES` is same-object version history; `DERIVED_FROM` is cross-version provenance (e.g. STEP exported from SolidWorks native) |
| Search / lineage | OpenSearch `representation` facet; `GET /v1/graph/{object_id}/lineage` walks derived children |

Postgres `versions.derived_from_version_id` is the source of truth; the graph edge is materialized after parse.

### `REPRESENTS` (cross-object association)

| Property | Rule |
|----------|------|
| Direction | `(a:HardwareObject)-[:REPRESENTS]->(b:HardwareObject)` |
| Trigger | Bundle manifest `relationships[]` or `POST /v1/graph/link` |
| Tenancy | Both objects must share `org_id` |
| Use | Link electrical ↔ mechanical (or other domain) identities without merging objects |

Migration `graph/schema/004_derived_from.cypher` adds `Version` indexes on `representation`, `domain`, and `source_tool` for org-scoped derived lookups. Relationship types have no Neo4j uniqueness constraints (edges are optional).

## Migrations

Apply in order after Neo4j is running:

```bash
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/001_initial_constraints.cypher
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/002_indexes.cypher
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/003_node_constraints.cypher
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/004_derived_from.cypher
```

## Multi-tenancy

Every service-layer Cypher query filters org-scoped nodes with `org_id = $org_id`. `Part` and `Supplier` are global; traversal into them always starts from an org-scoped `Version` or `HardwareObject`.

## Auto-linker (§10.3)

Triggered on `parse_complete` (Celery task `graph.tasks.auto_link_version`). Idempotent via `MERGE`:

1. Merge `Part` nodes for each unique `(mpn, manufacturer)` in `ParsedOutput`
2. `MERGE (Version)-[:USES]->(Part)`
3. `MERGE (HardwareObject)-[:HAS_VERSION]->(Version)`
4. `MERGE (new Version)-[:SUPERSEDES]->(previous Version)` when `version_num > 1`
5. When `representation=derived` and parent version id present: `MERGE (child)-[:DERIVED_FROM]->(parent)` (same `org_id`)
6. Enqueue Octopart enrichment (7-day Postgres cache on `parts`)
7. Index document in OpenSearch `hcp-versions` index

`REPRESENTS` and bundle-driven `DERIVED_FROM` are not in the core linker yet; see `graph/linker.py` (V2 stub).

## OpenSearch index

Index `hcp-versions` documents include: `org_id`, `object_id`, `version_id`, `name`, `object_type`, `domain`, `source_tool`, `representation`, `lifecycle_state`, `project_id`, `mpn` (array), `filename`, `version_num`, `parsed_at`.

Facets: `object_type`, `domain`, `source_tool`, `representation`, `lifecycle_state`, `project_id`.

## API surface

Implemented in `api/app/services/graph.py` and `api/app/routers/graph.py`:

- `GET /v1/graph/{object_id}/dependencies?depth=3` (max 10)
- `GET /v1/graph/{object_id}/dependents`
- `GET /v1/graph/{object_id}/lineage`
- `POST /v1/graph/link` — manual relationships
- `DELETE /v1/graph/link/{relationship_id}`
- `POST /v1/graph/query` — read-only Cypher (admin)

Search: `GET /v1/search` via `api/app/services/search.py`.
