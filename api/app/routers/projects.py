from __future__ import annotations
import uuid

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user, require_admin
from app.auth.rbac import can_upload
from app.dependencies import get_db
from app.models.db import HardwareObject, Project, Version
from app.models.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    if not can_upload(user.role):
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": "Editor role required"},
        )

    existing = db.scalar(
        select(Project).where(Project.org_id == user.org_id, Project.name == body.name)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"code": "conflict", "message": "Project name exists"},
        )

    project = Project(
        org_id=user.org_id,
        name=body.name,
        description=body.description,
        created_by=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=dict)
def list_projects(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    projects = db.scalars(
        select(Project)
        .where(Project.org_id == user.org_id, Project.archived_at.is_(None))
        .order_by(Project.name)
    ).all()
    return {"data": [ProjectOut.model_validate(p) for p in projects]}


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.org_id == user.org_id)
    )
    if project is None or project.archived_at is not None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Project not found"},
        )
    return project


@router.get("/{project_id}/tree")
def project_tree(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == user.org_id,
            Project.archived_at.is_(None),
        )
    )
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Project not found"},
        )

    objects = db.scalars(
        select(HardwareObject).where(
            HardwareObject.project_id == project_id,
            HardwareObject.org_id == user.org_id,
            HardwareObject.deleted_at.is_(None),
        )
    ).all()

    tree = []
    for obj in objects:
        versions = db.scalars(
            select(Version)
            .where(Version.object_id == obj.id)
            .order_by(Version.version_num.desc())
        ).all()
        tree.append(
            {
                "object_id": str(obj.id),
                "name": obj.name,
                "object_type": obj.object_type,
                "versions": [
                    {
                        "version_num": v.version_num,
                        "lifecycle_state": v.lifecycle_state,
                        "parse_status": v.parse_status,
                    }
                    for v in versions
                ],
            }
        )

    return {"project_id": str(project_id), "objects": tree}


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    if not can_upload(user.role):
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": "Editor role required"},
        )

    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == user.org_id,
            Project.archived_at.is_(None),
        )
    )
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Project not found"},
        )

    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id,
            Project.org_id == user.org_id,
            Project.archived_at.is_(None),
        )
    )
    if project is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Project not found"},
        )
    project.archived_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
