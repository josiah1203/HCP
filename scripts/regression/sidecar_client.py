"""JSON-RPC stdio client for HCP IDE sidecars."""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RpcExchange:
    direction: str
    payload: dict[str, Any]


@dataclass
class SidecarSession:
    """Drive a sidecar process over newline-delimited JSON-RPC on stdio."""

    binary: Path
    exchanges: list[RpcExchange] = field(default_factory=list)
    scene_traces: list[dict[str, Any]] = field(default_factory=list)

    _proc: subprocess.Popen[str] | None = field(default=None, repr=False)
    _next_id: int = field(default=0, repr=False)
    _stderr_lines: list[str] = field(default_factory=list, repr=False)

    def start(self) -> None:
        if self._proc is not None:
            return
        self._proc = subprocess.Popen(
            [str(self.binary)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self._proc.stderr is not None
        threading.Thread(target=self._drain_stderr, daemon=True).start()

    def _drain_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        for line in self._proc.stderr:
            stripped = line.rstrip("\n")
            self._stderr_lines.append(stripped)
            if stripped.startswith("HCP_TRACE:"):
                raw = stripped[len("HCP_TRACE:") :]
                self.scene_traces.append(json.loads(raw))

    def close(self) -> None:
        if self._proc is None:
            return
        if self._proc.stdin:
            self._proc.stdin.close()
        self._proc.wait(timeout=30)
        self._proc = None

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._proc is None or self._proc.stdin is None or self._proc.stdout is None:
            raise RuntimeError("sidecar session is not started")
        self._next_id += 1
        request_id = self._next_id
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        line = json.dumps(request, sort_keys=True, separators=(",", ":"))
        self.exchanges.append(RpcExchange(direction="request", payload=request))
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

        while True:
            response_line = self._proc.stdout.readline()
            if not response_line:
                raise RuntimeError(f"sidecar closed stdout before responding to {method}")
            response_line = response_line.strip()
            if not response_line:
                continue
            response = json.loads(response_line)
            self.exchanges.append(RpcExchange(direction="response", payload=response))
            if response.get("id") != request_id:
                continue
            if "error" in response and response["error"] is not None:
                raise RuntimeError(
                    f"JSON-RPC error for {method}: {response['error']}"
                )
            result = response.get("result")
            if result is None:
                raise RuntimeError(f"missing result for {method}")
            return result

    def ping(self) -> dict[str, Any]:
        return self.call("hcp/ping")

    def project_open(
        self,
        *,
        project_id: str,
        workspace_root: str,
        api_url: str = "https://api.hcp.local",
        token: str = "regression-token",
    ) -> dict[str, Any]:
        return self.call(
            "hcp/project/open",
            {
                "projectId": project_id,
                "workspaceRoot": workspace_root,
                "auth": {"apiUrl": api_url, "token": token},
            },
        )

    def apply_mutations(
        self, *, document_uri: str, mutations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self.call(
            "hcp/document/applyMutations",
            {"documentUri": document_uri, "mutations": mutations},
        )
