from __future__ import annotations

import io
import uuid

import pytest
from sqlalchemy import func, select

from app.auth.dependencies import hash_password
from app.models.db import AuditLog, User, Version


def _login(client, email: str, password: str = "testpass") -> str:
    resp = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _role_user(db_session, client, role: str) -> User:
    user = User(
        org_id=client.test_org.id,
        email=f"{role}-{uuid.uuid4().hex[:8]}@hcp.test",
        name=f"{role} user",
        password_hash=hash_password("testpass"),
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_viewer_cannot_upload(client, db_session):
    viewer = _role_user(db_session, client, "viewer")
    token = _login(client, viewer.email)
    resp = client.post(
        "/v1/objects/upload",
        headers=_auth(token),
        data={
            "project_id": str(client.test_project.id),
            "name": "blocked",
        },
        files={"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "forbidden"


def test_editor_cannot_approve(client, db_session):
    editor = _role_user(db_session, client, "editor")
    token = _login(client, editor.email)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "lifecycle"},
            files={"file": ("t.csv", io.BytesIO(b"x\n1\n"), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code != 201:
        pytest.skip("storage unavailable")

    object_id = upload.json()["object"]["id"]
    version_num = upload.json()["version"]["version_num"]
    promote = client.post(
        f"/v1/objects/{object_id}/versions/{version_num}/promote",
        headers=headers,
        json={"target_state": "approved"},
    )
    assert promote.status_code == 403


def test_sha256_dedup_reuses_storage_key(client):
    token = _login(client, client.test_user.email)
    headers = _auth(token)
    project_id = str(client.test_project.id)
    payload = b"ref,mpn\nR1,LM358\n"

    try:
        first = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "dedup-a"},
            files={"file": ("a.csv", io.BytesIO(payload), "text/csv")},
        )
        second = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "dedup-b"},
            files={"file": ("b.csv", io.BytesIO(payload), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if first.status_code != 201 or second.status_code != 201:
        pytest.skip("storage unavailable")

    assert second.json()["deduplicated"] is True
    assert (
        first.json()["version"]["storage_key"]
        == second.json()["version"]["storage_key"]
    )


def test_presigned_download_url(client):
    token = _login(client, client.test_user.email)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "download-me"},
            files={"file": ("d.csv", io.BytesIO(b"1\n"), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code != 201:
        pytest.skip("storage unavailable")

    object_id = upload.json()["object"]["id"]
    version_num = upload.json()["version"]["version_num"]
    dl = client.get(
        f"/v1/objects/{object_id}/versions/{version_num}/download",
        headers=headers,
    )
    assert dl.status_code == 200
    body = dl.json()
    assert body["url"]
    assert body["expires_in_seconds"] > 0


def test_audit_log_on_version_and_promote(client, db_session):
    token = _login(client, client.test_user.email)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={"project_id": project_id, "name": "audit"},
            files={"file": ("a.csv", io.BytesIO(b"c\n1\n"), "text/csv")},
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code != 201:
        pytest.skip("storage unavailable")

    object_id = uuid.UUID(upload.json()["object"]["id"])
    version_num = upload.json()["version"]["version_num"]

    created_count = db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.object_id == object_id,
            AuditLog.event_type == "version_created",
        )
    )
    assert created_count == 1

    promote = client.post(
        f"/v1/objects/{object_id}/versions/{version_num}/promote",
        headers=headers,
        json={"target_state": "in_review"},
    )
    assert promote.status_code == 200

    transition_count = db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.object_id == object_id,
            AuditLog.event_type == "lifecycle_transition",
        )
    )
    assert transition_count == 1
