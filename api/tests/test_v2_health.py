from __future__ import annotations


def test_v2_health(client):
    response = client.get("/v2/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["api_version"] == "2"
