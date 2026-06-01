from __future__ import annotations

import json
import uuid

from app.services.hnf import (
    HnfObjectSnapshotInput,
    document_content_hash,
    legacy_tree_value,
    snapshots_from_legacy_tree,
    validate_document_body,
    validate_hnf_document,
    validate_object_snapshot,
)


def test_validate_hnf_document_accepts_minimum():
    body, warnings = validate_hnf_document(
        {
            "document_uri": "hcp://proj/board.hnf",
            "metadata": {"tool": "kicad"},
            "objects": [{"id": "obj-1", "kind": "schematic.symbol"}],
        }
    )
    assert body is not None
    assert body["document_uri"] == "hcp://proj/board.hnf"
    assert warnings == []


def test_validate_hnf_document_never_raises_on_garbage():
    body, warnings = validate_hnf_document(b"not-json-at-all")
    assert body is None
    assert "hnf_invalid_json" in warnings


def test_validate_object_snapshot_additive():
    warnings = validate_object_snapshot(
        {
            "object_path": "board.kicad_sch",
            "hnf_type": "schematic.board",
        }
    )
    assert warnings == []


def test_legacy_tree_roundtrip():
    tree = {
        "schematic.kicad_sch": {
            "object_id": str(uuid.uuid4()),
            "version_num": 2,
            "hnf_type": "schematic.board",
            "domain": "electrical",
        }
    }
    snaps = snapshots_from_legacy_tree(tree)
    assert len(snaps) == 1
    assert legacy_tree_value(snaps[0])["hnf_type"] == "schematic.board"


def test_document_content_hash_stable():
    body = {"document_uri": "hcp://x", "objects": []}
    assert document_content_hash(body) == document_content_hash(body)


def test_validate_document_body_partial():
    warnings = validate_document_body({"objects": []})
    assert isinstance(warnings, list)


def test_hnf_object_snapshot_input():
    snap = HnfObjectSnapshotInput(
        object_path="x",
        hnf_type="part",
        object_id=uuid.uuid4(),
    )
    assert snap.object_path == "x"


def test_validate_hnf_from_json_bytes():
    payload = json.dumps(
        {
            "document_uri": "hcp://doc",
            "objects": [{"id": "a", "kind": "part"}],
        }
    ).encode()
    body, warnings = validate_hnf_document(payload)
    assert body is not None
