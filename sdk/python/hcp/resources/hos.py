from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class HosResource:
    """
    Minimal HOS client surface intended for fork shims.

    This is intentionally small and transport-agnostic at the call-site; today it maps to
    HTTP endpoints. The method shapes mirror `docs/protocol/jsonrpc/hcp-hos-client.v0.json`.
    """

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    # --- Commit trees ---

    def read_commit_tree(self, tree_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/hos/trees/{tree_id}")

    def write_commit_tree(self, tree_id: str, *, entries: list[dict[str, Any]]) -> dict[str, Any]:
        return self._http.post_json(
            f"/v1/hos/trees/{tree_id}",
            json={"tree_id": tree_id, "entries": entries},
        )

    # --- Artifact blob upload ---

    def upload_artifact_blob(
        self,
        *,
        file_path: str,
        project_id: str,
        name: str,
        description: str | None = None,
        object_id: str | None = None,
        wait_for_parse: bool = False,
        parse_timeout: float = 120.0,
    ) -> dict[str, Any]:
        # Reuse existing objects upload surface for now.
        # NOTE: forks should treat the returned (object.id, version.version_num) as the blob reference.
        from hcp.resources.objects import ObjectsResource

        return ObjectsResource(self._http).upload(
            file_path,
            project_id=project_id,
            name=name,
            description=description,
            object_id=object_id,
            wait_for_parse=wait_for_parse,
            parse_timeout=parse_timeout,
        )

    # --- Scene graph writes + snapshot ---

    def upsert_scene_graph(
        self,
        *,
        commit_id: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._http.post_json(
            "/v1/scene/upsert",
            json={"commit_id": commit_id, "nodes": nodes, "edges": edges},
        )

    def create_snapshot(self, *, commit_id: str, snapshot_type: str = "sceneGraph") -> dict[str, Any]:
        return self._http.post_json(
            "/v1/snapshots",
            json={"commit_id": commit_id, "snapshot_type": snapshot_type},
        )

    # --- Events ---

    def poll_events(self, *, cursor: str, limit: int = 100) -> dict[str, Any]:
        return self._http.get_json(
            "/v1/events",
            params={"cursor": cursor, "limit": limit},
        )

