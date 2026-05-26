from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class ObjectsResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self, object_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/objects/{object_id}")

    def list_versions(self, object_id: str) -> list[dict[str, Any]]:
        payload = self._http.get_json(f"/v1/objects/{object_id}/versions")
        return list(payload.get("data", []))

    def get_version(self, object_id: str, version_num: int) -> dict[str, Any]:
        return self._http.get_json(f"/v1/objects/{object_id}/versions/{version_num}")

    def get_parsed(self, object_id: str, version_num: int) -> dict[str, Any]:
        return self._http.get_json(f"/v1/objects/{object_id}/versions/{version_num}/parsed")

    def download_url(self, object_id: str, version_num: int) -> str:
        payload = self._http.get_json(
            f"/v1/objects/{object_id}/versions/{version_num}/download"
        )
        return str(payload["url"])

    def promote(
        self,
        object_id: str,
        version_num: int,
        target_state: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"target_state": target_state}
        if comment:
            body["comment"] = comment
        return self._http.post_json(
            f"/v1/objects/{object_id}/versions/{version_num}/promote",
            json=body,
        )

    def upload(
        self,
        file_path: str,
        project_id: str,
        name: str,
        *,
        description: str | None = None,
        object_id: str | None = None,
        wait_for_parse: bool = False,
        parse_timeout: float = 120.0,
    ) -> dict[str, Any]:
        path = Path(file_path)
        if not path.is_file():
            raise ValueError(f"File not found: {file_path}")

        data: dict[str, str] = {
            "project_id": project_id,
            "name": name,
        }
        if description:
            data["description"] = description
        if object_id:
            data["object_id"] = object_id

        with path.open("rb") as fh:
            response = self._http.request(
                "POST",
                "/v1/objects/upload",
                data=data,
                files={"file": (path.name, fh)},
            )
        result: dict[str, Any] = response.json()

        if wait_for_parse:
            version = result["version"]
            oid = str(result["object"]["id"])
            vnum = int(version["version_num"])
            result["version"] = self._http.poll_parse(oid, vnum, timeout=parse_timeout)

        return result
