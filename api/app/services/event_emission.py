from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.services.event_taxonomy import (
    EVENT_CONFLICT_DETECTED,
    EVENT_COMMIT_CREATED,
    EVENT_CRDT_OPERATION,
    EVENT_CROSS_DOMAIN_ALERT,
    EVENT_MERGE_CREATED,
    EVENT_PRESENCE_HEARTBEAT,
    EVENT_PRESENCE_JOINED,
    EVENT_PRESENCE_LEFT,
    EVENT_SOFT_LOCK_ACQUIRED,
    EVENT_SOFT_LOCK_RELEASED,
)
from app.services.events import EventPublisher


def heartbeat_bucket_ts(now: datetime | None = None, *, bucket_seconds: int = 30) -> int:
    ts = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return int(ts.timestamp()) // bucket_seconds


def presence_heartbeat_dedupe_key(session_id: str, bucket_ts: int) -> str:
    return f"presence:{session_id}:hb:{bucket_ts}"


def presence_joined_dedupe_key(session_id: str) -> str:
    return f"presence:{session_id}:joined"


def presence_left_dedupe_key(session_id: str) -> str:
    return f"presence:{session_id}:left"


def soft_lock_acquired_dedupe_key(resource_path: str) -> str:
    return f"lock:{resource_path}:acquired"


def soft_lock_released_dedupe_key(resource_path: str, lock_id: uuid.UUID) -> str:
    return f"lock:{resource_path}:released:{lock_id}"


def cross_domain_alert_dedupe_key(alert_key: str) -> str:
    return f"alert:{alert_key}"


def crdt_operation_dedupe_key(document_id: str, operation_id: str) -> str:
    return f"crdt:{document_id}:{operation_id}"


def commit_created_dedupe_key(commit_id: uuid.UUID) -> str:
    return f"commit:{commit_id}"


def merge_created_dedupe_key(merge_id: uuid.UUID) -> str:
    return f"merge:{merge_id}"


def conflict_detected_dedupe_key(merge_id: uuid.UUID) -> str:
    return f"merge:{merge_id}:conflicts"


class EventEmissionHooks:
    """Deterministic dedupe keys + EventPublisher wrappers for Phase 0.5 beta."""

    def __init__(self, db: Session) -> None:
        self._pub = EventPublisher(db)

    def publish_commit_created(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        commit_id: uuid.UUID,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_COMMIT_CREATED,
            dedupe_key=commit_created_dedupe_key(commit_id),
            actor_id=actor_id,
            source="hos",
            metadata=metadata,
        )

    def publish_merge_created(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        merge_id: uuid.UUID,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_MERGE_CREATED,
            dedupe_key=merge_created_dedupe_key(merge_id),
            actor_id=actor_id,
            source="hos",
            metadata=metadata,
        )

    def publish_conflict_detected(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        merge_id: uuid.UUID,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_CONFLICT_DETECTED,
            dedupe_key=conflict_detected_dedupe_key(merge_id),
            actor_id=actor_id,
            source="hos",
            metadata=metadata,
        )

    def publish_presence_heartbeat(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        session_id: str,
        actor_id: uuid.UUID,
        bucket_ts: int | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        bucket = bucket_ts if bucket_ts is not None else heartbeat_bucket_ts()
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_PRESENCE_HEARTBEAT,
            dedupe_key=presence_heartbeat_dedupe_key(session_id, bucket),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_presence_joined(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        session_id: str,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_PRESENCE_JOINED,
            dedupe_key=presence_joined_dedupe_key(session_id),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_presence_left(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        session_id: str,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_PRESENCE_LEFT,
            dedupe_key=presence_left_dedupe_key(session_id),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_soft_lock_acquired(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        resource_path: str,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_SOFT_LOCK_ACQUIRED,
            dedupe_key=soft_lock_acquired_dedupe_key(resource_path),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_soft_lock_released(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        resource_path: str,
        lock_id: uuid.UUID,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_SOFT_LOCK_RELEASED,
            dedupe_key=soft_lock_released_dedupe_key(resource_path, lock_id),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_cross_domain_alert(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        alert_key: str,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_CROSS_DOMAIN_ALERT,
            dedupe_key=cross_domain_alert_dedupe_key(alert_key),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )

    def publish_crdt_operation(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        document_id: str,
        operation_id: str,
        actor_id: uuid.UUID,
        metadata: dict[str, Any] | None = None,
    ):
        return self._pub.publish(
            org_id=org_id,
            project_id=project_id,
            event_type=EVENT_CRDT_OPERATION,
            dedupe_key=crdt_operation_dedupe_key(document_id, operation_id),
            actor_id=actor_id,
            source="collaboration",
            metadata=metadata,
        )
