from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hcp._http import HttpClient


class SearchResource:
    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def query(
        self,
        q: str | None = None,
        *,
        type: str | None = None,
        state: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if q:
            params["q"] = q
        if type:
            params["type"] = type
        if state:
            params["state"] = state
        if project_id:
            params["project_id"] = project_id
        return self._http.get_json("/v1/search", params=params)
