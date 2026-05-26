from __future__ import annotations
import os

from infra.pal.interfaces.secrets import SecretsProvider


class EnvSecretsProvider(SecretsProvider):
    """On-prem simple mode: secrets from environment variables."""

    def get_secret(self, secret_name: str) -> str:
        env_key = secret_name.upper().replace("/", "_").replace("-", "_")
        if env_key in os.environ:
            return os.environ[env_key]
        if secret_name in os.environ:
            return os.environ[secret_name]
        raise KeyError(f"Secret not found in environment: {secret_name}")

    def list_secrets(self, prefix: str) -> list[str]:
        prefix_upper = prefix.upper()
        return sorted(
            k for k in os.environ if k.startswith(prefix_upper) or k.startswith(prefix)
        )
