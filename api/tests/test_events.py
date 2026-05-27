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


def test_events_poll_emits_hos_commit_created(client):
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

    commit = client.post(
        "/v1/hos/commits",
        headers=headers,
        json={
            "project_id": project_id,
            "branch_id": main_branch_id,
            "message": "init",
            "tree": {"schematic.kicad_sch": {"object_id": project_id, "version_num": 1}},
        },
    )
    assert commit.status_code == 201
    commit_id = commit.json()["id"]

    poll = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": 0, "limit": 50},
    )
    assert poll.status_code == 200
    body = poll.json()
    items = body["data"]
    assert any(
        e["event_type"] == "commit_created" and e["dedupe_key"] == f"commit:{commit_id}"
        for e in items
    )


def test_events_poll_cursor_and_idempotent_publish(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    publish1 = client.post(
        "/v1/events/publish",
        headers=headers,
        json={
            "project_id": project_id,
            "event_type": "parse_complete",
            "dedupe_key": "version:deadbeef:parse_complete",
            "metadata": {"ok": True},
        },
    )
    assert publish1.status_code == 201
    e1 = publish1.json()["event"]

    publish2 = client.post(
        "/v1/events/publish",
        headers=headers,
        json={
            "project_id": project_id,
            "event_type": "parse_complete",
            "dedupe_key": "version:deadbeef:parse_complete",
            "metadata": {"ok": True},
        },
    )
    assert publish2.status_code == 201
    assert publish2.json()["deduped"] is True
    e2 = publish2.json()["event"]
    assert e1["event_id"] == e2["event_id"]
    assert e1["seq"] == e2["seq"]

    poll1 = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": 0, "limit": 1},
    )
    assert poll1.status_code == 200
    body1 = poll1.json()
    assert len(body1["data"]) == 1
    next_cursor = body1["next_cursor"]

    poll2 = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": next_cursor, "limit": 10},
    )
    assert poll2.status_code == 200
    assert all(e["seq"] > next_cursor for e in poll2.json()["data"])

