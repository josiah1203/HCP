from __future__ import annotations
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.services.graph import GraphService
from app.services.objects import ObjectService


class BOMService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.objects = ObjectService(db)
        self.graph = GraphService(db)

    def get_bom(
        self, object_id: uuid.UUID, org_id: uuid.UUID, version_num: int | None = None
    ) -> dict[str, Any]:
        hw_object = self.objects.get_object(object_id, org_id)
        if hw_object is None:
            raise ValueError("not_found")

        if version_num is None:
            versions = self.objects.list_versions(object_id, org_id)
            if not versions:
                raise ValueError("no_versions")
            version = versions[0]
        else:
            version = self.objects.get_version(object_id, version_num, org_id)
            if version is None:
                raise ValueError("version_not_found")

        parsed = self.objects.get_parsed_json(version)
        rows = (parsed or {}).get("bom_rows", [])
        return {
            "object_id": str(object_id),
            "version_num": version.version_num,
            "rows": rows,
            "components": (parsed or {}).get("components", []),
        }

    def flat_bom(self, object_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any]:
        base = self.get_bom(object_id, org_id)
        flat_rows: list[dict[str, Any]] = list(base["rows"])
        for edge in self.graph._edges_for(org_id, object_id, "out"):
            if edge["relationship_type"] != "CONTAINS":
                continue
            child_id = uuid.UUID(edge["to_object_id"])
            try:
                child = self.flat_bom(child_id, org_id)
                flat_rows.extend(child["flat_rows"])
            except ValueError:
                continue

        return {
            "object_id": str(object_id),
            "flat_rows": flat_rows,
            "total_lines": len(flat_rows),
        }

    def diff(
        self,
        object_id: uuid.UUID,
        org_id: uuid.UUID,
        version_a: int,
        version_b: int,
    ) -> dict[str, Any]:
        bom_a = self.get_bom(object_id, org_id, version_a)
        bom_b = self.get_bom(object_id, org_id, version_b)

        def key(row: dict) -> str:
            return f"{row.get('mpn', '')}:{row.get('manufacturer', '')}"

        map_a = {key(r): r for r in bom_a["rows"]}
        map_b = {key(r): r for r in bom_b["rows"]}

        added = [map_b[k] for k in map_b if k not in map_a]
        removed = [map_a[k] for k in map_a if k not in map_b]
        changed = [
            {"before": map_a[k], "after": map_b[k]}
            for k in map_a
            if k in map_b and map_a[k] != map_b[k]
        ]

        return {
            "object_id": str(object_id),
            "version_a": version_a,
            "version_b": version_b,
            "added": added,
            "removed": removed,
            "changed": changed,
        }
