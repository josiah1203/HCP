from __future__ import annotations

import os
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError

from infra.pal.interfaces.storage import StorageProvider


class S3StorageProvider(StorageProvider):
    """AWS S3 object storage via default credential chain (IAM role, env, profile)."""

    def __init__(self, bucket: str, region: str = "us-east-1") -> None:
        self.bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    @classmethod
    def from_env(cls) -> "S3StorageProvider":
        bucket = os.environ.get("AWS_S3_BUCKET") or os.environ["HCP_S3_BUCKET"]
        region = os.environ.get(
            "AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )
        return cls(bucket=bucket, region=region)

    def _put_extra(self) -> dict[str, str]:
        kms_key = os.environ.get("AWS_S3_KMS_KEY_ID")
        if kms_key:
            return {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": kms_key}
        return {"ServerSideEncryption": "AES256"}

    def upload(self, key: str, data: BinaryIO, content_type: str) -> str:
        body = data.read()
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            **self._put_extra(),
        )
        return key

    def download(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def generate_presigned_url(self, key: str, expiry_seconds: int) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=key)

    def ping(self) -> bool:
        try:
            self._client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False
