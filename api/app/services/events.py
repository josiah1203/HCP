from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db import EventLog

_EVENT_ID_NAMESPACE = uuid.UUID("5a9b0c7f-4a08-4d91-83f2-95fb20c5fb42")


def deterministic_event_id(
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    event_type: str,
    dedupe_key: str,
) -> uuid.UUID:
    return uuid.uuid5(
        _EVENT_ID_NAMESPACE, f"{org_id}:{project_id}:{event_type}:{dedupe_key}"
    )


class EventPublisher:
    def __init__(self, db: Session) -> None:
        self.db = db

    def publish(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        event_type: str,
        dedupe_key: str,
        actor_id: uuid.UUID | None = None,
        source: str = "api",
        metadata: dict[str, Any] | None = None,
        event_id: uuid.UUID | None = None,
    ) -> tuple[EventLog, bool]:
        eid = event_id or deterministic_event_id(
            org_id=org_id,
            project_id=project_id,
            event_type=event_type,
            dedupe_key=dedupe_key,
        )
        row = EventLog(
            event_id=eid,
            org_id=org_id,
            project_id=project_id,
            event_type=event_type,
            dedupe_key=dedupe_key,
            actor_id=actor_id,
            source=source,
            metadata_=metadata,
        )
        self.db.add(row)
        try:
            self.db.flush()
            return row, True
        except IntegrityError:
            self.db.rollback()
            existing = self.db.scalar(
                select(EventLog).where(
                    EventLog.event_id == eid,
                )
            )
            if existing is not None:
                return existing, False
            existing = self.db.scalar(
                select(EventLog).where(
                    EventLog.org_id == org_id,
                    EventLog.project_id == project_id,
                    EventLog.event_type == event_type,
                    EventLog.dedupe_key == dedupe_key,
                )
            )
            if existing is None:
                raise
            return existing, False

