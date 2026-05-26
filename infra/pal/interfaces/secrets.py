from __future__ import annotations
from abc import ABC, abstractmethod


class SecretsProvider(ABC):
    @abstractmethod
    def get_secret(self, secret_name: str) -> str:
        """Retrieve secret value by name."""

    @abstractmethod
    def list_secrets(self, prefix: str) -> list[str]:
        """List secret names matching a prefix."""
