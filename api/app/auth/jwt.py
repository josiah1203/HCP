from __future__ import annotations
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.api_keys import hash_refresh_token
from app.config import settings
from app.models.db import RefreshToken


def create_access_token(user_id: UUID, org_id: UUID, role: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "role": role,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(db: Session, user_id: UUID) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw)
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires,
        )
    )
    db.flush()
    return raw


def refresh_access_token(db: Session, raw_refresh: str) -> tuple[str, int] | None:
    token_hash = hash_refresh_token(raw_refresh)
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if record is None:
        return None
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        return None

    from app.models.db import User

    user = db.get(User, record.user_id)
    if user is None or not user.is_active:
        return None

    token = create_access_token(user.id, user.org_id, user.role, user.email)
    return token, settings.jwt_access_expire_minutes * 60


def revoke_refresh_token(db: Session, raw_refresh: str) -> bool:
    token_hash = hash_refresh_token(raw_refresh)
    record = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if record is None or record.revoked_at is not None:
        return False
    record.revoked_at = datetime.now(timezone.utc)
    return True


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def safe_decode(token: str) -> dict[str, Any] | None:
    try:
        claims = decode_access_token(token)
        if claims.get("type", "access") != "access":
            return None
        return claims
    except JWTError:
        return None
