# PartGraph (Neo4j)

Cypher migration scripts live in `schema/`. Apply in order after Neo4j is running.

```bash
export NEO4J_PASSWORD=hcpsecret
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/001_initial_constraints.cypher
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/002_indexes.cypher
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" -f graph/schema/003_node_constraints.cypher
```

- Schema reference: `docs/graph-schema.md`
- API services: `api/app/services/graph.py`, `api/app/services/search.py`
- Auto-linker Celery task: `graph/tasks.py` (`graph.tasks.auto_link_version`)
