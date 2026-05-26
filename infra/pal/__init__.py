"""Provider Abstraction Layer — cloud-agnostic infrastructure interfaces."""

from __future__ import annotations

from infra.pal.factory import (
    get_queue_provider,
    get_secrets_provider,
    get_storage_provider,
)

__all__ = [
    "get_storage_provider",
    "get_secrets_provider",
    "get_queue_provider",
]
