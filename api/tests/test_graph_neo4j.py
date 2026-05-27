"""Neo4j graph client query contracts (org-scoped, depth limits)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.services.graph import Neo4jGraphClient, _MAX_DEPTH


class _FakeSession:
    def __init__(self) -> None:
        self.last_query: str | None = None
        self.last_params: dict | None = None

    def run(self, query: str, params: dict | None = None):
        self.last_query = query
        self.last_params = params
        return [
            {
                "labels": ["Part"],
                "id": "LM358",
                "name": "LM358",
                "depth": 1,
                "rel_type": "USES",
            }
        ]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_get_dependencies_includes_org_filter_and_depth() -> None:
    client = Neo4jGraphClient.__new__(Neo4jGraphClient)
    session = _FakeSession()
    client.session = lambda: session  # type: ignore[method-assign]

    org_id = str(uuid.uuid4())
    object_id = str(uuid.uuid4())
    depth = _MAX_DEPTH + 5
    rows = client.get_dependencies(org_id, object_id, depth)

    assert rows
    assert session.last_params is not None
    assert session.last_params["org_id"] == org_id
    assert session.last_query is not None
    assert "org_id = $org_id" in session.last_query
    assert f"*1..{_MAX_DEPTH}" in session.last_query


def test_query_readonly_rejects_writes() -> None:
    client = Neo4jGraphClient.__new__(Neo4jGraphClient)
    try:
        client.query_readonly("org", "CREATE (n:Node) RETURN n", {})
    except ValueError as exc:
        assert str(exc) == "write_operations_forbidden"
    else:
        raise AssertionError("expected write_operations_forbidden")
