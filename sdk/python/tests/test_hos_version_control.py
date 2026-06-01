from __future__ import annotations

import uuid

import httpx
import pytest
import respx

from hcp import Client

BASE = "https://api.test.hcp.io"
API_KEY = "hcp_test_key"


@pytest.fixture
def client() -> Client:
    return Client(api_key=API_KEY, api_url=BASE)


@respx.mock
def test_hos_branch_commit_diff(client: Client) -> None:
    project_id = str(uuid.uuid4())
    branch_id = str(uuid.uuid4())
    commit_id = str(uuid.uuid4())

    respx.post(f"{BASE}/v1/hos/branches").mock(
        return_value=httpx.Response(201, json={"id": branch_id, "name": "main"})
    )
    respx.post(f"{BASE}/v1/hos/commits").mock(
        return_value=httpx.Response(201, json={"id": commit_id, "message": "init"})
    )
    respx.post(f"{BASE}/v1/hos/diff").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    branch = client.hos.create_branch(project_id=project_id, name="main")
    assert branch["id"] == branch_id

    commit = client.hos.commit(
        project_id=project_id,
        branch_id=branch_id,
        message="init",
        tree={},
    )
    assert commit["id"] == commit_id

    diff = client.hos.diff(
        project_id=project_id,
        from_commit_id=commit_id,
        to_commit_id=commit_id,
    )
    assert diff["data"] == []
