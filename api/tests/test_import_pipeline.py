from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock

import pytest

from app.services.import_pipeline import count_parsed_elements

MINIMAL_KICAD_SCH = b"""(kicad_sch (version 20230121) (generator "test")
  (symbol (lib_id "Device:R") (at 0 0 0)
    (property "Reference" "R1")
    (property "Value" "10k")
  )
  (symbol (lib_id "Device:C") (at 10 0 0)
    (property "Reference" "C1")
    (property "Value" "100nF")
  )
)
"""


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_count_parsed_elements_from_kicad():
    from parser.parsers.kicad_sch import KiCadSchematicParser
    from parser.pral.interfaces.parser_plugin import ParseContext

    parser = KiCadSchematicParser()
    ctx = ParseContext(
        filename="board.kicad_sch",
        object_id="obj",
        version_id="ver",
    )
    parsed = parser.parse(MINIMAL_KICAD_SCH, ctx)
    assert count_parsed_elements(parsed) >= 2


@pytest.fixture(autouse=True)
def _stub_upload_deps(monkeypatch):
    monkeypatch.setattr(
        "app.services.objects.get_storage_provider",
        lambda: _NoopStorage(),
    )
    mock_celery = MagicMock()
    mock_celery.send_task.return_value = MagicMock(id="noop-task")
    monkeypatch.setattr("app.services.tasks.get_celery", lambda: mock_celery)
    monkeypatch.setattr("app.services.objects.enqueue_parse", lambda *_a, **_k: "noop-task")


def test_project_import_kicad_file(client):

    token = _login(client)
    project_id = str(client.test_project.id)

    resp = client.post(
        f"/v1/projects/{project_id}/import",
        headers=_auth(token),
        data={"format": "kicad", "message": "corpus import"},
        files={"file": ("design.kicad_sch", MINIMAL_KICAD_SCH, "application/octet-stream")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["format"] == "kicad"
    assert body["branch_name"].startswith("import/kicad/")
    assert len(body["artifacts"]) == 1
    assert body["metrics"]["source_elements"] >= 2
    assert body["metrics"]["loss_ratio"] < 0.05


def test_project_import_zip(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("proj/main.kicad_sch", MINIMAL_KICAD_SCH)

    token = _login(client)
    project_id = str(client.test_project.id)
    resp = client.post(
        f"/v1/projects/{project_id}/import",
        headers=_auth(token),
        data={"format": "kicad"},
        files={"file": ("bundle.zip", buf.getvalue(), "application/zip")},
    )
    assert resp.status_code == 201
    assert resp.json()["artifacts"][0]["path"] == "proj/main.kicad_sch"


def test_project_import_forbidden_viewer(client, db_session):
    from app.auth.dependencies import hash_password
    from app.models.db import User

    viewer = User(
        org_id=client.test_org.id,
        email=f"viewer-{client.test_user.id}@hcp.test",
        name="Viewer",
        password_hash=hash_password("testpass"),
        role="viewer",
    )
    db_session.add(viewer)
    db_session.commit()

    login = client.post(
        "/v1/auth/login",
        json={"email": viewer.email, "password": "testpass"},
    )
    token = login.json()["access_token"]
    resp = client.post(
        f"/v1/projects/{client.test_project.id}/import",
        headers=_auth(token),
        data={"format": "kicad"},
        files={"file": ("x.kicad_sch", MINIMAL_KICAD_SCH, "application/octet-stream")},
    )
    assert resp.status_code == 403


class _NoopStorage:
    def upload(self, key, stream, content_type):  # noqa: ANN001
        return None

    def presign_get(self, key, expires_seconds=900):  # noqa: ANN001
        return f"https://example.test/{key}"
