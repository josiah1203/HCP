from __future__ import annotations

import uuid

from app.auth.dependencies import hash_password
from app.models.db import User
from app.services.event_emission import heartbeat_bucket_ts, presence_heartbeat_dedupe_key
from app.services.events import deterministic_event_id


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_presence_heartbeat_list_and_events(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    session_id = f"sess-{uuid.uuid4().hex[:8]}"

    hb = client.post(
        "/v1/collaboration/presence/heartbeat",
        headers=headers,
        json={
            "project_id": project_id,
            "session_id": session_id,
            "resource_path": "schematic/main.kicad_sch",
            "domain": "electrical",
        },
    )
    assert hb.status_code == 200
    body = hb.json()
    assert body["joined"] is True
    assert body["presence"]["session_id"] == session_id

    listed = client.get(
        "/v1/collaboration/presence",
        headers=headers,
        params={"project_id": project_id},
    )
    assert listed.status_code == 200
    assert any(p["session_id"] == session_id for p in listed.json()["data"])

    poll = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": 0, "limit": 50},
    )
    assert poll.status_code == 200
    types = {e["event_type"] for e in poll.json()["data"]}
    assert "presence_joined" in types
    assert "presence_heartbeat" in types


def test_presence_heartbeat_event_idempotency(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    session_id = f"sess-{uuid.uuid4().hex[:8]}"
    bucket = heartbeat_bucket_ts()
    dedupe = presence_heartbeat_dedupe_key(session_id, bucket)
    expected_id = str(
        deterministic_event_id(
            org_id=client.test_org.id,
            project_id=client.test_project.id,
            event_type="presence_heartbeat",
            dedupe_key=dedupe,
        )
    )

    for _ in range(2):
        client.post(
            "/v1/collaboration/presence/heartbeat",
            headers=headers,
            json={"project_id": project_id, "session_id": session_id},
        )

    publish = client.post(
        "/v1/events/publish",
        headers=headers,
        json={
            "project_id": project_id,
            "event_type": "presence_heartbeat",
            "dedupe_key": dedupe,
            "metadata": {"session_id": session_id},
        },
    )
    assert publish.status_code == 201
    assert publish.json()["deduped"] is True
    assert publish.json()["event"]["event_id"] == expected_id


def test_soft_lock_advisory_when_held_by_other(client, db_session):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    resource = "pcb/layout.kicad_pcb"

    first = client.post(
        "/v1/collaboration/locks/acquire",
        headers=headers,
        json={"project_id": project_id, "resource_path": resource, "session_id": "a"},
    )
    assert first.status_code == 200
    assert first.json()["acquired"] is True

    other = User(
        org_id=client.test_org.id,
        email=f"other-{uuid.uuid4().hex[:8]}@hcp.test",
        name="Other",
        password_hash=hash_password("testpass"),
        role="editor",
    )
    db_session.add(other)
    db_session.commit()

    other_login = client.post(
        "/v1/auth/login",
        json={"email": other.email, "password": "testpass"},
    )
    assert other_login.status_code == 200
    other_headers = _auth(other_login.json()["access_token"])

    second = client.post(
        "/v1/collaboration/locks/acquire",
        headers=other_headers,
        json={"project_id": project_id, "resource_path": resource, "session_id": "b"},
    )
    assert second.status_code == 200
    assert second.json()["acquired"] is False
    assert second.json()["held_by_other"] is True


def test_unknown_event_type_rejected(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    resp = client.post(
        "/v1/events/publish",
        headers=headers,
        json={
            "project_id": project_id,
            "event_type": "not_a_real_event",
            "dedupe_key": "x:1",
        },
    )
    assert resp.status_code == 422


def test_crdt_operation_idempotent(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    op_id = f"op-{uuid.uuid4().hex[:8]}"
    payload = {
        "project_id": project_id,
        "document_id": "doc-1",
        "operation_id": op_id,
        "envelope": {"op_type": "insert", "payload": {"path": "/a"}},
    }

    r1 = client.post("/v1/collaboration/crdt/operations", headers=headers, json=payload)
    assert r1.status_code == 201
    assert r1.json()["accepted"] is True

    r2 = client.post("/v1/collaboration/crdt/operations", headers=headers, json=payload)
    assert r2.status_code == 201
    assert r2.json()["accepted"] is False


def test_cross_domain_alert_event(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    alert_id = f"alert-{uuid.uuid4().hex[:8]}"

    resp = client.post(
        "/v1/collaboration/alerts",
        headers=headers,
        json={
            "project_id": project_id,
            "alert_id": alert_id,
            "source_domain": "electrical",
            "target_domain": "mechanical",
            "severity": "warning",
            "message": "Board outline changed",
        },
    )
    assert resp.status_code == 201

    poll = client.get(
        "/v1/events/poll",
        headers=headers,
        params={"project_id": project_id, "cursor": 0, "limit": 100},
    )
    assert any(
        e["event_type"] == "cross_domain_alert" and e["dedupe_key"] == f"alert:{alert_id}"
        for e in poll.json()["data"]
    )

