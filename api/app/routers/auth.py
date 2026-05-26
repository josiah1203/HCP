from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.api_keys import create_api_key_record
from app.auth.dependencies import CurrentUser, get_current_user, verify_password
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
)
from app.config import settings
from app.dependencies import get_db
from app.models.db import ApiKey, User
from app.models.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyOut,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(
        select(User).where(User.email == body.email, User.is_active.is_(True))
    )
    if (
        user is None
        or user.password_hash is None
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid email or password"},
        )

    access = create_access_token(user.id, user.org_id, user.role, user.email)
    refresh = create_refresh_token(db, user.id)
    db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    result = refresh_access_token(db, body.refresh_token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthorized",
                "message": "Invalid or expired refresh token",
            },
        )
    access, expires_in = result
    db.commit()
    return TokenResponse(access_token=access, expires_in=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, db: Session = Depends(get_db)) -> Response:
    revoke_refresh_token(db, body.refresh_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=dict)
def me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "user": UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            org_id=user.org_id,
        )
    }


@router.post(
    "/api-keys", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED
)
def create_api_key(
    body: ApiKeyCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreated:
    db_user = db.get(User, user.id)
    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "User not found"},
        )

    record, full_key = create_api_key_record(
        db, user=db_user, name=body.name, scopes=body.scopes
    )
    db.commit()
    return ApiKeyCreated(
        key=full_key, key_id=record.id, name=record.name, prefix=record.key_prefix
    )


@router.get("/api-keys", response_model=dict)
def list_api_keys(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    keys = db.scalars(
        select(ApiKey).where(
            ApiKey.org_id == user.org_id,
            ApiKey.user_id == user.id,
            ApiKey.is_active.is_(True),
        )
    ).all()
    return {
        "data": [
            ApiKeyOut(
                key_id=k.id,
                name=k.name,
                prefix=k.key_prefix,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ]
    }


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    api_key = db.scalar(
        select(ApiKey).where(
            ApiKey.id == key_id, ApiKey.org_id == user.org_id, ApiKey.user_id == user.id
        )
    )
    if api_key is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "API key not found"},
        )
    api_key.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
