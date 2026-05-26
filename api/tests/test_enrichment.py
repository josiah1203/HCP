from __future__ import annotations
from datetime import datetime, timedelta, timezone

from app.models.db import Part
from app.services.enrichment import CACHE_TTL_DAYS, _cache_valid, fetch_octopart_stub


def test_cache_valid_within_seven_days() -> None:
    part = Part(
        mpn="TEST-1",
        manufacturer="Acme",
        enriched_at=datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS - 1),
        enrichment_data={"cached": True},
    )
    assert _cache_valid(part) is True


def test_cache_invalid_when_stale() -> None:
    part = Part(
        mpn="TEST-2",
        manufacturer="Acme",
        enriched_at=datetime.now(timezone.utc) - timedelta(days=CACHE_TTL_DAYS + 1),
        enrichment_data={"cached": True},
    )
    assert _cache_valid(part) is False


def test_octopart_stub_payload() -> None:
    payload = fetch_octopart_stub("LM358", "TI")
    assert payload["source"] == "octopart_stub"
    assert payload["mpn"] == "LM358"
