from __future__ import annotations
from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProvider(ABC):
    @abstractmethod
    def upload(self, key: str, data: BinaryIO, content_type: str) -> str:
        """Upload object. Returns canonical storage key."""

    @abstractmethod
    def download(self, key: str) -> bytes:
        """Download object bytes by key."""

    @abstractmethod
    def generate_presigned_url(self, key: str, expiry_seconds: int) -> str:
        """Generate a time-limited download URL."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if object exists."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete object (test cleanup only — never in production)."""
