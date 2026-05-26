from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import ApiKey, User

BCRYPT_ROUNDS = 12


def api_key_prefix() -> str:
    return "hcp_live_" if settings.hcp_env in ("prod", "production") else "hcp_test_"


def generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix_display, key_hash)."""
    prefix = api_key_prefix()
    secret = secrets.token_urlsafe(32)
    full_key = f"{prefix}{secret}"
    prefix_display = full_key[:16]
    key_hash = bcrypt.hashpw(
        full_key.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    ).decode("utf-8")
    return full_key, prefix_display, key_hash


def verify_api_key(plain: str, key_hash: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), key_hash.encode("utf-8"))


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_api_key_record(
    db: Session,
    *,
    user: User,
    name: str,
    scopes: list[str] | None = None,
) -> tuple[ApiKey, str]:
    full_key, prefix_display, key_hash = generate_api_key()
    record = ApiKey(
        org_id=user.org_id,
        user_id=user.id,
        name=name,
        key_prefix=prefix_display,
        key_hash=key_hash,
        scopes=scopes or ["read", "write"],
    )
    db.add(record)
    db.flush()
    return record, full_key


def authenticate_api_key(db: Session, raw_key: str) -> tuple[User, ApiKey] | None:
    if not (raw_key.startswith("hcp_live_") or raw_key.startswith("hcp_test_")):
        return None

    prefix = raw_key[:16]
    candidates = db.scalars(
        select(ApiKey).where(
            ApiKey.key_prefix == prefix,
            ApiKey.is_active.is_(True),
        )
    ).all()

    for api_key in candidates:
        if verify_api_key(raw_key, api_key.key_hash):
            user = db.get(User, api_key.user_id)
            if user is None or not user.is_active:
                return None
            api_key.last_used_at = datetime.now(timezone.utc)
            return user, api_key

    return None
