from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.dependencies import get_db
from app.models.schemas import (
    HosBranchCreate,
    HosBranchOut,
    HosCommitCreate,
    HosCommitOut,
    HosConflictListResponse,
    HosConflictOut,
    HosConflictResolveRequest,
    HosDiffRequest,
    HosDiffResponse,
    HosLogResponse,
    HosMergeOut,
    HosMergeRequest,
)
from app.services.hos_version_control import HosVersionControlService

router = APIRouter(prefix="/v1/hos", tags=["hos"])


def _err(code: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": code})


@router.post("/branches", response_model=HosBranchOut, status_code=201)
def create_branch(
    body: HosBranchCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        branch = svc.create_branch(
            user=user,
            project_id=body.project_id,
            name=body.name,
            from_commit_id=body.from_commit_id,
        )
        db.commit()
        return branch
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found",):
            raise _err(code, 404)
        if code in ("commit_not_found",):
            raise _err(code, 404)
        if code in ("forbidden",):
            raise _err(code, 403)
        raise _err("branch_create_failed", 400)


@router.get("/branches", response_model=dict)
def list_branches(
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        branches = svc.list_branches(user=user, project_id=project_id)
        return {"data": [HosBranchOut.model_validate(b).model_dump() for b in branches]}
    except ValueError as e:
        code = str(e)
        if code in ("project_not_found",):
            raise _err(code, 404)
        raise _err("branches_list_failed", 400)


@router.post("/commits", response_model=HosCommitOut, status_code=201)
def create_commit(
    body: HosCommitCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        commit = svc.commit(
            user=user,
            project_id=body.project_id,
            branch_id=body.branch_id,
            message=body.message,
            tree=body.tree,
            parent_commit_ids=body.parent_commit_ids,
        )
        db.commit()
        return HosCommitOut(
            id=commit.id,
            org_id=commit.org_id,
            project_id=commit.project_id,
            branch_id=commit.branch_id,
            message=commit.message,
            tree=commit.tree,
            created_by=commit.created_by,
            created_at=commit.created_at,
            parent_commit_ids=[],
        )
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found", "branch_not_found", "commit_not_found"):
            raise _err(code, 404)
        if code in ("parent_commit_not_found",):
            raise _err(code, 422)
        if code in ("forbidden",):
            raise _err(code, 403)
        raise _err("commit_create_failed", 400)


@router.get("/log", response_model=HosLogResponse)
def log(
    project_id: uuid.UUID = Query(...),
    branch_id: uuid.UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        commits = svc.log(user=user, project_id=project_id, branch_id=branch_id, limit=limit)
        data: list[HosCommitOut] = []
        for c in commits:
            data.append(
                HosCommitOut(
                    id=c.id,
                    org_id=c.org_id,
                    project_id=c.project_id,
                    branch_id=c.branch_id,
                    message=c.message,
                    tree=c.tree,
                    created_by=c.created_by,
                    created_at=c.created_at,
                    parent_commit_ids=[],
                )
            )
        return HosLogResponse(data=data)
    except ValueError as e:
        code = str(e)
        if code in ("project_not_found", "branch_not_found"):
            raise _err(code, 404)
        raise _err("log_failed", 400)


@router.post("/diff", response_model=HosDiffResponse)
def diff(
    body: HosDiffRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        entries = svc.diff(
            user=user,
            project_id=body.project_id,
            from_commit_id=body.from_commit_id,
            to_commit_id=body.to_commit_id,
        )
        return {"data": entries}
    except ValueError as e:
        code = str(e)
        if code in ("project_not_found", "commit_not_found"):
            raise _err(code, 404)
        raise _err("diff_failed", 400)


@router.post("/merge", response_model=HosMergeOut, status_code=201)
def merge(
    body: HosMergeRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        merge_row, result_commit, conflict_count = svc.merge(
            user=user,
            project_id=body.project_id,
            target_branch_id=body.target_branch_id,
            source_branch_id=body.source_branch_id,
        )
        db.commit()
        return HosMergeOut(
            merge_id=merge_row.id,
            status=merge_row.status,
            result_commit_id=result_commit.id if result_commit else None,
            conflict_count=conflict_count,
        )
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found", "branch_not_found"):
            raise _err(code, 404)
        if code in ("forbidden",):
            raise _err(code, 403)
        raise _err("merge_failed", 400)


@router.get("/merges/{merge_id}/conflicts", response_model=HosConflictListResponse)
def list_conflicts(
    merge_id: uuid.UUID,
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        rows = svc.list_conflicts(user=user, project_id=project_id, merge_id=merge_id)
        data = [HosConflictOut.model_validate(r).model_dump() for r in rows]
        return HosConflictListResponse(data=data)
    except ValueError as e:
        code = str(e)
        if code in ("project_not_found", "merge_not_found"):
            raise _err(code, 404)
        raise _err("conflicts_list_failed", 400)


@router.post("/conflicts/{conflict_id}/resolve", response_model=HosConflictOut)
def resolve_conflict(
    conflict_id: uuid.UUID,
    body: HosConflictResolveRequest,
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = HosVersionControlService(db)
    try:
        row = svc.resolve_conflict(
            user=user,
            project_id=project_id,
            conflict_id=conflict_id,
            resolution=body.resolution,
        )
        db.commit()
        return HosConflictOut.model_validate(row)
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found", "conflict_not_found"):
            raise _err(code, 404)
        if code in ("forbidden",):
            raise _err(code, 403)
        raise _err("conflict_resolve_failed", 400)

