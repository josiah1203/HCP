from __future__ import annotations

import json
import uuid
from pathlib import Path

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
def test_hos_read_commit_tree(client: Client) -> None:
    tree_id = "tree-123"
    respx.get(f"{BASE}/v1/hos/trees/{tree_id}").mock(
        return_value=httpx.Response(200, json={"tree_id": tree_id, "entries": []})
    )
    result = client.hos.read_commit_tree(tree_id)
    assert result["tree_id"] == tree_id


@respx.mock
def test_hos_write_commit_tree(client: Client) -> None:
    tree_id = "tree-abc"
    entries = [{"path": "board.kicad_pcb", "kind": "blob", "objectId": "o1", "versionNum": 1}]
    respx.post(f"{BASE}/v1/hos/trees/{tree_id}").mock(
        return_value=httpx.Response(201, json={"tree_id": tree_id})
    )
    result = client.hos.write_commit_tree(tree_id, entries=entries)
    assert result["tree_id"] == tree_id


@respx.mock
def test_hos_upsert_scene_graph(client: Client) -> None:
    commit_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/scene/upsert").mock(
        return_value=httpx.Response(200, json={"nodesUpserted": 1, "edgesUpserted": 0})
    )
    result = client.hos.upsert_scene_graph(commit_id=commit_id, nodes=[{"nodeId": "n1"}], edges=[])
    assert result["nodesUpserted"] == 1


@respx.mock
def test_hos_create_snapshot(client: Client) -> None:
    commit_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/snapshots").mock(
        return_value=httpx.Response(201, json={"snapshotId": "snap-1"})
    )
    result = client.hos.create_snapshot(commit_id=commit_id)
    assert result["snapshotId"] == "snap-1"


@respx.mock
def test_hos_poll_events(client: Client) -> None:
    respx.get(f"{BASE}/v1/events").mock(
        return_value=httpx.Response(200, json={"nextCursor": "c2", "events": []})
    )
    result = client.hos.poll_events(cursor="c1", limit=10)
    assert result["nextCursor"] == "c2"


def test_protocol_json_files_parse() -> None:
    root = Path(__file__).resolve().parents[3]
    paths = [
        root / "docs/protocol/jsonrpc/hcp-ide-sidecar.v0.json",
        root / "docs/protocol/jsonrpc/hcp-sidecar-scenegraph.v0.json",
        root / "docs/protocol/jsonrpc/hcp-hos-client.v0.json",
    ]
    for p in paths:
        payload = json.loads(p.read_text())
        # These files are JSON Schemas describing a protocol, not protocol instances.
        const = (
            payload.get("properties", {})
            .get("protocol", {})
            .get("const")
        )
        assert const == "hcp.rpc.v0"

