from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from sqlalchemy.orm import Session

from app.auth.api_keys import authenticate_api_key
from app.auth.jwt import safe_decode
from app.auth.rbac import can_admin, can_approve, can_upload, role_at_least
from app.dependencies import get_db
from app.models.db import User

security = HTTPBearer(auto_error=False)
BCRYPT_ROUNDS = 12


@dataclass
class CurrentUser:
    id: UUID
    org_id: UUID
    email: str
    name: str
    role: str
    api_key_scopes: list[str] = field(default_factory=list)


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(
        plain.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing bearer token"},
        )

    token = credentials.credentials

    if token.startswith("hcp_live_") or token.startswith("hcp_test_"):
        result = authenticate_api_key(db, token)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "unauthorized", "message": "Invalid API key"},
            )
        user, api_key = result
        db.commit()
        return CurrentUser(
            id=user.id,
            org_id=user.org_id,
            email=user.email,
            name=user.name,
            role=user.role,
            api_key_scopes=list(api_key.scopes or []),
        )

    claims = safe_decode(token)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid or expired token"},
        )

    user_id = UUID(claims["sub"])
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "User not found or inactive"},
        )

    return CurrentUser(
        id=user.id,
        org_id=user.org_id,
        email=user.email,
        name=user.name,
        role=user.role,
    )


def require_upload_permission(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not can_upload(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": "Editor role or higher required to upload",
            },
        )
    return user


def require_approver(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not can_approve(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Approver role or higher required"},
        )
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not can_admin(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "forbidden", "message": "Admin role required"},
        )
    return user


def require_graph_query(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if (
        can_admin(user.role)
        or "graph_query" in user.api_key_scopes
        or "admin" in user.api_key_scopes
    ):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "forbidden",
            "message": "graph_query scope or admin role required",
        },
    )


def require_role(minimum: str):
    def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not role_at_least(user.role, minimum):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "forbidden",
                    "message": f"{minimum} role or higher required",
                },
            )
        return user

    return _checker
