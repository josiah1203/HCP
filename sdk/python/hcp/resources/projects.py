from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class ProjectsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def create(self, name: str, description: str | None = None) -> dict[str, Any]:
        return self._http.post_json("/v1/projects", json={"name": name, "description": description})

    def list(self) -> list[dict[str, Any]]:
        payload = self._http.get_json("/v1/projects")
        return list(payload.get("data", []))

    def get(self, project_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/projects/{project_id}")

    def tree(self, project_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/projects/{project_id}/tree")
