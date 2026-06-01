from __future__ import annotations

import uuid


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_commit_with_object_snapshots_and_scene_graph(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    branch = client.post(
        "/v1/hos/branches",
        headers=headers,
        json={"project_id": project_id, "name": "hnf-main"},
    )
    assert branch.status_code == 201
    branch_id = branch.json()["id"]

    obj_id = str(uuid.uuid4())
    commit = client.post(
        "/v1/hos/commits",
        headers=headers,
        json={
            "project_id": project_id,
            "branch_id": branch_id,
            "message": "hnf snapshot commit",
            "tree_root_ref": "schematic.kicad_sch",
            "object_snapshots": [
                {
                    "object_path": "schematic.kicad_sch",
                    "object_id": obj_id,
                    "version_num": 1,
                    "content_hash": "abc123",
                    "hnf_type": "schematic",
                    "domain": "electrical",
                }
            ],
            "create_scene_snapshot": True,
            "scene_snapshot_format": "json",
        },
    )
    assert commit.status_code == 201
    body = commit.json()
    assert body["tree_root_ref"] == "schematic.kicad_sch"
    assert body["tree"]["schematic.kicad_sch"]["hnf_type"] == "schematic"
    commit_id = body["id"]

    listed = client.get(
        f"/v1/hos/commits/{commit_id}/snapshots",
        headers=headers,
        params={"project_id": project_id},
    )
    assert listed.status_code == 200
    snaps = listed.json()["data"]
    assert len(snaps) == 1
    assert snaps[0]["object_path"] == "schematic.kicad_sch"
    assert snaps[0]["hnf_type"] == "schematic"

    snap_resp = client.post(
        "/v1/scene/snapshots",
        headers=headers,
        json={
            "project_id": project_id,
            "commit_id": commit_id,
            "snapshot_format": "json",
        },
    )
    assert snap_resp.status_code == 201
    snapshot = snap_resp.json()["snapshot"]["snapshot"]
    assert snapshot.get("format") == "json"
    assert snapshot.get("protocol") == "hcp.rpc.v0"
    assert "nodes" in snapshot
    assert "rpc" in snapshot
