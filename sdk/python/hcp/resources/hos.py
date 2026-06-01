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

    # --- Version control (/v1/hos/*) ---

    def create_branch(
        self,
        *,
        project_id: str,
        name: str,
        from_commit_id: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"project_id": project_id, "name": name}
        if from_commit_id is not None:
            body["from_commit_id"] = from_commit_id
        return self._http.post_json("/v1/hos/branches", json=body)

    def list_branches(self, *, project_id: str) -> dict[str, Any]:
        return self._http.get_json(
            "/v1/hos/branches",
            params={"project_id": project_id},
        )

    def commit(
        self,
        *,
        project_id: str,
        branch_id: str,
        message: str,
        tree: dict[str, Any] | None = None,
        parent_commit_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "project_id": project_id,
            "branch_id": branch_id,
            "message": message,
            "tree": tree or {},
        }
        if parent_commit_ids is not None:
            body["parent_commit_ids"] = parent_commit_ids
        return self._http.post_json("/v1/hos/commits", json=body)

    def log(
        self,
        *,
        project_id: str,
        branch_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        return self._http.get_json(
            "/v1/hos/log",
            params={"project_id": project_id, "branch_id": branch_id, "limit": limit},
        )

    def diff(
        self,
        *,
        project_id: str,
        from_commit_id: str,
        to_commit_id: str,
    ) -> dict[str, Any]:
        return self._http.post_json(
            "/v1/hos/diff",
            json={
                "project_id": project_id,
                "from_commit_id": from_commit_id,
                "to_commit_id": to_commit_id,
            },
        )

    def merge(
        self,
        *,
        project_id: str,
        target_branch_id: str,
        source_branch_id: str,
    ) -> dict[str, Any]:
        return self._http.post_json(
            "/v1/hos/merge",
            json={
                "project_id": project_id,
                "target_branch_id": target_branch_id,
                "source_branch_id": source_branch_id,
            },
        )

    def list_conflicts(self, *, project_id: str, merge_id: str) -> dict[str, Any]:
        return self._http.get_json(
            f"/v1/hos/merges/{merge_id}/conflicts",
            params={"project_id": project_id},
        )

    def resolve_conflict(
        self,
        *,
        project_id: str,
        conflict_id: str,
        resolution: dict[str, Any],
    ) -> dict[str, Any]:
        return self._http.post_json(
            f"/v1/hos/conflicts/{conflict_id}/resolve",
            params={"project_id": project_id},
            json={"resolution": resolution},
        )

