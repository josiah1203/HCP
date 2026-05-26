from __future__ import annotations
import uuid

from app.services.graph import GraphService, Neo4jGraphClient, READ_ONLY_DENY


def test_write_cypher_detection_blocks_mutations() -> None:
    assert READ_ONLY_DENY.search("CREATE (n:Node)") is not None
    assert READ_ONLY_DENY.search("MATCH (n) RETURN n") is None


def test_neo4j_query_readonly_requires_org_filter() -> None:
    class FakeSession:
        def run(self, *args, **kwargs):
            return []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeClient(Neo4jGraphClient):
        def __init__(self):
            pass

        def session(self):
            return FakeSession()

    client = FakeClient()
    try:
        client.query_readonly("org-1", "MATCH (n) RETURN n", {})
    except ValueError as exc:
        assert str(exc) == "org_id_filter_required"
    else:
        raise AssertionError("expected org_id_filter_required")


def test_manual_relationship_type_validation() -> None:
    g = GraphService(db=None)  # type: ignore[arg-type]
    try:
        g.create_link(
            org_id=uuid.uuid4(),
            from_object_id=uuid.uuid4(),
            to_object_id=uuid.uuid4(),
            relationship_type="NOT_A_REL",
        )
    except ValueError as exc:
        assert str(exc) == "invalid_relationship_type"
    else:
        raise AssertionError("expected invalid_relationship_type")


def test_in_memory_link_roundtrip() -> None:
    org = uuid.uuid4()
    a, b = uuid.uuid4(), uuid.uuid4()
    g = GraphService(db=None)  # type: ignore[arg-type]
    link = g.create_link(
        org_id=org,
        from_object_id=a,
        to_object_id=b,
        relationship_type="CONTAINS",
    )
    assert link["relationship_id"]
    edges = g._edges_for(org, a, "out")
    assert len(edges) == 1
    assert g.delete_link(org, link["relationship_id"]) is True
