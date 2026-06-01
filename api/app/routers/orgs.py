from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, require_admin
from app.dependencies import get_db
from app.models.schemas import (
    OrgInviteAccept,
    OrgInviteAcceptResponse,
    OrgInviteCreate,
    OrgInviteCreated,
    OrgRegisterRequest,
    OrgRegisterResponse,
)
from app.services.org_invites import OrgInviteService

router = APIRouter(prefix="/v1/orgs", tags=["orgs"])


@router.post(
    "/register",
    response_model=OrgRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_org(
    body: OrgRegisterRequest,
    db: Session = Depends(get_db),
) -> OrgRegisterResponse:
    service = OrgInviteService(db)
    try:
        result = service.register_org(
            org_name=body.org_name,
            slug=body.slug,
            admin_email=body.admin_email,
            admin_name=body.admin_name,
            admin_password=body.admin_password,
            plan=body.plan,
        )
    except ValueError as exc:
        code = str(exc)
        if code in ("email_in_use", "slug_taken"):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "conflict",
                    "message": "Email already registered"
                    if code == "email_in_use"
                    else "Organization slug already taken",
                },
            ) from exc
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": code},
        ) from exc
    return OrgRegisterResponse(**result)


@router.post(
    "/invites",
    response_model=OrgInviteCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_invite(
    body: OrgInviteCreate,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrgInviteCreated:
    service = OrgInviteService(db)
    try:
        result = service.create_invite(
            user=user,
            email=body.email,
            role=body.role,
        )
    except ValueError as exc:
        code = str(exc)
        status_code = 403 if code == "forbidden" else 409
        if code == "invalid_role":
            status_code = 422
        raise HTTPException(
            status_code=status_code,
            detail={"code": code, "message": code.replace("_", " ")},
        ) from exc
    return OrgInviteCreated(**result)


@router.post("/invites/accept", response_model=OrgInviteAcceptResponse)
def accept_invite(
    body: OrgInviteAccept,
    db: Session = Depends(get_db),
) -> OrgInviteAcceptResponse:
    service = OrgInviteService(db)
    try:
        result = service.accept_invite(
            token=body.token,
            name=body.name,
            password=body.password,
            email=body.email,
        )
    except ValueError as exc:
        code = str(exc)
        status_map = {
            "invalid_token": 404,
            "invite_expired": 410,
            "invite_already_used": 409,
            "email_mismatch": 422,
            "email_in_use": 409,
        }
        raise HTTPException(
            status_code=status_map.get(code, 422),
            detail={"code": code, "message": code.replace("_", " ")},
        ) from exc
    return OrgInviteAcceptResponse(**result)
