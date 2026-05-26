from __future__ import annotations
from celery import Celery

from app.config import settings

_celery: Celery | None = None


def get_celery() -> Celery:
    global _celery
    if _celery is None:
        _celery = Celery(
            "hcp_api", broker=settings.redis_url, backend=settings.redis_url
        )
        _celery.conf.task_default_queue = settings.parse_queue_name
    return _celery


def enqueue_parse(version_id: str, context: dict | None = None) -> str:
    kwargs: dict = {}
    if context:
        kwargs["parse_context"] = context
    result = get_celery().send_task(
        "parser.worker.parse_object",
        args=[version_id],
        kwargs=kwargs,
        queue=settings.parse_queue_name,
    )
    return result.id


def enqueue_auto_link(version_id: str) -> str:
    result = get_celery().send_task(
        "graph.tasks.auto_link_version",
        args=[version_id],
        queue=settings.graph_queue_name,
    )
    return result.id
