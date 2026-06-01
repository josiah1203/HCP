from __future__ import annotations

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, hash_password
from app.auth.jwt import create_access_token, create_refresh_token
from app.auth.rbac import can_admin
from app.config import settings
from app.models.db import Org, OrgInvite, User

INVITE_TTL_DAYS = 7
VALID_ROLES = frozenset({"viewer", "editor", "approver", "admin"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or f"org-{uuid.uuid4().hex[:8]}"


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class OrgInviteService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register_org(
        self,
        *,
        org_name: str,
        admin_email: str,
        admin_name: str,
        admin_password: str,
        plan: str = "free",
        slug: str | None = None,
    ) -> dict:
        email = admin_email.strip().lower()
        org_slug = _slugify(slug or org_name)

        existing_org = self.db.scalar(select(Org).where(Org.slug == org_slug))
        if existing_org is not None:
            raise ValueError("slug_taken")

        existing_user = self.db.scalar(select(User).where(User.email == email))
        if existing_user is not None:
            raise ValueError("email_in_use")

        org = Org(name=org_name.strip(), slug=org_slug, plan=plan)
        self.db.add(org)
        self.db.flush()

        user = User(
            org_id=org.id,
            email=email,
            name=admin_name.strip(),
            password_hash=hash_password(admin_password),
            role="admin",
        )
        self.db.add(user)
        self.db.flush()

        access = create_access_token(user.id, org.id, user.role, user.email)
        refresh = create_refresh_token(self.db, user.id)
        self.db.commit()

        return {
            "org": {"id": str(org.id), "name": org.name, "slug": org.slug},
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
            },
            "access_token": access,
            "refresh_token": refresh,
            "expires_in": settings.jwt_access_expire_minutes * 60,
        }

    def create_invite(
        self,
        *,
        user: CurrentUser,
        email: str,
        role: str,
    ) -> dict:
        if not can_admin(user.role):
            raise ValueError("forbidden")

        normalized_role = role.strip().lower()
        if normalized_role not in VALID_ROLES:
            raise ValueError("invalid_role")

        invite_email = email.strip().lower()
        pending = self.db.scalar(
            select(OrgInvite).where(
                OrgInvite.org_id == user.org_id,
                OrgInvite.email == invite_email,
                OrgInvite.accepted_at.is_(None),
            )
        )
        if pending is not None and _as_utc(pending.expires_at) > _now():
            raise ValueError("invite_pending")

        existing_member = self.db.scalar(
            select(User).where(
                User.org_id == user.org_id,
                User.email == invite_email,
                User.is_active.is_(True),
            )
        )
        if existing_member is not None:
            raise ValueError("already_member")

        token = secrets.token_urlsafe(32)
        invite = OrgInvite(
            org_id=user.org_id,
            email=invite_email,
            role=normalized_role,
            token_hash=_hash_token(token),
            invited_by=user.id,
            expires_at=_now() + timedelta(days=INVITE_TTL_DAYS),
        )
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)

        return {
            "invite_id": invite.id,
            "email": invite_email,
            "role": normalized_role,
            "invite_token": token,
            "expires_at": invite.expires_at,
        }

    def accept_invite(
        self,
        *,
        token: str,
        name: str,
        password: str,
        email: str | None = None,
    ) -> dict:
        token_hash = _hash_token(token.strip())
        invite = self.db.scalar(
            select(OrgInvite).where(OrgInvite.token_hash == token_hash)
        )
        if invite is None:
            raise ValueError("invalid_token")
        if invite.accepted_at is not None:
            raise ValueError("invite_already_used")
        if _as_utc(invite.expires_at) < _now():
            raise ValueError("invite_expired")

        if email is not None and email.strip().lower() != invite.email:
            raise ValueError("email_mismatch")

        existing = self.db.scalar(select(User).where(User.email == invite.email))
        if existing is not None:
            if existing.org_id != invite.org_id:
                raise ValueError("email_in_use")
            if not existing.is_active:
                raise ValueError("email_in_use")
            existing.role = invite.role
            existing.name = name.strip()
            existing.password_hash = hash_password(password)
            user = existing
        else:
            user = User(
                org_id=invite.org_id,
                email=invite.email,
                name=name.strip(),
                password_hash=hash_password(password),
                role=invite.role,
            )
            self.db.add(user)
            self.db.flush()

        invite.accepted_at = _now()
        invite.accepted_user_id = user.id

        access = create_access_token(user.id, user.org_id, user.role, user.email)
        refresh = create_refresh_token(self.db, user.id)
        self.db.commit()

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "org_id": str(user.org_id),
            },
            "access_token": access,
            "refresh_token": refresh,
            "expires_in": settings.jwt_access_expire_minutes * 60,
        }
