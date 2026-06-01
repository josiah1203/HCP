from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_upload_permission
from app.dependencies import get_db
from app.models.schemas import (
    ComponentIdentityCreate,
    ComponentIdentityListResponse,
    ComponentIdentityOut,
    SceneGraphEdgeUpsert,
    SceneGraphEdgeUpsertRequest,
    SceneGraphEdgeUpsertResponse,
    SceneGraphNodeUpsert,
    SceneGraphNodeUpsertRequest,
    SceneGraphNodeUpsertResponse,
    SceneGraphSnapshotCreateRequest,
    SceneGraphSnapshotOut,
    SceneGraphSnapshotResponse,
)
from app.services.scene_graph import SceneGraphService

router = APIRouter(prefix="/v1/scene", tags=["scene"])


@router.post(
    "/component-identities",
    response_model=ComponentIdentityOut,
    status_code=status.HTTP_201_CREATED,
)
def create_component_identity(
    payload: ComponentIdentityCreate,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        row = svc.create_component_identity(
            user=user,
            project_id=payload.project_id,
            canonical_key=payload.canonical_key,
            source_tool=payload.source_tool,
            source_ref=payload.source_ref,
            metadata=payload.metadata,
        )
        db.commit()
        return row
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404,
                detail={"code": code, "message": "Project not found"},
            )
        if code == "forbidden":
            raise HTTPException(
                status_code=403, detail={"code": code, "message": "Forbidden"}
            )
        raise


@router.get(
    "/component-identities/{identity_id}",
    response_model=ComponentIdentityOut,
)
def get_component_identity(
    identity_id: uuid.UUID,
    project_id: uuid.UUID = Query(...),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        return svc.get_component_identity(
            user=user, project_id=project_id, identity_id=identity_id
        )
    except ValueError as e:
        code = str(e)
        if code in ("project_not_found", "component_identity_not_found"):
            raise HTTPException(
                status_code=404, detail={"code": code, "message": "Not found"}
            )
        raise


@router.get(
    "/component-identities",
    response_model=ComponentIdentityListResponse,
)
def list_component_identities(
    project_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        rows = svc.list_component_identities(
            user=user, project_id=project_id, limit=limit, offset=offset
        )
        return {"data": rows}
    except ValueError as e:
        code = str(e)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404, detail={"code": code, "message": "Project not found"}
            )
        raise


@router.put(
    "/nodes",
    response_model=SceneGraphNodeUpsertResponse,
)
def upsert_nodes(
    payload: SceneGraphNodeUpsertRequest,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        items: list[dict[str, Any]] = [i.model_dump() for i in payload.nodes]
        rows = svc.upsert_nodes(user=user, project_id=payload.project_id, nodes=items)
        db.commit()
        return {"data": rows}
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404, detail={"code": code, "message": "Project not found"}
            )
        if code == "forbidden":
            raise HTTPException(
                status_code=403, detail={"code": code, "message": "Forbidden"}
            )
        raise


@router.put(
    "/edges",
    response_model=SceneGraphEdgeUpsertResponse,
)
def upsert_edges(
    payload: SceneGraphEdgeUpsertRequest,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        items: list[dict[str, Any]] = [i.model_dump() for i in payload.edges]
        rows = svc.upsert_edges(user=user, project_id=payload.project_id, edges=items)
        db.commit()
        return {"data": rows}
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404, detail={"code": code, "message": "Project not found"}
            )
        if code == "forbidden":
            raise HTTPException(
                status_code=403, detail={"code": code, "message": "Forbidden"}
            )
        raise


@router.post(
    "/snapshots",
    response_model=SceneGraphSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_snapshot(
    payload: SceneGraphSnapshotCreateRequest,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> Any:
    svc = SceneGraphService(db)
    try:
        row, created = svc.create_snapshot(
            user=user,
            project_id=payload.project_id,
            commit_id=payload.commit_id,
            snapshot_format=payload.snapshot_format,
        )
        db.commit()
        return {"snapshot": row, "deduped": not created}
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found", "commit_not_found"):
            raise HTTPException(
                status_code=404, detail={"code": code, "message": "Not found"}
            )
        if code == "forbidden":
            raise HTTPException(
                status_code=403, detail={"code": code, "message": "Forbidden"}
            )
        raise

