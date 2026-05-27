"""Celery worker — consumes parse tasks from Redis queue."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser.pral.interfaces.parser_plugin import apply_capabilities  # noqa: E402
from parser.pral.registry import build_context, resolve_parser  # noqa: E402
from parser.schema import ParsedOutput  # noqa: E402

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg2://hcp:hcp@localhost:5432/hcp"
)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("hcp_parser", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.task_default_queue = "hcp.parse"
celery_app.conf.task_routes = {"parser.worker.parse_object": {"queue": "hcp.parse"}}

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def _parsed_storage_key(
    org_id: str, project_id: str, object_id: str, version_num: int
) -> str:
    return f"{org_id}/{project_id}/{object_id}/v{version_num}/parsed/output.json"


def _version_metadata(version) -> dict:
    """Upload metadata on Version row when API migration lands."""
    return {
        "source_tool": getattr(version, "source_tool", None),
        "domain": getattr(version, "domain", None),
        "representation": getattr(version, "representation", None),
    }


@celery_app.task(name="parser.worker.parse_object", bind=True, max_retries=3)
def parse_object(self, version_id: str) -> dict:
    from app.models.db import HardwareObject, Version  # noqa: PLC0415
    from app.services.event_taxonomy import EVENT_PARSE_COMPLETE  # noqa: PLC0415
    from app.services.events import EventPublisher  # noqa: PLC0415
    from infra.pal.factory import get_storage_provider  # noqa: PLC0415

    storage = get_storage_provider()
    db = SessionLocal()

    try:
        version = db.get(Version, UUID(version_id))
        if version is None:
            return {"status": "error", "message": "version not found"}

        version.parse_status = "processing"
        db.commit()

        hw_object = db.get(HardwareObject, version.object_id)
        if hw_object is None:
            version.parse_status = "failed"
            version.parse_error = "object not found"
            db.commit()
            return {"status": "error"}

        raw_bytes = storage.download(version.storage_key)
        meta = _version_metadata(version)
        parser = resolve_parser(
            version.filename,
            raw_bytes,
            source_tool=meta["source_tool"],
            domain=meta["domain"],
            representation=meta["representation"],
        )
        context = build_context(
            version.filename,
            str(version.object_id),
            str(version.id),
            source_tool=meta["source_tool"],
            domain=meta["domain"],
            representation=meta["representation"],
        )
        output: ParsedOutput = apply_capabilities(parser.parse(raw_bytes, context))

        parsed_key = _parsed_storage_key(
            str(version.org_id),
            str(hw_object.project_id),
            str(version.object_id),
            version.version_num,
        )
        storage.upload(
            parsed_key,
            BytesIO(output.model_dump_json().encode()),
            "application/json",
        )

        version.parsed_key = parsed_key
        version.parse_status = (
            "skipped" if parser.parser_name == "RawStore" else "complete"
        )
        version.parsed_at = datetime.now(timezone.utc)
        version.parse_error = None
        db.commit()

        if version.parse_status == "complete":
            try:
                pub = EventPublisher(db)
                pub.publish(
                    org_id=version.org_id,
                    project_id=hw_object.project_id,
                    event_type=EVENT_PARSE_COMPLETE,
                    dedupe_key=f"version:{version.id}:parse_complete",
                    actor_id=None,
                    source="parser",
                    metadata={
                        "version_id": str(version.id),
                        "object_id": str(version.object_id),
                        "version_num": version.version_num,
                    },
                )
                db.commit()
            except Exception:
                db.rollback()
            try:
                from graph.tasks import enqueue_auto_link

                enqueue_auto_link(version_id)
            except Exception:
                pass

        return {"status": version.parse_status, "version_id": version_id}
    except Exception as exc:
        db.rollback()
        version = db.get(Version, UUID(version_id))
        if version:
            version.parse_status = "failed"
            version.parse_error = str(exc)[:2000]
            db.commit()
        raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
    finally:
        db.close()


# Bridge Redis list queue from PAL enqueue to Celery (dev mode)
@celery_app.task(name="parser.worker.poll_redis_bridge")
def poll_redis_bridge() -> None:
    """Optional: PAL lpush uses raw JSON; Celery expects its protocol. API uses Celery send in production."""
    pass
