"""Octopart enrichment stub — 7-day cache in Postgres `parts` table."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import Part

CACHE_TTL_DAYS = 7


def _cache_valid(part: Part) -> bool:
    if part.enriched_at is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS)
    enriched = part.enriched_at
    if enriched.tzinfo is None:
        enriched = enriched.replace(tzinfo=timezone.utc)
    return enriched >= cutoff


def fetch_octopart_stub(mpn: str, manufacturer: str) -> dict[str, Any]:
    """Placeholder for Octopart API — returns deterministic stub payload."""
    return {
        "source": "octopart_stub",
        "mpn": mpn,
        "manufacturer": manufacturer,
        "lifecycle": "active",
        "offers": [],
        "specs": {},
    }


def get_or_enrich_part(db: Session, mpn: str, manufacturer: str) -> Part:
    mfr = manufacturer or "Unknown"
    part = db.scalar(select(Part).where(Part.mpn == mpn, Part.manufacturer == mfr))
    if part is None:
        part = Part(mpn=mpn, manufacturer=mfr)
        db.add(part)
        db.flush()

    if _cache_valid(part):
        return part

    payload = fetch_octopart_stub(mpn, mfr)
    part.lifecycle = payload.get("lifecycle")
    part.enrichment_data = payload
    part.enriched_at = datetime.now(timezone.utc)
    part.octopart_id = f"stub-{mpn}-{mfr}"
    return part


def enrich_parts_from_parsed(db: Session, parsed: dict[str, Any]) -> int:
    from graph.linker import extract_parts

    count = 0
    for ref in extract_parts(parsed):
        get_or_enrich_part(db, ref.mpn, ref.manufacturer)
        count += 1
    return count
