from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from infra.pal.providers.onprem.queue import RedisQueueProvider
from infra.pal.providers.onprem.secrets import EnvSecretsProvider
from infra.pal.providers.onprem.storage import MinioStorageProvider


def _storage_with_mock_client() -> tuple[MinioStorageProvider, MagicMock]:
    client = MagicMock()
    client.head_bucket.return_value = {}
    body_mock = MagicMock()
    body_mock.read.return_value = b"payload"
    client.get_object.return_value = {"Body": body_mock}
    client.generate_presigned_url.return_value = "http://minio/presigned"
    with patch("infra.pal.providers.onprem.storage.boto3.client", return_value=client):
        storage = MinioStorageProvider(
            endpoint="http://minio:9000",
            access_key="hcp",
            secret_key="hcpsecret",
            bucket="hcp-local",
        )
    storage._client = client
    return storage, client


def test_minio_storage_roundtrip_mocked() -> None:
    storage, client = _storage_with_mock_client()
    key = "org/obj/v1/raw/file.kicad_pcb"
    storage.upload(key, BytesIO(b"test"), "application/octet-stream")
    client.put_object.assert_called_once()
    assert storage.exists(key)
    assert storage.download(key) == b"payload"
    assert storage.ping()
    assert "presigned" in storage.generate_presigned_url(key, 60)
    storage.delete(key)
    client.delete_object.assert_called_once()


def test_minio_storage_exists_not_found() -> None:
    storage, client = _storage_with_mock_client()
    err = ClientError({"Error": {"Code": "404"}}, "HeadObject")
    client.head_object.side_effect = err
    assert not storage.exists("missing")


def test_minio_storage_ensure_bucket_creates() -> None:
    client = MagicMock()
    client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404"}}, "HeadBucket"
    )
    with patch("infra.pal.providers.onprem.storage.boto3.client", return_value=client):
        MinioStorageProvider("http://minio:9000", "a", "b", "new-bucket")
    client.create_bucket.assert_called_once()


def test_minio_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "hcp")
    monkeypatch.setenv("MINIO_SECRET_KEY", "secret")
    monkeypatch.setenv("MINIO_BUCKET", "hcp-local")
    with patch(
        "infra.pal.providers.onprem.storage.boto3.client", return_value=MagicMock()
    ):
        storage = MinioStorageProvider.from_env()
    assert storage.bucket == "hcp-local"


def test_env_secrets_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JWT_SECRET", "from-env")
    provider = EnvSecretsProvider()
    assert provider.get_secret("JWT_SECRET") == "from-env"
    assert provider.get_secret("jwt/secret") == "from-env"
    names = provider.list_secrets("JWT")
    assert "JWT_SECRET" in names


def test_env_secrets_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    with pytest.raises(KeyError):
        EnvSecretsProvider().get_secret("missing-secret")


def test_redis_queue_provider() -> None:
    mock_client = MagicMock()
    mock_client.ping.return_value = True

    with patch(
        "infra.pal.providers.onprem.queue.redis.from_url", return_value=mock_client
    ):
        provider = RedisQueueProvider("redis://localhost:6379/0")
        assert provider.ping()
        message_id = provider.enqueue("parse", {"job": 1})
        assert message_id
        mock_client.lpush.assert_called_once()


def test_redis_queue_ping_failure() -> None:
    mock_client = MagicMock()
    mock_client.ping.side_effect = __import__("redis").RedisError("down")
    with patch(
        "infra.pal.providers.onprem.queue.redis.from_url", return_value=mock_client
    ):
        assert not RedisQueueProvider("redis://localhost:6379/0").ping()
