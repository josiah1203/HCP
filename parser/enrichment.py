"""Octopart enrichment trigger — enqueue one task per unique MPN (V1 stub)."""

from __future__ import annotations

import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)

_ENRICHMENT_HANDLER: Callable[[str, str], None] | None = None


def set_enrichment_handler(handler: Callable[[str, str], None] | None) -> None:
    """Test hook to replace Celery enqueue."""
    global _ENRICHMENT_HANDLER  # noqa: PLW0603
    _ENRICHMENT_HANDLER = handler


def enqueue_octopart_enrichment(mpns: list[str], version_id: str) -> None:
    """Enqueue Octopart lookup per unique MPN. Batched in production; stub logs in dev."""
    unique = sorted({m.strip() for m in mpns if m and m.strip()})
    if not unique:
        return

    if _ENRICHMENT_HANDLER is not None:
        for mpn in unique:
            _ENRICHMENT_HANDLER(mpn, version_id)
        return

    if os.environ.get("HCP_OCTOPART_DISABLED", "").lower() in ("1", "true", "yes"):
        logger.debug("octopart enrichment disabled for %d MPNs", len(unique))
        return

    try:
        from celery import current_app  # noqa: PLC0415

        task_name = "graph.worker.enrich_part"
        for mpn in unique:
            current_app.send_task(
                task_name,
                kwargs={"mpn": mpn, "version_id": version_id},
                queue="hcp.enrich",
            )
    except Exception:
        logger.info(
            "octopart enrichment stub: version=%s mpns=%s",
            version_id,
            unique,
            extra={"mpn_count": len(unique)},
        )
