from __future__ import annotations

import time
from typing import Any

import httpx

from hcp.exceptions import HCPError, ParseTimeoutError, raise_for_status


class HttpClient:
    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        access_token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        token = access_token or api_key
        if not token:
            raise HCPError("api_key or access_token required")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = httpx.Client(
            base_url=self.api_url,
            headers=self._headers,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, Any] | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                )
                if response.status_code == 429 and attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
                raise_for_status(response)
                return response
            except HCPError:
                raise
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(2**attempt)
                    continue
        raise HCPError(str(last_exc) if last_exc else "Request failed")

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params).json()

    def post_json(self, path: str, *, json: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json=json).json()

    def poll_parse(
        self,
        object_id: str,
        version_num: int,
        *,
        timeout: float,
        interval: float = 2.0,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            version = self.get_json(f"/v1/objects/{object_id}/versions/{version_num}")
            status = version.get("parse_status", "pending")
            if status in ("complete", "failed"):
                return version
            time.sleep(interval)
        raise ParseTimeoutError(
            f"Parse did not complete within {timeout}s",
            code="parse_timeout",
        )
