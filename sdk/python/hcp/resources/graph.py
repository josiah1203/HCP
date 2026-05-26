from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class GraphResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def dependencies(self, object_id: str, depth: int = 3) -> dict[str, Any]:
        return self._http.get_json(
            f"/v1/graph/{object_id}/dependencies",
            params={"depth": depth},
        )

    def dependents(self, object_id: str, depth: int = 3) -> dict[str, Any]:
        return self._http.get_json(
            f"/v1/graph/{object_id}/dependents",
            params={"depth": depth},
        )

    def lineage(self, object_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/graph/{object_id}/lineage")

    def link(
        self,
        from_object_id: str,
        relationship_type: str,
        to_object_id: str,
    ) -> dict[str, Any]:
        return self._http.post_json(
            "/v1/graph/link",
            json={
                "from_object_id": from_object_id,
                "relationship_type": relationship_type,
                "to_object_id": to_object_id,
            },
        )
