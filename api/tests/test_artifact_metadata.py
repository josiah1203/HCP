from __future__ import annotations

import io
import json
import zipfile
from unittest.mock import MagicMock, patch


from app.models.db import HardwareObject, Version
from app.services.bundles import BundleIngestService
from app.services.object_types import (
    infer_domain,
    infer_object_type,
    infer_representation,
)
from app.services.search import SearchParams, SearchService


def _login(client) -> str:
    resp = client.post(
        "/v1/auth/login",
        json={"email": client.test_user.email, "password": "testpass"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_infer_helpers():
    assert infer_representation("board.step") == "interchange"
    assert infer_representation("design.kicad_pcb") == "native"
    assert infer_domain("fab.gbr") == "manufacturing"
    assert infer_domain("assy.step") == "mechanical"
    assert infer_domain("bom.csv", source_tool="KiCad") == "electrical"
    assert infer_object_type("test.csv") == "BOM"
    assert infer_object_type("unknown.xyz", domain="firmware") == "FIRMWARE"


def test_upload_persists_metadata(client, db_session):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    mock_storage = MagicMock()
    with patch("app.services.objects.get_storage_provider", return_value=mock_storage):
        with patch("app.services.objects.enqueue_parse") as mock_enqueue:
            resp = client.post(
                "/v1/objects/upload",
                headers=headers,
                data={
                    "project_id": project_id,
                    "name": "step-assy",
                    "source_tool": "SolidWorks",
                    "source_tool_version": "2024",
                    "domain": "mechanical",
                },
                files={
                    "file": ("assy.step", io.BytesIO(b"ISO-10303-21"), "model/step")
                },
            )

    assert resp.status_code == 201
    body = resp.json()
    assert body["object"]["domain"] == "mechanical"
    assert body["object"]["source_tool"] == "SolidWorks"
    assert body["version"]["representation"] == "interchange"
    assert body["version"]["source_tool"] == "SolidWorks"
    assert body["version"]["source_tool_version"] == "2024"
    mock_enqueue.assert_called_once()
    call_kwargs = mock_enqueue.call_args.kwargs.get(
        "context"
    ) or mock_enqueue.call_args[1].get("context")
    assert call_kwargs["domain"] == "mechanical"
    assert call_kwargs["source_tool"] == "SolidWorks"


def test_upload_infers_domain_from_extension(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    mock_storage = MagicMock()
    with patch("app.services.objects.get_storage_provider", return_value=mock_storage):
        with patch("app.services.objects.enqueue_parse"):
            resp = client.post(
                "/v1/objects/upload",
                headers=headers,
                data={"project_id": project_id, "name": "gerber-top"},
                files={"file": ("top.gtl", io.BytesIO(b"G04*"), "text/plain")},
            )

    assert resp.status_code == 201
    assert resp.json()["object"]["domain"] == "manufacturing"
    assert resp.json()["version"]["representation"] == "interchange"


def test_bundle_ingest_creates_artifacts_and_links(client, db_session):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    manifest = {
        "schema_version": "1.0",
        "source_tool": "SolidWorks",
        "release": "Rev-C",
        "artifacts": [
            {"path": "assy.step", "domain": "mechanical", "role": "assembly"},
            {"path": "bom.csv", "domain": "electrical", "role": "bom"},
        ],
        "relationships": [{"from": "assy.step", "to": "bom.csv", "type": "CONTAINS"}],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("assy.step", b"ISO-10303-21")
        zf.writestr("bom.csv", b"ref,mpn\nR1,LM358\n")
    bundle_bytes = buf.getvalue()

    mock_storage = MagicMock()
    with patch("app.services.objects.get_storage_provider", return_value=mock_storage):
        with patch("app.services.objects.enqueue_parse"):
            with patch.object(
                BundleIngestService, "_apply_relationships", return_value=1
            ) as mock_rels:
                resp = client.post(
                    "/v1/objects/upload-bundle",
                    headers=headers,
                    data={"project_id": project_id, "name": "rev-c-bundle"},
                    files={
                        "file": (
                            "release.zip",
                            io.BytesIO(bundle_bytes),
                            "application/zip",
                        )
                    },
                )

    assert resp.status_code == 201
    body = resp.json()
    assert body["release"] == "Rev-C"
    assert body["source_tool"] == "SolidWorks"
    assert len(body["artifacts"]) == 2
    assert body["relationships_applied"] == 1
    mock_rels.assert_called_once()

    paths = {a["path"] for a in body["artifacts"]}
    assert paths == {"assy.step", "bom.csv"}


def test_search_postgres_facets_include_domain(db_session, client):
    org = client.test_org
    user = client.test_user
    project = client.test_project

    obj = HardwareObject(
        org_id=org.id,
        project_id=project.id,
        name="facet-test",
        object_type="STEP",
        domain="mechanical",
        source_tool="SolidWorks",
        representation="interchange",
        created_by=user.id,
    )
    db_session.add(obj)
    db_session.flush()
    ver = Version(
        org_id=org.id,
        object_id=obj.id,
        version_num=1,
        filename="a.step",
        content_hash="abc",
        file_size_bytes=3,
        storage_key="k",
        parse_status="pending",
        lifecycle_state="draft",
        uploaded_by=user.id,
        domain="mechanical",
        source_tool="SolidWorks",
        representation="interchange",
    )
    db_session.add(ver)
    db_session.commit()

    result = SearchService(db_session).search(
        SearchParams(org_id=org.id, domain="mechanical")
    )
    assert result["facets"]["domains"].get("mechanical", 0) >= 1
    assert result["facets"]["source_tools"].get("SolidWorks", 0) >= 1
    assert any(h["name"] == "facet-test" for h in result["data"])


def test_bundle_invalid_without_manifest(client):
    token = _login(client)
    headers = _auth(token)
    project_id = str(client.test_project.id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("only.txt", b"no manifest")
    resp = client.post(
        "/v1/objects/upload-bundle",
        headers=headers,
        data={"project_id": project_id},
        files={"file": ("bad.zip", io.BytesIO(buf.getvalue()), "application/zip")},
    )
    assert resp.status_code == 422
