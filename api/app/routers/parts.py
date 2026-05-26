from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.dependencies import get_db
from app.services.enrichment import get_or_enrich_part
from app.services.parts import PartsService

router = APIRouter(prefix="/v1/parts", tags=["parts"])


@router.get("/search")
def search_parts(
    q: str = Query(..., min_length=1),
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = PartsService(db)
    parts = service.search(q)
    return {
        "data": [
            {
                "mpn": p.mpn,
                "manufacturer": p.manufacturer,
                "description": p.description,
                "lifecycle": p.lifecycle,
            }
            for p in parts
        ]
    }


@router.get("/{mpn}")
def get_part(
    mpn: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = PartsService(db)
    part = service.get_by_mpn(mpn)
    if part is None:
        part = service.upsert_stub(mpn)
        db.commit()
    return {
        "mpn": part.mpn,
        "manufacturer": part.manufacturer,
        "description": part.description,
        "lifecycle": part.lifecycle,
        "enriched_at": part.enriched_at,
        "enrichment_data": part.enrichment_data,
    }


@router.get("/{mpn}/where-used")
def where_used(
    mpn: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = PartsService(db)
    return {"mpn": mpn, "data": service.where_used(mpn, user.org_id)}


@router.post("/{mpn}/refresh-enrichment")
def refresh_enrichment(
    mpn: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    part = get_or_enrich_part(db, mpn, "Unknown")
    db.commit()
    return {
        "mpn": part.mpn,
        "enriched_at": part.enriched_at,
        "enrichment_data": part.enrichment_data,
    }
