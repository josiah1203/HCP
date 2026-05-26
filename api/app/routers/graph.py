from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_graph_query,
    require_upload_permission,
)
from app.dependencies import get_db
from app.models.schemas import GraphLinkCreate, GraphQueryRequest
from app.services.graph import GraphService
from app.services.objects import ObjectService

router = APIRouter(prefix="/v1/graph", tags=["graph"])


@router.get("/{object_id}/dependencies")
def dependencies(
    object_id: uuid.UUID,
    depth: int = Query(3, ge=1, le=10),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_object(db, object_id, user.org_id)
    return GraphService(db).dependencies(user.org_id, object_id, depth)


@router.get("/{object_id}/dependents")
def dependents(
    object_id: uuid.UUID,
    depth: int = Query(3, ge=1, le=10),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_object(db, object_id, user.org_id)
    return GraphService(db).dependents(user.org_id, object_id, depth)


@router.get("/{object_id}/lineage")
def lineage(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_object(db, object_id, user.org_id)
    return GraphService(db).lineage(user.org_id, object_id)


@router.post("/link", status_code=status.HTTP_201_CREATED)
def create_link(
    body: GraphLinkCreate,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_object(db, body.from_object_id, user.org_id)
    _ensure_object(db, body.to_object_id, user.org_id)
    service = GraphService(db)
    try:
        return service.create_link(
            org_id=user.org_id,
            from_object_id=body.from_object_id,
            to_object_id=body.to_object_id,
            relationship_type=body.relationship_type,
            metadata=body.metadata,
        )
    except ValueError as exc:
        if str(exc) == "invalid_relationship_type":
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_error", "message": str(exc)},
            ) from exc
        raise


@router.delete("/link/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(
    relationship_id: str,
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> Response:
    if not GraphService(db).delete_link(user.org_id, relationship_id):
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Relationship not found"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/query")
def graph_query(
    body: GraphQueryRequest,
    user: CurrentUser = Depends(require_graph_query),
    db: Session = Depends(get_db),
) -> dict:
    service = GraphService(db)
    try:
        return service.run_read_query(user.org_id, body.cypher, body.params)
    except ValueError as exc:
        if str(exc) == "write_operations_forbidden":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "Only read-only Cypher queries are allowed",
                },
            ) from exc
        raise


def _ensure_object(db: Session, object_id: uuid.UUID, org_id: uuid.UUID) -> None:
    if ObjectService(db).get_object(object_id, org_id) is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )
