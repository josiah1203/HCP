from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_events_publish
from app.dependencies import get_db
from app.models.db import EventLog, Project
from app.models.schemas import (
    EventOut,
    EventPollResponse,
    EventPublishRequest,
    EventPublishResponse,
)
from app.services.event_taxonomy import validate_event_type
from app.services.events import EventPublisher

router = APIRouter(prefix="/v1/events", tags=["events"])


def _err(code: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": code})


@router.post("/publish", response_model=EventPublishResponse, status_code=201)
def publish_event(
    body: EventPublishRequest,
    db: Session = Depends(get_db),
    user=Depends(require_events_publish),
):
    project = db.scalar(
        select(Project.id).where(Project.id == body.project_id, Project.org_id == user.org_id)
    )
    if project is None:
        raise _err("project_not_found", 404)

    try:
        validate_event_type(body.event_type)
    except ValueError:
        raise _err("unknown_event_type", 422)

    pub = EventPublisher(db)
    row, created = pub.publish(
        org_id=user.org_id,
        project_id=body.project_id,
        event_type=body.event_type,
        dedupe_key=body.dedupe_key,
        actor_id=body.actor_id or user.id,
        source=body.source or "api",
        metadata=body.metadata,
        event_id=body.event_id,
    )
    db.commit()
    return EventPublishResponse(
        event=EventOut.model_validate(row),
        deduped=(not created),
    )


@router.get("/poll", response_model=EventPollResponse)
def poll_events(
    project_id: uuid.UUID = Query(...),
    cursor: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    project = db.scalar(
        select(Project.id).where(Project.id == project_id, Project.org_id == user.org_id)
    )
    if project is None:
        raise _err("project_not_found", 404)

    rows = list(
        db.scalars(
            select(EventLog)
            .where(
                EventLog.org_id == user.org_id,
                EventLog.project_id == project_id,
                EventLog.seq > cursor,
            )
            .order_by(EventLog.seq.asc())
            .limit(limit + 1)
        )
    )

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1].seq if rows else cursor
    return EventPollResponse(
        data=[EventOut.model_validate(r) for r in rows],
        next_cursor=next_cursor,
        has_more=has_more,
    )

