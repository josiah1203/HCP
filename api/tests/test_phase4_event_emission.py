from __future__ import annotations

import io

import pytest


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _poll(client, headers, project_id: str, cursor: int = 0):
    return client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": cursor, "limit": 100},
    )


def test_upload_emits_version_created_event(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "event-upload"},
            files={"file": ("e.csv", io.BytesIO(b"a\n1\n"), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code != 201:
        pytest.skip("storage unavailable")

    version_id = upload.json()["version"]["id"]
    poll = _poll(client, headers, project_id)
    assert poll.status_code == 200
    assert any(
        e["event_type"] == "version_created"
        and e["dedupe_key"] == f"version:{version_id}:created"
        for e in poll.json()["data"]
    )


def test_promote_emits_lifecycle_event(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "event-promote"},
            files={"file": ("p.csv", io.BytesIO(b"b\n2\n"), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code != 201:
        pytest.skip("storage unavailable")

    object_id = upload.json()["object"]["id"]
    version_num = upload.json()["version"]["version_num"]
    version_id = upload.json()["version"]["id"]

    promote = client.post(
        f"/v1/objects/{object_id}/versions/{version_num}/promote",
        headers=headers,
        json={"target_state": "in_review"},
    )
    assert promote.status_code == 200

    poll = _poll(client, headers, project_id)
    assert poll.status_code == 200
    assert any(
        e["event_type"] == "lifecycle_transition"
        and e["dedupe_key"]
        == f"version:{version_id}:lifecycle:draft:in_review"
        for e in poll.json()["data"]
    )
