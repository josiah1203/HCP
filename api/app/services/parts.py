from __future__ import annotations
import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.db import Part
from app.services.graph import GraphService


class PartsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.graph = GraphService(db)

    def get_by_mpn(self, mpn: str) -> Part | None:
        return self.db.scalar(select(Part).where(Part.mpn == mpn).limit(1))

    def search(self, q: str, limit: int = 20) -> list[Part]:
        pattern = f"%{q}%"
        return list(
            self.db.scalars(
                select(Part)
                .where(
                    or_(
                        Part.mpn.ilike(pattern),
                        Part.manufacturer.ilike(pattern),
                        Part.description.ilike(pattern),
                    )
                )
                .limit(limit)
            )
        )

    def where_used(self, mpn: str, org_id: uuid.UUID) -> list[dict]:
        usages = []
        for org_key, links in GraphService._links.items():
            if org_key != str(org_id):
                continue
            for link in links.values():
                meta = link.get("metadata") or {}
                if meta.get("mpn") == mpn or link.get("to_object_id") == mpn:
                    usages.append(
                        {
                            "object_id": link["from_object_id"],
                            "relationship_type": link["relationship_type"],
                            "relationship_id": link["relationship_id"],
                        }
                    )
        return usages

    def refresh_enrichment(self, part: Part) -> Part:
        part.enriched_at = datetime.now(timezone.utc)
        part.enrichment_data = {
            "source": "octopart",
            "status": "stub",
            "message": "Octopart enrichment not configured",
        }
        return part

    def upsert_stub(self, mpn: str, manufacturer: str = "Unknown") -> Part:
        existing = self.get_by_mpn(mpn)
        if existing:
            return existing
        part = Part(mpn=mpn, manufacturer=manufacturer, description=f"Stub part {mpn}")
        self.db.add(part)
        self.db.flush()
        return part
