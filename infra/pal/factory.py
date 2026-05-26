from __future__ import annotations
import os

from infra.pal.interfaces.queue import QueueProvider
from infra.pal.interfaces.secrets import SecretsProvider
from infra.pal.interfaces.storage import StorageProvider
from infra.pal.providers.onprem.queue import RedisQueueProvider
from infra.pal.providers.onprem.secrets import EnvSecretsProvider
from infra.pal.providers.onprem.storage import MinioStorageProvider

_ONPREM_PROVIDERS = frozenset({"onprem", "onprem-compose"})
_AWS_PROVIDER = "aws"


def _provider_name() -> str:
    return os.environ.get("HCP_PROVIDER", "onprem-compose").lower()


def get_storage_provider() -> StorageProvider:
    name = _provider_name()
    if name in _ONPREM_PROVIDERS:
        return MinioStorageProvider.from_env()
    if name == _AWS_PROVIDER:
        from infra.pal.providers.aws.storage import S3StorageProvider

        return S3StorageProvider.from_env()
    raise ValueError(f"Unsupported HCP_PROVIDER for storage: {name}")


def get_secrets_provider() -> SecretsProvider:
    name = _provider_name()
    if name in _ONPREM_PROVIDERS:
        return EnvSecretsProvider()
    raise ValueError(f"Unsupported HCP_PROVIDER for secrets: {name}")


def get_queue_provider() -> QueueProvider:
    name = _provider_name()
    if name in _ONPREM_PROVIDERS:
        return RedisQueueProvider.from_env()
    raise ValueError(f"Unsupported HCP_PROVIDER for queue: {name}")
