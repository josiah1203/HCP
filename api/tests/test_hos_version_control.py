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


def test_hos_branch_commit_diff_merge_conflicts(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    main = client.post(
        "/v1/hos/branches",
        headers=headers,
        json={"project_id": project_id, "name": "main"},
    )
    assert main.status_code == 201
    main_branch_id = main.json()["id"]

    feature = client.post(
        "/v1/hos/branches",
        headers=headers,
        json={"project_id": project_id, "name": "feature"},
    )
    assert feature.status_code == 201
    feature_branch_id = feature.json()["id"]

    c1 = client.post(
        "/v1/hos/commits",
        headers=headers,
        json={
            "project_id": project_id,
            "branch_id": main_branch_id,
            "message": "init",
            "tree": {"schematic.kicad_sch": {"object_id": str(uuid.uuid4()), "version_num": 1}},
        },
    )
    assert c1.status_code == 201
    commit_main_1 = c1.json()["id"]

    c2 = client.post(
        "/v1/hos/commits",
        headers=headers,
        json={
            "project_id": project_id,
            "branch_id": feature_branch_id,
            "message": "edit on feature",
            "tree": {"schematic.kicad_sch": {"object_id": str(uuid.uuid4()), "version_num": 2}},
        },
    )
    assert c2.status_code == 201
    commit_feature_1 = c2.json()["id"]

    diff = client.post(
        "/v1/hos/diff",
        headers=headers,
        json={
            "project_id": project_id,
            "from_commit_id": commit_main_1,
            "to_commit_id": commit_feature_1,
        },
    )
    assert diff.status_code == 200
    assert diff.json()["data"][0]["change_type"] in ("modified", "added")

    merge = client.post(
        "/v1/hos/merge",
        headers=headers,
        json={
            "project_id": project_id,
            "target_branch_id": main_branch_id,
            "source_branch_id": feature_branch_id,
        },
    )
    assert merge.status_code == 201
    merge_body = merge.json()
    assert merge_body["status"] in ("merged", "conflicts")

    if merge_body["status"] == "conflicts":
        conflicts = client.get(
            f"/v1/hos/merges/{merge_body['merge_id']}/conflicts",
            headers=headers,
            params={"project_id": project_id},
        )
        assert conflicts.status_code == 200
        items = conflicts.json()["data"]
        assert len(items) >= 1
        conflict_id = items[0]["id"]

        resolve = client.post(
            f"/v1/hos/conflicts/{conflict_id}/resolve",
            headers=headers,
            params={"project_id": project_id},
            json={"resolution": {"take": "ours"}},
        )
        assert resolve.status_code == 200
        assert resolve.json()["status"] == "resolved"

        branches = client.get(
            "/v1/hos/branches",
            headers=headers,
            params={"project_id": project_id},
        )
        assert branches.status_code == 200
        main_after = next(
            b for b in branches.json()["data"] if b["id"] == main_branch_id
        )
        assert main_after["head_commit_id"] != commit_main_1

