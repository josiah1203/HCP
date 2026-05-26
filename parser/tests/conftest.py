from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES


def load_fixture(*parts: str) -> bytes:
    path = FIXTURES.joinpath(*parts)
    return path.read_bytes()


@pytest.fixture
def object_ids() -> tuple[str, str]:
    return (
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    )
