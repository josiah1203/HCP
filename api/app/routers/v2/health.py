from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v2", tags=["v2"])


@router.get("/health")
def v2_health() -> dict[str, str]:
    """V2 API liveness stub; full readiness probes remain on /health/ready."""
    return {"status": "ok", "api_version": "2"}
