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

    def import_design(
        self,
        project_id: str,
        *,
        format: str,
        file_path: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        from pathlib import Path

        path = Path(file_path)
        with path.open("rb") as fh:
            return self._http.request(
                "POST",
                f"/v1/projects/{project_id}/import",
                data={"format": format, "message": message or ""},
                files={"file": (path.name, fh, "application/octet-stream")},
            ).json()

    def import_archive(
        self,
        project_id: str,
        *,
        format: str,
        file_path: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        from pathlib import Path

        path = Path(file_path)
        with path.open("rb") as handle:
            files = {"file": (path.name, handle)}
            data: dict[str, str] = {"format": format}
            if message:
                data["message"] = message
            return self._http.request(
                "POST",
                f"/v1/projects/{project_id}/import",
                files=files,
                data=data,
            ).json()
