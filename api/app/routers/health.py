from __future__ import annotations
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.dependencies import SessionLocal
from app.models.schemas import HealthCheck
from infra.pal.factory import get_queue_provider, get_storage_provider

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/health/live")
def health_live() -> dict:
    return {"status": "ok"}


@router.get("/health/ready", response_model=HealthCheck)
def health_ready() -> HealthCheck:
    checks: dict[str, str] = {}

    try:
        storage = get_storage_provider()
        checks["storage"] = "ok" if storage.ping() else "fail"  # type: ignore[attr-defined]
    except Exception:
        checks["storage"] = "fail"

    try:
        queue = get_queue_provider()
        checks["queue"] = "ok" if queue.ping() else "fail"
    except Exception:
        checks["queue"] = "fail"

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "fail"

    try:
        from app.services.graph import get_graph_service

        neo4j = get_graph_service()
        checks["neo4j"] = (
            "ok" if neo4j and neo4j.ping() else ("skipped" if neo4j is None else "fail")
        )
    except Exception:
        checks["neo4j"] = "fail"

    try:
        from app.services.search import get_search_service

        checks["opensearch"] = "ok" if get_search_service().ping() else "fail"
    except Exception:
        checks["opensearch"] = "fail"
    checks["provider"] = settings.hcp_provider

    critical = ("db", "storage", "neo4j", "opensearch")
    status = "ok"
    if any(checks.get(k) == "fail" for k in critical):
        status = "fail"
    elif any(v not in ("ok", "skipped") for v in checks.values()):
        status = "degraded"

    return HealthCheck(status=status, checks=checks)
