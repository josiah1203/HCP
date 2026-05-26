from __future__ import annotations
import os
from io import BytesIO

import pytest

from infra.pal.providers.onprem.storage import MinioStorageProvider

pytestmark = pytest.mark.skipif(
    os.environ.get("MINIO_ENDPOINT") is None,
    reason="MINIO_ENDPOINT not set — run with docker compose or set env",
)


@pytest.fixture
def storage() -> MinioStorageProvider:
    return MinioStorageProvider.from_env()


def test_upload_download_roundtrip(storage: MinioStorageProvider) -> None:
    key = "test-org/test-project/test-object/v1/raw/board.kicad_pcb"
    data = b"(kicad_pcb (version 20240108))"
    storage.upload(key, BytesIO(data), "application/octet-stream")
    assert storage.exists(key)
    assert storage.download(key) == data
    storage.delete(key)
    assert not storage.exists(key)
