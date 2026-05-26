// V2 derived-artifact graph support (ADR-003, HCP Phase C)
//
// Relationship types (no uniqueness constraints — edges are optional):
//   (child:Version)-[:DERIVED_FROM]->(parent:Version)
//     Child has representation=derived; both nodes share org_id.
//     Created idempotently on parse_complete (see graph/tasks.py).
//   (a:HardwareObject)-[:REPRESENTS]->(b:HardwareObject)
//     Cross-domain association from bundle manifest or POST /v1/graph/link.
//
// Property indexes support org-scoped lineage and search facets on representation.

CREATE INDEX version_representation IF NOT EXISTS FOR (v:Version) ON (v.representation);
CREATE INDEX version_domain IF NOT EXISTS FOR (v:Version) ON (v.domain);
CREATE INDEX version_source_tool IF NOT EXISTS FOR (v:Version) ON (v.source_tool);
