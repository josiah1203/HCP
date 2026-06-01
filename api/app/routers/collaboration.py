from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.dependencies import get_db
from app.models.schemas import (
    CrdtOperationRequest,
    CrdtOperationResponse,
    CrossDomainAlertRequest,
    CrossDomainAlertResponse,
    PresenceHeartbeatRequest,
    PresenceHeartbeatResponse,
    PresenceLeaveRequest,
    PresenceLeaveResponse,
    PresenceListResponse,
    PresenceOut,
    SoftLockAcquireRequest,
    SoftLockAcquireResponse,
    SoftLockListResponse,
    SoftLockOut,
)
from app.services.collaboration import CollaborationService

router = APIRouter(prefix="/v1/collaboration", tags=["collaboration"])


def _err(code: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": code})


@router.post(
    "/presence/heartbeat",
    response_model=PresenceHeartbeatResponse,
    status_code=200,
)
def presence_heartbeat(
    body: PresenceHeartbeatRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    """Polling-based presence (beta): clients POST every ~30s; list via GET /presence."""
    svc = CollaborationService(db)
    try:
        row, joined = svc.heartbeat_presence(
            user=user,
            project_id=body.project_id,
            session_id=body.session_id,
            resource_path=body.resource_path,
            domain=body.domain,
            client_meta=body.client_meta,
        )
        db.commit()
        return PresenceHeartbeatResponse(
            presence=PresenceOut.model_validate(row),
            joined=joined,
        )
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("presence_heartbeat_failed", 400)


@router.get("/presence", response_model=PresenceListResponse)
def list_presence(
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = CollaborationService(db)
    try:
        rows = svc.list_presence(user=user, project_id=project_id)
        return PresenceListResponse(data=[PresenceOut.model_validate(r) for r in rows])
    except ValueError as e:
        if str(e) == "project_not_found":
            raise _err(str(e), 404)
        raise _err("presence_list_failed", 400)


@router.post("/presence/leave", response_model=PresenceLeaveResponse)
def leave_presence(
    body: PresenceLeaveRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    svc = CollaborationService(db)
    try:
        left = svc.leave_presence(
            user=user, project_id=body.project_id, session_id=body.session_id
        )
        db.commit()
        return PresenceLeaveResponse(left=left)
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("presence_leave_failed", 400)


@router.post("/locks/acquire", response_model=SoftLockAcquireResponse, status_code=200)
def acquire_soft_lock(
    body: SoftLockAcquireRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    """Advisory soft lock: does not block other editors; surfaces holder for UI warnings."""
    svc = CollaborationService(db)
    try:
        lock, acquired = svc.acquire_soft_lock(
            user=user,
            project_id=body.project_id,
            resource_path=body.resource_path,
            session_id=body.session_id,
            ttl_seconds=body.ttl_seconds,
        )
        db.commit()
        lock_out = SoftLockOut.model_validate(lock)
        return SoftLockAcquireResponse(
            lock=lock_out,
            acquired=acquired,
            held_by_other=not acquired,
            existing_lock=None if acquired else lock_out,
        )
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("soft_lock_acquire_failed", 400)


@router.delete("/locks/{lock_id}", status_code=204)
def release_soft_lock(
    lock_id: uuid.UUID,
    project_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    svc = CollaborationService(db)
    try:
        svc.release_soft_lock(user=user, project_id=project_id, lock_id=lock_id)
        db.commit()
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code in ("project_not_found", "lock_not_found"):
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("soft_lock_release_failed", 400)


@router.get("/locks", response_model=SoftLockListResponse)
def list_soft_locks(
    project_id: uuid.UUID = Query(...),
    resource_path: str | None = Query(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    svc = CollaborationService(db)
    try:
        rows = svc.list_soft_locks(
            user=user, project_id=project_id, resource_path=resource_path
        )
        return SoftLockListResponse(data=[SoftLockOut.model_validate(r) for r in rows])
    except ValueError as e:
        if str(e) == "project_not_found":
            raise _err(str(e), 404)
        raise _err("soft_lock_list_failed", 400)


@router.post("/alerts", response_model=CrossDomainAlertResponse, status_code=201)
def cross_domain_alert(
    body: CrossDomainAlertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    svc = CollaborationService(db)
    try:
        svc.publish_cross_domain_alert(
            user=user,
            project_id=body.project_id,
            alert_id=body.alert_id,
            source_domain=body.source_domain,
            target_domain=body.target_domain,
            severity=body.severity,
            message=body.message,
            context=body.context,
        )
        db.commit()
        return CrossDomainAlertResponse(alert_id=body.alert_id, published=True)
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("cross_domain_alert_failed", 400)


@router.post("/crdt/operations", response_model=CrdtOperationResponse, status_code=201)
def submit_crdt_operation(
    body: CrdtOperationRequest,
    db: Session = Depends(get_db),
    user=Depends(require_role("editor")),
):
    """CRDT merge engine stub: accepts envelope, publishes idempotent crdt_operation event."""
    svc = CollaborationService(db)
    try:
        row, created = svc.submit_crdt_operation(
            user=user,
            project_id=body.project_id,
            document_id=body.document_id,
            operation_id=body.operation_id,
            envelope=body.envelope,
        )
        db.commit()
        return CrdtOperationResponse(
            document_id=body.document_id,
            operation_id=body.operation_id,
            envelope=row.metadata_ or body.envelope,
            accepted=created,
        )
    except ValueError as e:
        db.rollback()
        code = str(e)
        if code == "project_not_found":
            raise _err(code, 404)
        if code == "forbidden":
            raise _err(code, 403)
        raise _err("crdt_operation_failed", 400)
