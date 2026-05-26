from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.db import HardwareObject, Project, Version

try:
    from opensearchpy import OpenSearch
    from opensearchpy.exceptions import OpenSearchException
except ImportError:  # pragma: no cover
    OpenSearch = None  # type: ignore[misc, assignment]
    OpenSearchException = Exception  # type: ignore[misc, assignment]


INDEX_MAPPING = {
    "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 0}},
    "mappings": {
        "properties": {
            "org_id": {"type": "keyword"},
            "object_id": {"type": "keyword"},
            "version_id": {"type": "keyword"},
            "name": {"type": "text"},
            "filename": {"type": "text"},
            "object_type": {"type": "keyword"},
            "domain": {"type": "keyword"},
            "source_tool": {"type": "keyword"},
            "representation": {"type": "keyword"},
            "lifecycle_state": {"type": "keyword"},
            "project_id": {"type": "keyword"},
            "project_name": {"type": "keyword"},
            "version_num": {"type": "integer"},
            "mpn": {"type": "keyword"},
            "parsed_at": {"type": "date"},
        }
    },
}


@dataclass
class SearchParams:
    org_id: uuid.UUID
    q: str | None = None
    object_type: str | None = None
    domain: str | None = None
    source_tool: str | None = None
    representation: str | None = None
    state: str | None = None
    project_id: uuid.UUID | None = None
    uploaded_by: uuid.UUID | None = None
    mpn: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    per_page: int = 20


class OpenSearchIndex:
    def __init__(self, url: str, index_name: str) -> None:
        if OpenSearch is None:
            raise RuntimeError("opensearch-py not installed")
        self._client = OpenSearch(
            hosts=[url],
            use_ssl=url.startswith("https"),
            verify_certs=False,
            ssl_show_warn=False,
        )
        self._index = index_name

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except OpenSearchException:
            return False

    def ensure_index(self) -> None:
        if not self._client.indices.exists(index=self._index):
            self._client.indices.create(index=self._index, body=INDEX_MAPPING)

    def index_version(
        self,
        *,
        org_id: str,
        object_id: str,
        version_id: str,
        name: str,
        object_type: str,
        domain: str | None = None,
        source_tool: str | None = None,
        representation: str | None = None,
        lifecycle_state: str,
        project_id: str,
        project_name: str,
        version_num: int,
        filename: str,
        mpns: list[str],
        parsed_at: datetime,
    ) -> None:
        self.ensure_index()
        doc = {
            "org_id": org_id,
            "object_id": object_id,
            "version_id": version_id,
            "name": name,
            "object_type": object_type,
            "domain": domain,
            "source_tool": source_tool,
            "representation": representation,
            "lifecycle_state": lifecycle_state,
            "project_id": project_id,
            "project_name": project_name,
            "version_num": version_num,
            "filename": filename,
            "mpn": mpns,
            "parsed_at": parsed_at.isoformat(),
        }
        self._client.index(
            index=self._index, id=version_id, body=doc, refresh="wait_for"
        )

    def search(self, params: SearchParams) -> dict:
        self.ensure_index()
        page = max(params.page, 1)
        per_page = min(max(params.per_page, 1), 100)
        must: list[dict] = [{"term": {"org_id": str(params.org_id)}}]
        if params.q:
            must.append(
                {
                    "multi_match": {
                        "query": params.q,
                        "fields": ["name^2", "filename", "mpn", "project_name"],
                    }
                }
            )
        if params.object_type:
            must.append({"term": {"object_type": params.object_type}})
        if params.domain:
            must.append({"term": {"domain": params.domain}})
        if params.source_tool:
            must.append({"term": {"source_tool": params.source_tool}})
        if params.representation:
            must.append({"term": {"representation": params.representation}})
        if params.state:
            must.append({"term": {"lifecycle_state": params.state}})
        if params.project_id:
            must.append({"term": {"project_id": str(params.project_id)}})
        if params.mpn:
            must.append({"term": {"mpn": params.mpn}})

        body = {
            "query": {"bool": {"must": must}},
            "from": (page - 1) * per_page,
            "size": per_page,
            "aggs": {
                "types": {"terms": {"field": "object_type", "size": 20}},
                "domains": {"terms": {"field": "domain", "size": 10}},
                "source_tools": {"terms": {"field": "source_tool", "size": 20}},
                "representations": {"terms": {"field": "representation", "size": 5}},
                "states": {"terms": {"field": "lifecycle_state", "size": 20}},
                "projects": {"terms": {"field": "project_id", "size": 50}},
            },
        }
        resp = self._client.search(index=self._index, body=body)
        hits = resp.get("hits", {})
        total = hits.get("total", {})
        total_val = (
            total.get("value", 0) if isinstance(total, dict) else int(total or 0)
        )
        data = [
            {
                "object_id": h["_source"].get("object_id"),
                "name": h["_source"].get("name"),
                "object_type": h["_source"].get("object_type"),
                "project_id": h["_source"].get("project_id"),
                "version_num": h["_source"].get("version_num"),
                "lifecycle_state": h["_source"].get("lifecycle_state"),
                "version_id": h["_source"].get("version_id"),
            }
            for h in hits.get("hits", [])
        ]
        aggs = resp.get("aggregations", {})
        facets = {
            "types": {
                b["key"]: b["doc_count"]
                for b in aggs.get("types", {}).get("buckets", [])
            },
            "domains": {
                b["key"]: b["doc_count"]
                for b in aggs.get("domains", {}).get("buckets", [])
            },
            "source_tools": {
                b["key"]: b["doc_count"]
                for b in aggs.get("source_tools", {}).get("buckets", [])
            },
            "representations": {
                b["key"]: b["doc_count"]
                for b in aggs.get("representations", {}).get("buckets", [])
            },
            "states": {
                b["key"]: b["doc_count"]
                for b in aggs.get("states", {}).get("buckets", [])
            },
            "projects": {
                b["key"]: b["doc_count"]
                for b in aggs.get("projects", {}).get("buckets", [])
            },
        }
        total_pages = (total_val + per_page - 1) // per_page if per_page else 0
        return {
            "data": data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_val,
                "total_pages": total_pages,
            },
            "facets": facets,
        }


