from __future__ import annotations
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.dependencies import get_db
from app.services.search import SearchParams, SearchService

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.get("")
def search(
    q: str | None = None,
    type: str | None = Query(None, alias="type"),
    domain: str | None = None,
    source_tool: str | None = None,
    representation: str | None = None,
    state: str | None = None,
    project_id: uuid.UUID | None = None,
    uploaded_by: uuid.UUID | None = None,
    mpn: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    params = SearchParams(
        org_id=user.org_id,
        q=q,
        object_type=type,
        domain=domain,
        source_tool=source_tool,
        representation=representation,
        state=state,
        project_id=project_id,
        uploaded_by=uploaded_by,
        mpn=mpn,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return SearchService(db).search(params)
