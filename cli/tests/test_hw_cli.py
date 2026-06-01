from __future__ import annotations

import json
import os
import uuid

import httpx
import pytest
import respx

from hw.main import main


BASE = "https://api.test.hcp.io"


@pytest.fixture(autouse=True)
def _env_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HCP_API_URL", BASE)
    monkeypatch.setenv("HCP_ACCESS_TOKEN", "test-token")


@respx.mock
def test_auth_login_json() -> None:
    respx.post(f"{BASE}/v1/auth/login").mock(
        return_value=httpx.Response(200, json={"access_token": "tok-1"})
    )
    code = main(
        [
            "auth",
            "login",
            "--email",
            "a@b.c",
            "--password",
            "secret",
            "--api-url",
            BASE,
            "--json",
        ]
    )
    assert code == 0


@respx.mock
def test_import_json() -> None:
    project_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/projects/{project_id}/import").mock(
        return_value=httpx.Response(
            201,
            json={
                "branch_id": str(uuid.uuid4()),
                "branch_name": "import/kicad/20260101T000000Z",
                "commit_id": str(uuid.uuid4()),
                "format": "kicad",
                "artifacts": [],
                "metrics": {
                    "source_elements": 2,
                    "imported_elements": 2,
                    "loss_ratio": 0.0,
                },
            },
        )
    )
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(suffix=".kicad_sch", delete=False) as tmp:
        tmp.write(b"(kicad_sch (version 20230121))")
        path = tmp.name
    try:
        code = main(
            [
                "import",
                "--project-id",
                project_id,
                "--format",
                "kicad",
                "--file",
                path,
                "--json",
            ]
        )
        assert code == 0
    finally:
        Path(path).unlink(missing_ok=True)


@respx.mock
def test_branch_create_json() -> None:
    project_id = str(uuid.uuid4())
    branch_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/hos/branches").mock(
        return_value=httpx.Response(
            201,
            json={"id": branch_id, "name": "feature", "project_id": project_id},
        )
    )
    code = main(
        [
            "branch",
            "create",
            "--project-id",
            project_id,
            "--name",
            "feature",
            "--json",
        ]
    )
    assert code == 0


@respx.mock
def test_diff_json() -> None:
    project_id = str(uuid.uuid4())
    from_id = str(uuid.uuid4())
    to_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/hos/diff").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {
                        "path": "schematic.kicad_sch",
                        "change_type": "modified",
                    }
                ]
            },
        )
    )
    code = main(
        [
            "diff",
            "--project-id",
            project_id,
            "--from",
            from_id,
            "--to",
            to_id,
            "--json",
        ]
    )
    assert code == 0


@respx.mock
def test_import_json() -> None:
    project_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/projects/{project_id}/import").mock(
        return_value=httpx.Response(
            201,
            json={
                "branch_id": str(uuid.uuid4()),
                "branch_name": "import/kicad/20260601T120000Z",
                "commit_id": str(uuid.uuid4()),
                "format": "kicad",
                "artifacts": [],
                "metrics": {
                    "source_elements": 2,
                    "imported_elements": 2,
                    "loss_ratio": 0.0,
                },
            },
        )
    )
    code = main(
        [
            "import",
            "--project-id",
            project_id,
            "--format",
            "kicad",
            "--file",
            __file__,
            "--json",
        ]
    )
    assert code == 0


@respx.mock
def test_merge_and_conflicts_json() -> None:
    project_id = str(uuid.uuid4())
    merge_id = str(uuid.uuid4())
    conflict_id = str(uuid.uuid4())
    respx.post(f"{BASE}/v1/hos/merge").mock(
        return_value=httpx.Response(
            201,
            json={
                "merge_id": merge_id,
                "status": "conflicts",
                "conflict_count": 1,
            },
        )
    )
    respx.get(f"{BASE}/v1/hos/merges/{merge_id}/conflicts").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"id": conflict_id, "path": "board.kicad_pcb", "status": "open"}]},
        )
    )
    respx.post(f"{BASE}/v1/hos/conflicts/{conflict_id}/resolve").mock(
        return_value=httpx.Response(
            200,
            json={"id": conflict_id, "status": "resolved"},
        )
    )
    assert (
        main(
            [
                "merge",
                "--project-id",
                project_id,
                "--target",
                str(uuid.uuid4()),
                "--source",
                str(uuid.uuid4()),
                "--json",
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "conflicts",
                "list",
                "--merge-id",
                merge_id,
                "--project-id",
                project_id,
                "--json",
            ]
        )
        == 0
    )
    resolution = json.dumps({"take": "ours"})
    assert (
        main(
            [
                "conflicts",
                "resolve",
                "--conflict-id",
                conflict_id,
                "--project-id",
                project_id,
                "--resolution",
                resolution,
                "--json",
            ]
        )
        == 0
    )
