from __future__ import annotations


import pytest


def test_factory_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HCP_PROVIDER", "gcp")
    from infra.pal.factory import get_storage_provider

    with pytest.raises(ValueError, match="Unsupported"):
        get_storage_provider()
