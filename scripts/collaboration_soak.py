#!/usr/bin/env python3
"""Accelerated collaboration soak test (Phase 0.5 C3).

Hits /v1/collaboration presence heartbeat and soft-lock acquire/release for two
synthetic session IDs. See docs/PHASE_0.5.md for pass criteria.

Example:
  export HCP_API_URL=http://localhost:8000
  export HCP_PROJECT_ID=<project-uuid>
  export HCP_TOKEN=dev-token
  python3 scripts/collaboration_soak.py --iterations 60 --interval-s 1
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid


def _json_request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
) -> tuple[float, dict | None]:
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
        if resp.status >= 500:
            raise RuntimeError(f"server error {resp.status} for {url}")
        parsed = json.loads(raw) if raw else None
    return time.monotonic() - start, parsed


def run_soak(
    *,
    api_url: str,
    project_id: str,
    token: str,
    iterations: int,
    interval_s: float,
    p95_limit_ms: float,
) -> int:
    latencies: list[float] = []
    sessions = ("soak-session-a", "soak-session-b")
    base = api_url.rstrip("/")
    project_uuid = str(uuid.UUID(project_id))

    for i in range(iterations):
        for session_id in sessions:
            heartbeat_url = f"{base}/v1/collaboration/presence/heartbeat"
            lat, _ = _json_request(
                "POST",
                heartbeat_url,
                token,
                {
                    "project_id": project_uuid,
                    "session_id": session_id,
                    "resource_path": "doc/main",
                    "domain": "soak",
                    "client_meta": {"iteration": i},
                },
            )
            latencies.append(lat)

            acquire_url = f"{base}/v1/collaboration/locks/acquire"
            lat, acquire_body = _json_request(
                "POST",
                acquire_url,
                token,
                {
                    "project_id": project_uuid,
                    "resource_path": f"doc/main/{session_id}",
                    "session_id": session_id,
                    "ttl_seconds": 30,
                },
            )
            latencies.append(lat)

            lock_id = (acquire_body or {}).get("lock", {}).get("id")
            if lock_id:
                release_url = (
                    f"{base}/v1/collaboration/locks/{lock_id}"
                    f"?project_id={project_uuid}"
                )
                lat, _ = _json_request("DELETE", release_url, token)
                latencies.append(lat)

        time.sleep(interval_s)

    if len(latencies) < 2:
        print("not enough samples", file=sys.stderr)
        return 1

    p95 = statistics.quantiles(latencies, n=20)[-1] * 1000
    print(f"samples={len(latencies)} p95_ms={p95:.1f} limit_ms={p95_limit_ms}")
    return 0 if p95 <= p95_limit_ms else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Collaboration soak helper")
    parser.add_argument("--iterations", type=int, default=60)
    parser.add_argument("--interval-s", type=float, default=1.0)
    parser.add_argument("--p95-limit-ms", type=float, default=500.0)
    args = parser.parse_args()

    api_url = os.environ.get("HCP_API_URL", "http://localhost:8000")
    project_id = os.environ.get("HCP_PROJECT_ID", "")
    token = os.environ.get("HCP_TOKEN", "dev-token")
    if not project_id:
        print("HCP_PROJECT_ID is required", file=sys.stderr)
        return 2

    try:
        return run_soak(
            api_url=api_url,
            project_id=project_id,
            token=token,
            iterations=args.iterations,
            interval_s=args.interval_s,
            p95_limit_ms=args.p95_limit_ms,
        )
    except urllib.error.URLError as exc:
        print(f"soak failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"invalid project id: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
