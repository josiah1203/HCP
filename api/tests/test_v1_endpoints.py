from __future__ import annotations
import io
import uuid

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


def test_auth_refresh_logout_api_keys(client):
    login = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert login.status_code == 200
    body = login.json()
    assert "refresh_token" in body
    refresh = client.post(
        "/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert refresh.status_code == 200
    assert "access_token" in refresh.json()

    logout = client.post(
        "/v1/auth/logout", json={"refresh_token": body["refresh_token"]}
    )
    assert logout.status_code == 204

    key_create = client.post(
        "/v1/auth/api-keys",
        headers=_auth(body["access_token"]),
        json={"name": "ci-key"},
    )
    assert key_create.status_code == 201
    key_body = key_create.json()
    assert key_body["key"].startswith("hcp_test_")

    keys = client.get("/v1/auth/api-keys", headers=_auth(body["access_token"]))
    assert keys.status_code == 200
    assert len(keys.json()["data"]) >= 1

    delete = client.delete(
        f"/v1/auth/api-keys/{key_body['key_id']}",
        headers=_auth(body["access_token"]),
    )
    assert delete.status_code == 204


def test_unauthorized_and_forbidden(client):
    assert client.get("/v1/auth/me").status_code == 401
    assert client.get("/v1/projects").status_code == 401

    token = _login(client)
    resp = client.get(
        "/v1/objects/00000000-0000-0000-0000-000000000099", headers=_auth(token)
    )
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_projects_crud_and_tree(client):
    token = _login(client)
    headers = _auth(token)

    create = client.post(
        "/v1/projects", headers=headers, json={"name": f"p-{uuid.uuid4().hex[:6]}"}
    )
    assert create.status_code == 201
    project_id = create.json()["id"]

    tree = client.get(f"/v1/projects/{project_id}/tree", headers=headers)
    assert tree.status_code == 200
    assert "objects" in tree.json()

    patch = client.patch(
        f"/v1/projects/{project_id}",
        headers=headers,
        json={"description": "updated"},
    )
    assert patch.status_code == 200


def test_object_lifecycle_and_search(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    try:
        upload = client.post(
            "/v1/objects/upload",
            headers=headers,
            data={
                "project_id": project_id,
                "name": "bom-test",
                "description": "test",
            },
            files={
                "file": ("test.csv", io.BytesIO(b"ref,mpn\nR1,LM358\n"), "text/csv")
            },
        )
    except Exception:
        pytest.skip("storage unavailable")
    if upload.status_code not in (201,):
        pytest.skip("storage unavailable")
    object_id = upload.json()["object"]["id"]
    version_num = upload.json()["version"]["version_num"]

    promote = client.post(
        f"/v1/objects/{object_id}/versions/{version_num}/promote",
        headers=headers,
        json={"target_state": "in_review"},
    )
    assert promote.status_code == 200
    assert promote.json()["lifecycle_state"] == "in_review"

    search = client.get("/v1/search", headers=headers, params={"q": "bom"})
    assert search.status_code == 200
    assert "facets" in search.json()

    bom = client.get(f"/v1/bom/{object_id}", headers=headers)
    assert bom.status_code == 200


def test_graph_link_and_query(client):
    token = _login(client)
    headers = _auth(token)

    obj_a = uuid.uuid4()
    obj_b = uuid.uuid4()
    try:
        link = client.post(
            "/v1/graph/link",
            headers=headers,
            json={
                "from_object_id": str(obj_a),
                "to_object_id": str(obj_b),
                "relationship_type": "USES",
            },
        )
    except Exception:
        pytest.skip("graph/storage unavailable")
    assert link.status_code in (404, 201)
    if link.status_code == 201:
        rel_id = link.json()["relationship_id"]
        delete = client.delete(f"/v1/graph/link/{rel_id}", headers=headers)
        assert delete.status_code == 204

    bad_query = client.post(
        "/v1/graph/query",
        headers=headers,
        json={"cypher": "CREATE (n) RETURN n"},
    )
    assert bad_query.status_code == 422

    ok_query = client.post(
        "/v1/graph/query",
        headers=headers,
        json={
            "cypher": "MATCH (n) WHERE n.org_id = $org_id RETURN n LIMIT 1",
            "params": {"org_id": str(client.test_org.id)},
        },
    )
    assert ok_query.status_code == 200


def test_parts_endpoints(client):
    token = _login(client)
    headers = _auth(token)

    get_part = client.get("/v1/parts/LM358", headers=headers)
    assert get_part.status_code == 200

    search = client.get("/v1/parts/search", headers=headers, params={"q": "LM"})
    assert search.status_code == 200


def test_error_schema_has_request_id(client):
    resp = client.get("/v1/auth/me")
    assert resp.status_code == 401
    assert "error" in resp.json()
    assert resp.json()["error"]["code"] == "unauthorized"
    assert resp.headers.get("X-Request-Id")
