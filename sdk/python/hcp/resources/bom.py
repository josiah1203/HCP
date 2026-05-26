from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class BomResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self, object_id: str, version_num: int | None = None) -> dict[str, Any]:
        if version_num is not None:
            return self._http.get_json(f"/v1/bom/{object_id}/versions/{version_num}")
        return self._http.get_json(f"/v1/bom/{object_id}")

    def flat(self, object_id: str) -> dict[str, Any]:
        return self._http.get_json(f"/v1/bom/{object_id}/flat")

    def diff(self, object_id: str, version_a: int, version_b: int) -> dict[str, Any]:
        return self._http.get_json(
            f"/v1/bom/{object_id}/diff/{version_a}/{version_b}"
        )
