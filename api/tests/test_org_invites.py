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


def test_register_org_and_accept_invite(client):
    suffix = uuid.uuid4().hex[:8]
    register = client.post(
        "/v1/orgs/register",
        json={
            "org_name": f"Acme {suffix}",
            "admin_name": "Admin User",
            "admin_email": f"admin-{suffix}@acme.test",
            "admin_password": "securepass1",
        },
    )
    assert register.status_code == 201, register.text
    admin_token = register.json()["access_token"]

    invite = client.post(
        "/v1/orgs/invites",
        headers=_auth(admin_token),
        json={"email": f"editor-{suffix}@acme.test", "role": "editor"},
    )
    assert invite.status_code == 201, invite.text
    invite_token = invite.json()["invite_token"]

    accept = client.post(
        "/v1/orgs/invites/accept",
        json={
            "token": invite_token,
            "name": "Editor User",
            "password": "securepass2",
            "email": f"editor-{suffix}@acme.test",
        },
    )
    assert accept.status_code == 200, accept.text
    assert accept.json()["user"]["role"] == "editor"

    login = client.post(
        "/v1/auth/login",
        json={
            "email": f"editor-{suffix}@acme.test",
            "password": "securepass2",
        },
    )
    assert login.status_code == 200


def test_invite_requires_admin_role(client, db_session):
    from app.auth.dependencies import hash_password
    from app.models.db import User

    suffix = uuid.uuid4().hex[:8]
    editor = User(
        org_id=client.test_org.id,
        email=f"ed-{suffix}@hcp.test",
        name="Editor",
        password_hash=hash_password("testpass"),
        role="editor",
    )
    db_session.add(editor)
    db_session.commit()

    login = client.post(
        "/v1/auth/login",
        json={"email": editor.email, "password": "testpass"},
    )
    token = login.json()["access_token"]

    resp = client.post(
        "/v1/orgs/invites",
        headers=_auth(token),
        json={"email": f"new-{suffix}@hcp.test", "role": "viewer"},
    )
    assert resp.status_code == 403
