from __future__ import annotations


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_scene_component_identities_nodes_edges_and_snapshot(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    created = client.post(
        "/v1/scene/component-identities",
        headers=headers,
        json={
            "project_id": project_id,
            "canonical_key": "C123",
            "source_tool": "kicad",
            "source_ref": "U1",
            "metadata": {"foo": "bar"},
        },
    )
    assert created.status_code == 201
    identity_id = created.json()["id"]

    got = client.get(
        f"/v1/scene/component-identities/{identity_id}",
        headers=headers,
        params={"project_id": project_id},
    )
    assert got.status_code == 200
    assert got.json()["canonical_key"] == "C123"

    listed = client.get(
        "/v1/scene/component-identities",
        headers=headers,
        params={"project_id": project_id, "limit": 10, "offset": 0},
    )
    assert listed.status_code == 200
    assert any(x["id"] == identity_id for x in listed.json()["data"])

    up_nodes = client.put(
        "/v1/scene/nodes",
        headers=headers,
        json={
            "project_id": project_id,
            "nodes": [
                {
                    "node_key": "node:root",
                    "identity_id": identity_id,
                    "transform": {"t": [0, 0, 0]},
                    "metadata": {"name": "root"},
                }
            ],
        },
    )
    assert up_nodes.status_code == 200
    node_id_1 = up_nodes.json()["data"][0]["id"]

    up_nodes_2 = client.put(
        "/v1/scene/nodes",
        headers=headers,
        json={
            "project_id": project_id,
            "nodes": [
                {
                    "node_key": "node:root",
                    "identity_id": identity_id,
                    "transform": {"t": [1, 2, 3]},
                    "metadata": {"name": "root2"},
                }
            ],
        },
    )
    assert up_nodes_2.status_code == 200
    node_id_2 = up_nodes_2.json()["data"][0]["id"]
    assert node_id_1 == node_id_2
    assert up_nodes_2.json()["data"][0]["transform"]["t"] == [1, 2, 3]

    up_edges = client.put(
        "/v1/scene/edges",
        headers=headers,
        json={
            "project_id": project_id,
            "edges": [
                {
                    "edge_key": "edge:root->root:fixed",
                    "from_node_key": "node:root",
                    "to_node_key": "node:root",
                    "constraint_type": "fixed",
                    "payload": {"k": 1},
                }
            ],
        },
    )
    assert up_edges.status_code == 200
    edge_id_1 = up_edges.json()["data"][0]["id"]

    up_edges_2 = client.put(
        "/v1/scene/edges",
        headers=headers,
        json={
            "project_id": project_id,
            "edges": [
                {
                    "edge_key": "edge:root->root:fixed",
                    "from_node_key": "node:root",
                    "to_node_key": "node:root",
                    "constraint_type": "fixed",
                    "payload": {"k": 2},
                }
            ],
        },
    )
    assert up_edges_2.status_code == 200
    edge_id_2 = up_edges_2.json()["data"][0]["id"]
    assert edge_id_1 == edge_id_2
    assert up_edges_2.json()["data"][0]["payload"]["k"] == 2

    main = client.post(
        "/v1/hos/branches",
        headers=headers,
        json={"project_id": project_id, "name": "main"},
    )
    assert main.status_code == 201
    main_branch_id = main.json()["id"]

    commit = client.post(
        "/v1/hos/commits",
        headers=headers,
        json={
            "project_id": project_id,
            "branch_id": main_branch_id,
            "message": "init",
            "tree": {},
        },
    )
    assert commit.status_code == 201
    commit_id = commit.json()["id"]

    snap1 = client.post(
        "/v1/scene/snapshots",
        headers=headers,
        json={"project_id": project_id, "commit_id": commit_id},
    )
    assert snap1.status_code == 201
    snap_id = snap1.json()["snapshot"]["id"]
    assert snap1.json()["deduped"] is False
    assert "nodes" in snap1.json()["snapshot"]["snapshot"]

    snap2 = client.post(
        "/v1/scene/snapshots",
        headers=headers,
        json={"project_id": project_id, "commit_id": commit_id},
    )
    assert snap2.status_code == 201
    assert snap2.json()["snapshot"]["id"] == snap_id
    assert snap2.json()["deduped"] is True

    log = client.get(
        "/v1/hos/log",
        headers=headers,
        params={"project_id": project_id, "branch_id": main_branch_id, "limit": 50},
    )
    assert log.status_code == 200
    commits = log.json()["data"]
    item = next(c for c in commits if c["id"] == commit_id)
    tree = item["tree"]
    assert tree.get("scene_graph_snapshot", {}).get("snapshot_id") == snap_id

    poll = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": 0, "limit": 200},
    )
    assert poll.status_code == 200
    items = poll.json()["data"]
    assert any(
        e["event_type"] == "scene_graph_snapshot_created"
        and e["dedupe_key"] == f"scene_graph_snapshot:{commit_id}"
        for e in items
    )

