"""Neo4j PartGraph service with org-scoped queries (HCP §10)."""

from __future__ import annotations

import re
import uuid
from functools import lru_cache
from typing import Any

from neo4j import GraphDatabase, Session
from neo4j.exceptions import Neo4jError
from sqlalchemy.orm import Session as OrmSession

from app.config import settings
from graph.linker import LinkContext, run_auto_link

_MAX_DEPTH = 10
_DEFAULT_DEPTH = 3
READ_ONLY_DENY = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH|CALL\s+\{)\b",
    re.IGNORECASE,
)
_WRITE_CYPHER = READ_ONLY_DENY
VALID_REL_TYPES = frozenset(
    {
        "USES",
        "CONTAINS",
        "TARGETS",
        "VALIDATES",
        "SATISFIES",
        "SOURCED_FROM",
        "DERIVED_FROM",
        "REPRESENTS",
    }
)
OBJECT_REL_TYPES = frozenset(
    {
        "USES",
        "CONTAINS",
        "TARGETS",
        "VALIDATES",
        "SATISFIES",
        "SOURCED_FROM",
        "REPRESENTS",
    }
)


class Neo4jGraphClient:
    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def ping(self) -> bool:
        try:
            self._driver.verify_connectivity()
            with self.session() as session:
                session.run("RETURN 1")
            return True
        except Neo4jError:
            return False

    def session(self) -> Session:
        return self._driver.session()

    def auto_link(self, ctx: LinkContext, parsed: dict[str, Any]) -> int:
        with self.session() as session:
            return run_auto_link(session, ctx, parsed)

    def get_dependencies(
        self, org_id: str, object_id: str, depth: int = _DEFAULT_DEPTH
    ) -> list[dict[str, Any]]:
        depth = min(max(depth, 1), _MAX_DEPTH)
        query = f"""
        MATCH (h:HardwareObject {{object_id: $object_id, org_id: $org_id}})
        MATCH (h)-[:HAS_VERSION]->(v:Version)
        MATCH path = (v)-[:USES|CONTAINS*1..{depth}]->(target)
        WHERE target:Part OR (target:HardwareObject AND target.org_id = $org_id)
        RETURN DISTINCT
            labels(target) AS labels,
            coalesce(target.object_id, target.mpn) AS id,
            coalesce(target.name, target.mpn) AS name,
            length(path) AS depth,
            type(last(relationships(path))) AS rel_type
        ORDER BY depth, name
        LIMIT 500
        """
        return self._run_list(query, {"org_id": org_id, "object_id": object_id})

    def get_dependents(
        self, org_id: str, object_id: str, depth: int = _DEFAULT_DEPTH
    ) -> list[dict[str, Any]]:
        depth = min(max(depth, 1), _MAX_DEPTH)
        query = f"""
        MATCH (h:HardwareObject {{object_id: $object_id, org_id: $org_id}})
        MATCH (h)-[:HAS_VERSION]->(v:Version)
        MATCH path = (source)-[:USES|CONTAINS|TARGETS*1..{depth}]->(v)
        WHERE (source:Version AND source.org_id = $org_id)
           OR (source:HardwareObject AND source.org_id = $org_id)
           OR (source:Firmware AND source.org_id = $org_id)
        RETURN DISTINCT
            labels(source) AS labels,
            coalesce(source.object_id, source.version_id) AS id,
            coalesce(source.name, source.version_id) AS name,
            length(path) AS depth,
            type(last(relationships(path))) AS rel_type
        ORDER BY depth, name
        LIMIT 500
        """
        return self._run_list(query, {"org_id": org_id, "object_id": object_id})

    def get_lineage(self, org_id: str, object_id: str) -> list[dict[str, Any]]:
        query = """
        MATCH (h:HardwareObject {object_id: $object_id, org_id: $org_id})
        MATCH (h)-[:HAS_VERSION]->(v:Version)
        WHERE v.org_id = $org_id
        OPTIONAL MATCH (v)-[:SUPERSEDES*]->(older:Version)
        WHERE older IS NULL OR older.org_id = $org_id
        WITH collect(DISTINCT v) + collect(DISTINCT older) AS vers
        UNWIND vers AS ver
        WITH ver WHERE ver IS NOT NULL
        RETURN DISTINCT
            ver.version_id AS version_id,
            ver.version_num AS version_num,
            ver.state AS state
        ORDER BY ver.version_num DESC
        """
        return self._run_list(query, {"org_id": org_id, "object_id": object_id})

    def create_derived_from(
        self, org_id: str, from_version_id: str, to_version_id: str
    ) -> str:
        query = """
        MATCH (child:Version {version_id: $from_id, org_id: $org_id})
        MATCH (parent:Version {version_id: $to_id, org_id: $org_id})
        MERGE (child)-[r:DERIVED_FROM]->(parent)
        RETURN elementId(r) AS rel_id
        """
        with self.session() as session:
            record = session.run(
                query,
                {
                    "org_id": org_id,
                    "from_id": from_version_id,
                    "to_id": to_version_id,
                },
            ).single()
        if record is None:
            raise ValueError("link_failed")
        return str(record["rel_id"])

    def create_represents(
        self,
        org_id: str,
        from_object_id: str,
        to_object_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        return self.create_object_link(
            org_id, from_object_id, to_object_id, "REPRESENTS", metadata
        )

    def create_object_link(
        self,
        org_id: str,
        from_object_id: str,
        to_object_id: str,
        rel_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        query = f"""
        MATCH (a:HardwareObject {{object_id: $from_id, org_id: $org_id}})
        MATCH (b:HardwareObject {{object_id: $to_id, org_id: $org_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props
        RETURN elementId(r) AS rel_id
        """
        with self.session() as session:
            record = session.run(
                query,
                {
                    "org_id": org_id,
                    "from_id": from_object_id,
                    "to_id": to_object_id,
                    "props": metadata or {},
                },
            ).single()
        if record is None:
            raise ValueError("link_failed")
        return str(record["rel_id"])

    def delete_relationship(self, org_id: str, relationship_id: str) -> bool:
        query = """
        MATCH ()-[r]->()
        WHERE elementId(r) = $rel_id
        AND startNode(r).org_id = $org_id
        DELETE r
        RETURN count(r) AS deleted
        """
        with self.session() as session:
            record = session.run(
                query, {"org_id": org_id, "rel_id": relationship_id}
            ).single()
        return bool(record and record["deleted"])

    def query_readonly(
        self, org_id: str, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if READ_ONLY_DENY.search(cypher):
            raise ValueError("write_operations_forbidden")
        if "$org_id" not in cypher and "org_id" not in (params or {}):
            raise ValueError("org_id_filter_required")
        merged = {"org_id": org_id, **(params or {})}
        return self._run_list(cypher, merged)

    def _run_list(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with self.session() as session:
            result = session.run(query, params)
            return [dict(record) for record in result]


_client: Neo4jGraphClient | None = None


@lru_cache
def get_graph_service() -> Neo4jGraphClient | None:
    global _client
    if not settings.neo4j_uri:
        return None
    if _client is None:
        _client = Neo4jGraphClient(
            settings.neo4j_uri,
            settings.neo4j_user,
            settings.neo4j_password,
        )
    return _client


class GraphService:
    """Facade used by routers — Neo4j for graph traversal, in-memory for dev fallback links."""

    _links: dict[str, dict[str, dict[str, Any]]] = {}

    def __init__(self, db: OrmSession) -> None:
        self.db = db
        self._neo4j = get_graph_service()

    def _org_links(self, org_id: str) -> dict[str, dict[str, Any]]:
        return self._links.setdefault(org_id, {})

    def _neo4j_available(self) -> bool:
        if self._neo4j is None:
            return False
        try:
            return self._neo4j.ping()
        except Exception:
            return False

    def query_readonly(
        self, org_id: str, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        if self._neo4j is None:
            raise ValueError("org_id_filter_required")
        return self._neo4j.query_readonly(org_id, cypher, params)

    def create_manual_link(
        self,
        org_id: str,
        *,
        rel_type: str,
        from_id: str,
        from_label: str,
        to_id: str,
        to_label: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        self._sanitize_label(from_label)
        self._sanitize_label(to_label)
        if rel_type not in OBJECT_REL_TYPES:
            raise ValueError("invalid_relationship_type")
        if from_label == "HardwareObject" and to_label == "Part" and rel_type != "USES":
            raise ValueError("invalid_relationship_type")
        if self._neo4j_available():
            return self._neo4j.create_object_link(
                org_id, from_id, to_id, rel_type, metadata
            )
        rel_id = str(uuid.uuid4())
        self._org_links(org_id)[rel_id] = {
            "relationship_id": rel_id,
            "org_id": org_id,
            "from_object_id": from_id,
            "to_object_id": to_id,
            "relationship_type": rel_type,
            "metadata": metadata or {},
        }
        return rel_id

    def dependencies(
        self, org_id: uuid.UUID, object_id: uuid.UUID, depth: int = 3
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        if self._neo4j_available():
            try:
                nodes = self._neo4j.get_dependencies(str(org_id), str(object_id), depth)
            except Neo4jError:
                pass
        edges = self._edges_for(org_id, object_id, "out")
        return {
            "object_id": str(object_id),
            "depth": depth,
            "nodes": nodes,
            "edges": edges,
        }

    def dependents(
        self, org_id: uuid.UUID, object_id: uuid.UUID, depth: int = 3
    ) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        if self._neo4j_available():
            try:
                nodes = self._neo4j.get_dependents(str(org_id), str(object_id), depth)
            except Neo4jError:
                pass
        return {
            "object_id": str(object_id),
            "depth": depth,
            "nodes": nodes,
            "edges": self._edges_for(org_id, object_id, "in"),
        }

    def lineage(self, org_id: uuid.UUID, object_id: uuid.UUID) -> dict[str, Any]:
        versions: list[dict[str, Any]] = []
        if self._neo4j_available():
            try:
                versions = self._neo4j.get_lineage(str(org_id), str(object_id))
            except Neo4jError:
                pass
        return {
            "object_id": str(object_id),
            "versions": versions,
            "relationships": self._edges_for(org_id, object_id, "both"),
        }

    def create_derived_from_link(
        self,
        org_id: uuid.UUID,
        *,
        from_version_id: uuid.UUID,
        to_version_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rel_id: str
        if self._neo4j_available():
            try:
                rel_id = self._neo4j.create_derived_from(
                    str(org_id), str(from_version_id), str(to_version_id)
                )
                return {
                    "relationship_id": rel_id,
                    "org_id": str(org_id),
                    "from_version_id": str(from_version_id),
                    "to_version_id": str(to_version_id),
                    "relationship_type": "DERIVED_FROM",
                    "metadata": metadata or {},
                }
            except Neo4jError:
                pass

        rel_id = str(uuid.uuid4())
        link = {
            "relationship_id": rel_id,
            "org_id": str(org_id),
            "from_version_id": str(from_version_id),
            "to_version_id": str(to_version_id),
            "relationship_type": "DERIVED_FROM",
            "metadata": metadata or {},
        }
        self._org_links(str(org_id))[rel_id] = link
        return link

    def create_link(
        self,
        *,
        org_id: uuid.UUID,
        from_object_id: uuid.UUID,
        to_object_id: uuid.UUID,
        relationship_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if relationship_type not in OBJECT_REL_TYPES:
            raise ValueError("invalid_relationship_type")

        rel_id: str
        if self._neo4j_available():
            try:
                rel_id = self._neo4j.create_object_link(
                    str(org_id),
                    str(from_object_id),
                    str(to_object_id),
                    relationship_type,
                    metadata,
                )
                return {
                    "relationship_id": rel_id,
                    "org_id": str(org_id),
                    "from_object_id": str(from_object_id),
                    "to_object_id": str(to_object_id),
                    "relationship_type": relationship_type,
                    "metadata": metadata or {},
                }
            except Neo4jError:
                pass

        rel_id = str(uuid.uuid4())
        link = {
            "relationship_id": rel_id,
            "org_id": str(org_id),
            "from_object_id": str(from_object_id),
            "to_object_id": str(to_object_id),
            "relationship_type": relationship_type,
            "metadata": metadata or {},
        }
        self._org_links(str(org_id))[rel_id] = link
        return link

    def delete_link(self, org_id: uuid.UUID, relationship_id: str) -> bool:
        if self._neo4j_available():
            try:
                if self._neo4j.delete_relationship(str(org_id), relationship_id):
                    return True
            except Neo4jError:
                pass
        links = self._org_links(str(org_id))
        if relationship_id in links:
            del links[relationship_id]
            return True
        return False

    def run_read_query(
        self, org_id: uuid.UUID, cypher: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if READ_ONLY_DENY.search(cypher):
            raise ValueError("write_operations_forbidden")
        records: list[dict[str, Any]] = []
        if self._neo4j_available():
            try:
                records = self._neo4j.query_readonly(str(org_id), cypher, params)
            except ValueError:
                raise
            except Neo4jError:
                pass
        return {
            "org_id": str(org_id),
            "records": records,
            "summary": {
                "query": cypher.strip(),
                "mode": "read",
                "params": params or {},
            },
        }

    def _edges_for(
        self, org_id: uuid.UUID, object_id: uuid.UUID, direction: str
    ) -> list[dict[str, Any]]:
        oid = str(object_id)
        org_key = str(org_id)
        edges = []
        for link in self._org_links(org_key).values():
            if direction in ("out", "both") and link["from_object_id"] == oid:
                edges.append(link)
            elif direction in ("in", "both") and link["to_object_id"] == oid:
                edges.append(link)
        return edges

    @staticmethod
    def _sanitize_label(label: str) -> str:
        allowed = {
            "HardwareObject",
            "Version",
            "Part",
            "Requirement",
            "Firmware",
            "Supplier",
            "Project",
        }
        if label not in allowed:
            raise ValueError("invalid_label")
        return label
