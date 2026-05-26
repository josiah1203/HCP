from __future__ import annotations

import os
from io import BytesIO

import boto3
import pytest
from moto import mock_aws

from infra.pal.providers.aws.storage import S3StorageProvider

pytest.importorskip("moto")


@pytest.fixture
def aws_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("HCP_S3_BUCKET", "hcp-test-bucket")


@mock_aws
def test_s3_upload_download_roundtrip(aws_env: None) -> None:
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="hcp-test-bucket")
    storage = S3StorageProvider.from_env()
    key = "org-1/proj-1/obj-1/v1/raw/board.kicad_pcb"
    data = b"(kicad_pcb (version 20240108))"
    storage.upload(key, BytesIO(data), "application/octet-stream")
    assert storage.exists(key)
    assert storage.download(key) == data
    url = storage.generate_presigned_url(key, 900)
    assert "hcp-test-bucket" in url
    storage.delete(key)
    assert not storage.exists(key)


@mock_aws
def test_s3_ping(aws_env: None) -> None:
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="hcp-test-bucket")
    assert S3StorageProvider.from_env().ping()


@mock_aws
def test_factory_aws_provider(aws_env: None) -> None:
    boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="hcp-test-bucket")
    os.environ["HCP_PROVIDER"] = "aws"
    from infra.pal.factory import get_storage_provider

    provider = get_storage_provider()
    assert provider.__class__.__name__ == "S3StorageProvider"
