from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.db import AuditLog


def write_audit(
    db: Session,
    *,
    org_id: uuid.UUID,
    object_id: uuid.UUID,
    version_num: int,
    event_type: str,
    actor_id: uuid.UUID,
    actor_email: str,
    from_state: str | None = None,
    to_state: str | None = None,
    comment: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        org_id=org_id,
        object_id=object_id,
        version_num=version_num,
        event_type=event_type,
        from_state=from_state,
        to_state=to_state,
        actor_id=actor_id,
        actor_email=actor_email,
        comment=comment,
        metadata_=metadata,
    )
    db.add(entry)
    return entry
