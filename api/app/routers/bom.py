from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.dependencies import get_db
from app.services.bom import BOMService

router = APIRouter(prefix="/v1/bom", tags=["bom"])


@router.get("/{object_id}")
def get_bom(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = BOMService(db)
    try:
        return service.get_bom(object_id, user.org_id)
    except ValueError as exc:
        _raise_from_value(exc)


@router.get("/{object_id}/versions/{version_num}")
def get_bom_version(
    object_id: uuid.UUID,
    version_num: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = BOMService(db)
    try:
        return service.get_bom(object_id, user.org_id, version_num)
    except ValueError as exc:
        _raise_from_value(exc)


@router.get("/{object_id}/flat")
def get_bom_flat(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = BOMService(db)
    try:
        return service.flat_bom(object_id, user.org_id)
    except ValueError as exc:
        _raise_from_value(exc)


@router.get("/{object_id}/diff/{version_num_a}/{version_num_b}")
def get_bom_diff(
    object_id: uuid.UUID,
    version_num_a: int,
    version_num_b: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = BOMService(db)
    try:
        return service.diff(object_id, user.org_id, version_num_a, version_num_b)
    except ValueError as exc:
        _raise_from_value(exc)


def _raise_from_value(exc: ValueError) -> None:
    code = str(exc)
    if code == "not_found":
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        ) from exc
    if code == "version_not_found":
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Version not found"},
        ) from exc
    raise HTTPException(
        status_code=404, detail={"code": "not_found", "message": code}
    ) from exc
