from __future__ import annotations

import uuid

import httpx
import pytest
import respx

from hcp import Client
from hcp.exceptions import AuthenticationError, NotFoundError, ParseTimeoutError

BASE = "https://api.test.hcp.io"
API_KEY = "hcp_test_key"


@pytest.fixture
def client() -> Client:
    return Client(api_key=API_KEY, api_url=BASE)


@respx.mock
def test_projects_create(client: Client) -> None:
    project_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/projects").mock(
        return_value=httpx.Response(201, json={"id": project_id, "name": "Rev C"})
    )
    result = client.projects.create("Rev C")
    assert result["name"] == "Rev C"


@respx.mock
def test_projects_list(client: Client) -> None:
    respx.get(f"{BASE}/v1/projects").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "1", "name": "A"}]})
    )
    projects = client.projects.list()
    assert len(projects) == 1


@respx.mock
def test_projects_get(client: Client) -> None:
    pid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/projects/{pid}").mock(
        return_value=httpx.Response(200, json={"id": pid, "name": "P"})
    )
    assert client.projects.get(pid)["name"] == "P"


@respx.mock
def test_objects_get(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/objects/{oid}").mock(
        return_value=httpx.Response(
            200,
            json={"id": oid, "name": "board", "object_type": "PCB"},
        )
    )
    obj = client.objects.get(oid)
    assert obj["object_type"] == "PCB"


@respx.mock
def test_objects_list_versions(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/objects/{oid}/versions").mock(
        return_value=httpx.Response(200, json={"data": [{"version_num": 1}]})
    )
    versions = client.objects.list_versions(oid)
    assert versions[0]["version_num"] == 1


@respx.mock
def test_objects_upload(client: Client, tmp_path) -> None:
    f = tmp_path / "board.kicad_pcb"
    f.write_text("(kicad_pcb)")

    respx.post(f"{BASE}/v1/objects/upload").mock(
        return_value=httpx.Response(
            201,
            json={
                "object": {"id": "obj-1", "name": "board"},
                "version": {"version_num": 1, "parse_status": "pending"},
                "deduplicated": False,
            },
        )
    )
    result = client.objects.upload(str(f), project_id="proj-1", name="board")
    assert result["object"]["id"] == "obj-1"


@respx.mock
def test_objects_upload_wait_parse(client: Client, tmp_path) -> None:
    f = tmp_path / "bom.csv"
    f.write_text("ref,mpn\nR1,10k")

    respx.post(f"{BASE}/v1/objects/upload").mock(
        return_value=httpx.Response(
            201,
            json={
                "object": {"id": "obj-2", "name": "bom"},
                "version": {"version_num": 1, "parse_status": "pending"},
                "deduplicated": False,
            },
        )
    )
    route = respx.get(f"{BASE}/v1/objects/obj-2/versions/1")
    route.side_effect = [
        httpx.Response(200, json={"version_num": 1, "parse_status": "pending"}),
        httpx.Response(200, json={"version_num": 1, "parse_status": "complete"}),
    ]

    result = client.objects.upload(
        str(f), project_id="proj-1", name="bom", wait_for_parse=True, parse_timeout=10
    )
    assert result["version"]["parse_status"] == "complete"


@respx.mock
def test_bom_get(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/bom/{oid}").mock(
        return_value=httpx.Response(200, json={"lines": [{"ref": "R1"}]})
    )
    bom = client.bom.get(oid)
    assert bom["lines"][0]["ref"] == "R1"


@respx.mock
def test_bom_flat(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/bom/{oid}/flat").mock(
        return_value=httpx.Response(200, json={"lines": []})
    )
    assert client.bom.flat(oid)["lines"] == []


@respx.mock
def test_bom_diff(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/bom/{oid}/diff/1/2").mock(
        return_value=httpx.Response(200, json={"added": [], "removed": []})
    )
    diff = client.bom.diff(oid, 1, 2)
    assert "added" in diff


@respx.mock
def test_graph_dependencies(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/graph/{oid}/dependencies").mock(
        return_value=httpx.Response(200, json={"nodes": [], "edges": []})
    )
    deps = client.graph.dependencies(oid, depth=2)
    assert deps["nodes"] == []


@respx.mock
def test_graph_dependents(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/graph/{oid}/dependents").mock(
        return_value=httpx.Response(200, json={"nodes": [], "edges": []})
    )
    assert client.graph.dependents(oid)["nodes"] == []


@respx.mock
def test_graph_link(client: Client) -> None:
    respx.post(f"{BASE}/v1/graph/link").mock(
        return_value=httpx.Response(201, json={"id": "rel-1"})
    )
    rel = client.graph.link("a", "VALIDATES", "b")
    assert rel["id"] == "rel-1"


@respx.mock
def test_search_query(client: Client) -> None:
    respx.get(f"{BASE}/v1/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"id": "1", "name": "STM32 board"}],
                "pagination": {"page": 1, "total": 1},
                "facets": {"types": ["PCB"]},
            },
        )
    )
    results = client.search.query("STM32", type="PCB", state="released")
    assert results["data"][0]["name"] == "STM32 board"


@respx.mock
def test_auth_error(client: Client) -> None:
    respx.get(f"{BASE}/v1/projects").mock(
        return_value=httpx.Response(
            401,
            json={"error": {"code": "unauthorized", "message": "Invalid token"}},
        )
    )
    with pytest.raises(AuthenticationError):
        client.projects.list()


@respx.mock
def test_not_found(client: Client) -> None:
    oid = str(uuid.uuid4())
    respx.get(f"{BASE}/v1/objects/{oid}").mock(
        return_value=httpx.Response(
            404,
            json={"error": {"code": "not_found", "message": "Object not found"}},
        )
    )
    with pytest.raises(NotFoundError):
        client.objects.get(oid)


@respx.mock
def test_parse_timeout(client: Client, tmp_path) -> None:
    f = tmp_path / "slow.step"
    f.write_bytes(b"STEP")

    respx.post(f"{BASE}/v1/objects/upload").mock(
        return_value=httpx.Response(
            201,
            json={
                "object": {"id": "obj-3"},
                "version": {"version_num": 1, "parse_status": "pending"},
            },
        )
    )
    respx.get(f"{BASE}/v1/objects/obj-3/versions/1").mock(
        return_value=httpx.Response(200, json={"parse_status": "pending"})
    )

    with pytest.raises(ParseTimeoutError):
        client.objects.upload(
            str(f),
            project_id="p",
            name="slow",
            wait_for_parse=True,
            parse_timeout=0.1,
        )


@respx.mock
def test_exceptions_hierarchy() -> None:
    from hcp.exceptions import HCPError, ServerError

    assert issubclass(AuthenticationError, HCPError)
    assert issubclass(ServerError, HCPError)
