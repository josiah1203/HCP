from __future__ import annotations
"""Celery tasks for PartGraph auto-linker and enrichment."""

import json
import os
import sys
from datetime import datetime, timezone
from uuid import UUID

from celery import Celery

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graph.linker import LinkContext, run_auto_link

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://hcp:hcp@localhost:5432/hcp"
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
GRAPH_QUEUE = os.environ.get("HCP_GRAPH_QUEUE", "hcp.graph")

celery_app = Celery("hcp_graph", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_default_queue = GRAPH_QUEUE
celery_app.conf.task_routes = {
    "graph.tasks.auto_link_version": {"queue": GRAPH_QUEUE},
    "graph.tasks.enrich_parts_for_version": {"queue": GRAPH_QUEUE},
}


def enqueue_auto_link(version_id: str) -> str:
    result = celery_app.send_task(
        "graph.tasks.auto_link_version",
        args=[version_id],
        queue=GRAPH_QUEUE,
    )
    return result.id


@celery_app.task(name="graph.tasks.auto_link_version", bind=True, max_retries=3)
def auto_link_version(self, version_id: str) -> dict:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.models.db import HardwareObject, Org, Project, Version
    from app.services.graph import get_graph_service
    from app.services.search import get_search_service
    from infra.pal.factory import get_storage_provider

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        version = db.get(Version, UUID(version_id))
        if version is None:
            return {"status": "error", "message": "version not found"}

        if version.parse_status not in ("complete", "skipped"):
            return {"status": "skipped", "reason": "parse_not_complete"}

        hw = db.get(HardwareObject, version.object_id)
        project = db.get(Project, hw.project_id) if hw else None
        org = db.get(Org, version.org_id)
        if hw is None or project is None or org is None:
            return {"status": "error", "message": "metadata missing"}

        parsed: dict = {}
        if version.parsed_key:
            storage = get_storage_provider()
            raw = storage.download(version.parsed_key)
            parsed = json.loads(raw.decode() if isinstance(raw, bytes) else raw)

        prev_id = None
        if version.version_num > 1:
            from app.models.db import Version as V

            prev = db.scalar(
                select(V.id).where(
                    V.object_id == version.object_id,
                    V.version_num == version.version_num - 1,
                )
            )
            if prev:
                prev_id = str(prev)

        ctx = LinkContext(
            org_id=str(version.org_id),
            org_name=org.name,
            project_id=str(project.id),
            project_name=project.name,
            object_id=str(hw.id),
            object_name=hw.name,
            object_type=hw.object_type,
            version_id=str(version.id),
            version_num=version.version_num,
            lifecycle_state=version.lifecycle_state,
            previous_version_id=prev_id,
        )

        graph = get_graph_service()
        with graph.session() as session:
            uses = run_auto_link(session, ctx, parsed)
            if version.representation == "derived" and version.derived_from_version_id:
                session.run(
                    """
                    MATCH (child:Version {version_id: $child_id, org_id: $org_id})
                    MATCH (parent:Version {version_id: $parent_id, org_id: $org_id})
                    MERGE (child)-[:DERIVED_FROM]->(parent)
                    """,
                    {
                        "org_id": str(version.org_id),
                        "child_id": str(version.id),
                        "parent_id": str(version.derived_from_version_id),
                    },
                )

        search = get_search_service()
        from graph.linker import extract_parts

        mpns = [p.mpn for p in extract_parts(parsed)]
        search.index_version(
            org_id=str(version.org_id),
            object_id=str(hw.id),
            version_id=str(version.id),
            name=hw.name,
            object_type=hw.object_type,
            domain=version.domain or hw.domain,
            source_tool=version.source_tool or hw.source_tool,
            representation=version.representation or hw.representation,
            lifecycle_state=version.lifecycle_state,
            project_id=str(project.id),
            project_name=project.name,
            version_num=version.version_num,
            filename=version.filename,
            mpns=mpns,
            parsed_at=version.parsed_at or datetime.now(timezone.utc),
        )

        enrich_parts_for_version.delay(version_id)

        return {"status": "ok", "version_id": version_id, "uses_edges": uses}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    finally:
        db.close()


@celery_app.task(name="graph.tasks.enrich_parts_for_version")
def enrich_parts_for_version(version_id: str) -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.db import Version
    from app.services.enrichment import enrich_parts_from_parsed

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        version = db.get(Version, UUID(version_id))
        if version is None or not version.parsed_key:
            return {"status": "skipped"}
        from infra.pal.factory import get_storage_provider

        storage = get_storage_provider()
        raw = storage.download(version.parsed_key)
        parsed = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        count = enrich_parts_from_parsed(db, parsed)
        db.commit()
        return {"status": "ok", "enriched": count}
    finally:
        db.close()
