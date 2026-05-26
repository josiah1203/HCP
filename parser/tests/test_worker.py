from __future__ import annotations

from parser.worker import parse_object


def test_parse_object_retry_policy():
    assert parse_object.max_retries == 3
