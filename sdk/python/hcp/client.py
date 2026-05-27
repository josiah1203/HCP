from __future__ import annotations

from hcp._http import HttpClient
from hcp.resources.bom import BomResource
from hcp.resources.graph import GraphResource
from hcp.resources.hos import HosResource
from hcp.resources.objects import ObjectsResource
from hcp.resources.projects import ProjectsResource
from hcp.resources.search import SearchResource


class Client:
    """HCP Python SDK client."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str = "https://api.hcp.io",
        access_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._http = HttpClient(
            api_url=api_url,
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.projects = ProjectsResource(self._http)
        self.objects = ObjectsResource(self._http)
        self.bom = BomResource(self._http)
        self.graph = GraphResource(self._http)
        self.search = SearchResource(self._http)
        self.hos = HosResource(self._http)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