_os_index: OpenSearchIndex | None = None


@lru_cache
def get_search_service() -> OpenSearchIndex:
    global _os_index
    if _os_index is None:
        _os_index = OpenSearchIndex(settings.opensearch_url, settings.opensearch_index)
    return _os_index


class SearchService:
    """Postgres-backed search; uses OpenSearch when available."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, params: SearchParams) -> dict:
        try:
            os_client = get_search_service()
            if os_client.ping():
                return os_client.search(params)
        except Exception:
            pass
        return self._search_postgres(params)

    def _search_postgres(self, params: SearchParams) -> dict:
        obj_query = select(HardwareObject).where(
            HardwareObject.org_id == params.org_id,
            HardwareObject.deleted_at.is_(None),
        )
        if params.project_id:
            obj_query = obj_query.where(HardwareObject.project_id == params.project_id)
        if params.object_type:
            obj_query = obj_query.where(
                HardwareObject.object_type == params.object_type
            )
        if params.domain:
            obj_query = obj_query.where(HardwareObject.domain == params.domain)
        if params.source_tool:
            obj_query = obj_query.where(
                HardwareObject.source_tool == params.source_tool
            )
        if params.representation:
            obj_query = obj_query.where(
                HardwareObject.representation == params.representation
            )
        if params.q:
            obj_query = obj_query.where(HardwareObject.name.ilike(f"%{params.q}%"))

        objects = list(self.db.scalars(obj_query))
        hits: list[dict] = []
        for obj in objects:
            versions = list(
                self.db.scalars(
                    select(Version)
                    .where(Version.object_id == obj.id, Version.org_id == params.org_id)
                    .order_by(Version.version_num.desc())
                )
            )
            if not versions:
                continue
            ver = versions[0]
            if params.state and ver.lifecycle_state != params.state:
                continue
            if params.uploaded_by and ver.uploaded_by != params.uploaded_by:
                continue
            if params.date_from and ver.created_at < params.date_from:
                continue
            if params.date_to and ver.created_at > params.date_to:
                continue
            hits.append(
                {
                    "object_id": str(obj.id),
                    "name": obj.name,
                    "object_type": obj.object_type,
                    "project_id": str(obj.project_id),
                    "version_num": ver.version_num,
                    "lifecycle_state": ver.lifecycle_state,
                    "parse_status": ver.parse_status,
                }
            )

        total = len(hits)
        start = (params.page - 1) * params.per_page
        data = hits[start : start + params.per_page]
        facets = self._facets(params.org_id)
        total_pages = (
            (total + params.per_page - 1) // params.per_page if params.per_page else 0
        )
        return {
            "data": data,
            "pagination": {
                "page": params.page,
                "per_page": params.per_page,
                "total": total,
                "total_pages": total_pages,
            },
            "facets": facets,
        }

    def _facets(self, org_id: uuid.UUID) -> dict:
        type_rows = self.db.execute(
            select(HardwareObject.object_type, func.count())
            .where(HardwareObject.org_id == org_id, HardwareObject.deleted_at.is_(None))
            .group_by(HardwareObject.object_type)
        ).all()
        state_rows = self.db.execute(
            select(Version.lifecycle_state, func.count())
            .where(Version.org_id == org_id)
            .group_by(Version.lifecycle_state)
        ).all()
        domain_rows = self.db.execute(
            select(HardwareObject.domain, func.count())
            .where(
                HardwareObject.org_id == org_id,
                HardwareObject.deleted_at.is_(None),
                HardwareObject.domain.isnot(None),
            )
            .group_by(HardwareObject.domain)
        ).all()
        tool_rows = self.db.execute(
            select(HardwareObject.source_tool, func.count())
            .where(
                HardwareObject.org_id == org_id,
                HardwareObject.deleted_at.is_(None),
                HardwareObject.source_tool.isnot(None),
            )
            .group_by(HardwareObject.source_tool)
        ).all()
        rep_rows = self.db.execute(
            select(HardwareObject.representation, func.count())
            .where(
                HardwareObject.org_id == org_id,
                HardwareObject.deleted_at.is_(None),
                HardwareObject.representation.isnot(None),
            )
            .group_by(HardwareObject.representation)
        ).all()
        project_rows = self.db.execute(
            select(Project.id, Project.name, func.count(HardwareObject.id))
            .join(HardwareObject, HardwareObject.project_id == Project.id)
            .where(Project.org_id == org_id, HardwareObject.deleted_at.is_(None))
            .group_by(Project.id, Project.name)
        ).all()
        return {
            "types": {row[0]: row[1] for row in type_rows},
            "domains": {row[0]: row[1] for row in domain_rows},
            "source_tools": {row[0]: row[1] for row in tool_rows},
            "representations": {row[0]: row[1] for row in rep_rows},
            "states": {row[0]: row[1] for row in state_rows},
            "projects": {
                str(row[0]): {"name": row[1], "count": row[2]} for row in project_rows
            },
        }
