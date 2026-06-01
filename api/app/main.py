from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.middleware.errors import http_exception_handler
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.routers import (
    auth,
    bom,
    collaboration,
    events,
    graph,
    health,
    hos_version_control,
    objects,
    orgs,
    parts,
    projects,
    scene,
    search,
)
from app.routers.v2 import health_router as v2_health

app = FastAPI(
    title="Hardware Cloud Platform",
    description="HCP V1 — Hardware Object Store API (§8 contract)",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "JWT and API key authentication"},
        {"name": "orgs", "description": "Organization registration and invites"},
        {"name": "projects", "description": "Project management"},
        {"name": "objects", "description": "Hardware object storage and lifecycle"},
        {"name": "bom", "description": "Bill of materials"},
        {"name": "parts", "description": "Canonical parts catalog"},
        {"name": "graph", "description": "PartGraph relationships"},
        {"name": "search", "description": "Full-text and faceted search"},
        {"name": "health", "description": "Health and readiness probes"},
        {"name": "hos", "description": "HOS version control (branches/commits/merge)"},
        {"name": "events", "description": "Event stream (poll/publish)"},
        {
            "name": "collaboration",
            "description": "Presence (polling), advisory soft locks, cross-domain alerts",
        },
        {"name": "scene", "description": "Component identity and scene graph"},
        {"name": "v2", "description": "HCP V2 API (breaking changes; stub endpoints)"},
    ],
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(HTTPException, http_exception_handler)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(orgs.router)
app.include_router(projects.router)
app.include_router(objects.router)
app.include_router(bom.router)
app.include_router(parts.router)
app.include_router(graph.router)
app.include_router(search.router)
app.include_router(hos_version_control.router)
app.include_router(events.router)
app.include_router(collaboration.router)
app.include_router(scene.router)
app.include_router(v2_health)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": str(exc.errors()),
                "request_id": request_id,
            }
        },
    )
