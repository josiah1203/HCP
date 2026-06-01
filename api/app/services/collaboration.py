from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.rbac import role_at_least
from app.models.db import CollaborationPresence, CollaborationSoftLock, Project
from app.services.event_emission import EventEmissionHooks, heartbeat_bucket_ts

PRESENCE_TTL_SECONDS = 90
SOFT_LOCK_TTL_SECONDS = 300


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class CollaborationService:
    """Phase 0.5 beta collaboration: polling presence, advisory soft locks."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._events = EventEmissionHooks(db)

    def _require_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.org_id == org_id)
        )
        if project is None:
            raise ValueError("project_not_found")
        return project

    def _require_editor(self, user: CurrentUser) -> None:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")

    def heartbeat_presence(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        session_id: str,
        resource_path: str | None = None,
        domain: str | None = None,
        client_meta: dict[str, Any] | None = None,
    ) -> tuple[CollaborationPresence, bool]:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        now = _now()

        row = self.db.scalar(
            select(CollaborationPresence).where(
                CollaborationPresence.org_id == user.org_id,
                CollaborationPresence.project_id == project_id,
                CollaborationPresence.user_id == user.id,
                CollaborationPresence.session_id == session_id,
            )
        )
        is_new = row is None
        if row is None:
            row = CollaborationPresence(
                org_id=user.org_id,
                project_id=project_id,
                user_id=user.id,
                session_id=session_id,
                resource_path=resource_path,
                domain=domain,
                client_meta=client_meta,
                last_heartbeat_at=now,
            )
            self.db.add(row)
        else:
            row.resource_path = resource_path
            row.domain = domain
            if client_meta is not None:
                row.client_meta = client_meta
            row.last_heartbeat_at = now

        self.db.flush()

        meta = {
            "session_id": session_id,
            "user_id": str(user.id),
            "resource_path": resource_path,
            "domain": domain,
        }
        if is_new:
            self._events.publish_presence_joined(
                org_id=user.org_id,
                project_id=project_id,
                session_id=session_id,
                actor_id=user.id,
                metadata=meta,
            )
        self._events.publish_presence_heartbeat(
            org_id=user.org_id,
            project_id=project_id,
            session_id=session_id,
            actor_id=user.id,
            bucket_ts=heartbeat_bucket_ts(now),
            metadata=meta,
        )
        return row, is_new

    def list_presence(
        self, *, user: CurrentUser, project_id: uuid.UUID
    ) -> list[CollaborationPresence]:
        self._require_project(project_id, user.org_id)
        cutoff = _now() - timedelta(seconds=PRESENCE_TTL_SECONDS)
        rows = list(
            self.db.scalars(
                select(CollaborationPresence)
                .where(
                    CollaborationPresence.org_id == user.org_id,
                    CollaborationPresence.project_id == project_id,
                )
                .order_by(CollaborationPresence.last_heartbeat_at.desc())
            )
        )
        return [r for r in rows if _as_utc(r.last_heartbeat_at) >= cutoff]

    def leave_presence(
        self, *, user: CurrentUser, project_id: uuid.UUID, session_id: str
    ) -> bool:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        row = self.db.scalar(
            select(CollaborationPresence).where(
                CollaborationPresence.org_id == user.org_id,
                CollaborationPresence.project_id == project_id,
                CollaborationPresence.user_id == user.id,
                CollaborationPresence.session_id == session_id,
            )
        )
        if row is None:
            return False
        self.db.delete(row)
        self.db.flush()
        self._events.publish_presence_left(
            org_id=user.org_id,
            project_id=project_id,
            session_id=session_id,
            actor_id=user.id,
            metadata={"session_id": session_id, "user_id": str(user.id)},
        )
        return True

    def acquire_soft_lock(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        resource_path: str,
        session_id: str | None = None,
        ttl_seconds: int = SOFT_LOCK_TTL_SECONDS,
    ) -> tuple[CollaborationSoftLock, bool]:
        """Advisory lock: returns (lock, acquired). acquired=False if another holder is active."""
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        now = _now()
        expires = now + timedelta(seconds=ttl_seconds)

        existing = self.db.scalar(
            select(CollaborationSoftLock).where(
                CollaborationSoftLock.org_id == user.org_id,
                CollaborationSoftLock.project_id == project_id,
                CollaborationSoftLock.resource_path == resource_path,
            )
        )

        if (
            existing is not None
            and _as_utc(existing.expires_at) > now
            and existing.holder_user_id != user.id
        ):
            return existing, False

        acquired = True
        if existing is None:
            lock = CollaborationSoftLock(
                org_id=user.org_id,
                project_id=project_id,
                resource_path=resource_path,
                holder_user_id=user.id,
                holder_session_id=session_id,
                advisory=True,
                expires_at=expires,
            )
            self.db.add(lock)
        else:
            lock = existing
            lock.holder_user_id = user.id
            lock.holder_session_id = session_id
            lock.expires_at = expires
            lock.updated_at = now

        self.db.flush()
        self._events.publish_soft_lock_acquired(
            org_id=user.org_id,
            project_id=project_id,
            resource_path=resource_path,
            actor_id=user.id,
            metadata={
                "lock_id": str(lock.id),
                "resource_path": resource_path,
                "holder_user_id": str(user.id),
                "advisory": True,
            },
        )
        return lock, acquired

    def release_soft_lock(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        lock_id: uuid.UUID,
    ) -> CollaborationSoftLock:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        lock = self.db.scalar(
            select(CollaborationSoftLock).where(
                CollaborationSoftLock.id == lock_id,
                CollaborationSoftLock.org_id == user.org_id,
                CollaborationSoftLock.project_id == project_id,
            )
        )
        if lock is None:
            raise ValueError("lock_not_found")
        if lock.holder_user_id != user.id and not role_at_least(user.role, "admin"):
            raise ValueError("forbidden")

        resource_path = lock.resource_path
        self.db.delete(lock)
        self.db.flush()
        self._events.publish_soft_lock_released(
            org_id=user.org_id,
            project_id=project_id,
            resource_path=resource_path,
            lock_id=lock_id,
            actor_id=user.id,
            metadata={"lock_id": str(lock_id), "resource_path": resource_path},
        )
        return lock

    def list_soft_locks(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        resource_path: str | None = None,
    ) -> list[CollaborationSoftLock]:
        self._require_project(project_id, user.org_id)
        now = _now()
        q = select(CollaborationSoftLock).where(
            CollaborationSoftLock.org_id == user.org_id,
            CollaborationSoftLock.project_id == project_id,
        )
        if resource_path is not None:
            q = q.where(CollaborationSoftLock.resource_path == resource_path)
        rows = list(self.db.scalars(q.order_by(CollaborationSoftLock.expires_at.asc())))
        return [r for r in rows if _as_utc(r.expires_at) > now]

    def publish_cross_domain_alert(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        alert_id: str,
        source_domain: str,
        target_domain: str,
        severity: str,
        message: str,
        context: dict[str, Any] | None = None,
    ):
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        payload = {
            "alert_id": alert_id,
            "source_domain": source_domain,
            "target_domain": target_domain,
            "severity": severity,
            "message": message,
            **(context or {}),
        }
        return self._events.publish_cross_domain_alert(
            org_id=user.org_id,
            project_id=project_id,
            alert_key=alert_id,
            actor_id=user.id,
            metadata=payload,
        )

    def submit_crdt_operation(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        document_id: str,
        operation_id: str,
        envelope: dict[str, Any],
    ):
        """Forward-compatible CRDT operation envelope stub (event-only, no merge engine)."""
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        full_envelope = {
            "document_id": document_id,
            "operation_id": operation_id,
            "schema_version": 0,
            **envelope,
        }
        return self._events.publish_crdt_operation(
            org_id=user.org_id,
            project_id=project_id,
            document_id=document_id,
            operation_id=operation_id,
            actor_id=user.id,
            metadata=full_envelope,
        )

    def prune_stale_presence(self, *, user: CurrentUser, project_id: uuid.UUID) -> int:
        self._require_project(project_id, user.org_id)
        cutoff = _now() - timedelta(seconds=PRESENCE_TTL_SECONDS)
        result = self.db.execute(
            delete(CollaborationPresence).where(
                CollaborationPresence.org_id == user.org_id,
                CollaborationPresence.project_id == project_id,
                CollaborationPresence.last_heartbeat_at < cutoff,
            )
        )
        return result.rowcount or 0
