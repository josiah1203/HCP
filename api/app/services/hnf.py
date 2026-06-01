from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import HnfDocument, HosObjectSnapshot, Version


HNF_SCHEMA_VERSION = "0.5-min"


class HnfObjectSnapshotInput(BaseModel):
    """Commit-level object snapshot (maps to hos_object_snapshots)."""

    object_path: str
    object_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    version_num: int | None = None
    content_hash: str | None = None
    hnf_type: str
    domain: str | None = None
    refs: list[str] = Field(default_factory=list)
    properties: dict[str, Any] | None = None


class HnfDocumentBody(BaseModel):
    document_uri: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    objects: list[dict[str, Any]] = Field(default_factory=list)


def validate_object_snapshot(snapshot: dict[str, Any]) -> list[str]:
    """Additive validation; returns warnings only (never raises)."""
    warnings: list[str] = []
    try:
        HnfObjectSnapshotInput.model_validate(snapshot)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", ()))
            warnings.append(f"{loc}: {err.get('msg', 'invalid')}")
        return warnings

    if not snapshot.get("object_path"):
        warnings.append("object_path: required")
    if not snapshot.get("hnf_type"):
        warnings.append("hnf_type: required")
    vnum = snapshot.get("version_num")
    if vnum is not None and int(vnum) < 1:
        warnings.append("version_num: must be >= 1 when set")
    return warnings


def validate_document_body(document: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    try:
        HnfDocumentBody.model_validate(document)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", ()))
            warnings.append(f"{loc}: {err.get('msg', 'invalid')}")
    return warnings


def document_content_hash(document: dict[str, Any]) -> str:
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def legacy_tree_value(snapshot: HnfObjectSnapshotInput) -> dict[str, Any]:
    out: dict[str, Any] = {"hnf_type": snapshot.hnf_type}
    if snapshot.object_id is not None:
        out["object_id"] = str(snapshot.object_id)
    if snapshot.version_num is not None:
        out["version_num"] = snapshot.version_num
    if snapshot.version_id is not None:
        out["version_id"] = str(snapshot.version_id)
    if snapshot.content_hash:
        out["content_hash"] = snapshot.content_hash
    if snapshot.domain:
        out["domain"] = snapshot.domain
    if snapshot.refs:
        out["refs"] = snapshot.refs
    if snapshot.properties:
        out["properties"] = snapshot.properties
    return out


def legacy_tree_from_snapshots(
    snapshots: list[HnfObjectSnapshotInput] | list[dict[str, Any]],
) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for snap in snapshots:
        if isinstance(snap, dict):
            path = snap.get("object_path")
            if not path:
                continue
            entry = {
                k: v
                for k, v in snap.items()
                if k not in ("object_path",) and v is not None
            }
            if "object_id" in entry and entry["object_id"] is not None:
                entry["object_id"] = str(entry["object_id"])
            if "version_id" in entry and entry["version_id"] is not None:
                entry["version_id"] = str(entry["version_id"])
            tree[str(path)] = entry
        else:
            tree[snap.object_path] = legacy_tree_value(snap)
    return tree


def snapshot_fingerprint(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def snapshots_from_legacy_tree(tree: dict[str, Any]) -> list[HnfObjectSnapshotInput]:
    out: list[HnfObjectSnapshotInput] = []
    for path, value in (tree or {}).items():
        if path in ("scene_graph_snapshot", "tree_root_ref"):
            continue
        if not isinstance(value, dict):
            continue
        hnf_type = value.get("hnf_type") or value.get("kind") or "hardware.object"
        object_id = value.get("object_id")
        version_id = value.get("version_id")
        out.append(
            HnfObjectSnapshotInput(
                object_path=path,
                object_id=uuid.UUID(str(object_id)) if object_id else None,
                version_id=uuid.UUID(str(version_id)) if version_id else None,
                version_num=value.get("version_num"),
                content_hash=value.get("content_hash"),
                hnf_type=str(hnf_type),
                domain=value.get("domain"),
                refs=list(value.get("refs") or []),
                properties=value.get("properties"),
            )
        )
    return out


def build_upload_snapshot_hint(
    *,
    object_id: uuid.UUID,
    version_num: int,
    version_id: uuid.UUID,
    content_hash: str,
    object_type: str,
    domain: str | None,
    filename: str,
) -> dict[str, Any]:
    return {
        "object_path": filename,
        "object_id": str(object_id),
        "version_id": str(version_id),
        "version_num": version_num,
        "content_hash": content_hash,
        "hnf_type": object_type,
        "domain": domain,
        "refs": [],
    }


class HnfService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_upload_metadata(
        self,
        *,
        org_id: uuid.UUID,
        version: Version,
        object_type: str,
        domain: str | None,
        filename: str,
    ) -> list[str]:
        _ = org_id
        hint = build_upload_snapshot_hint(
            object_id=version.object_id,
            version_num=version.version_num,
            version_id=version.id,
            content_hash=version.content_hash,
            object_type=object_type,
            domain=domain,
            filename=filename,
        )
        return validate_object_snapshot(hint)

    def upsert_document(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        document_uri: str,
        document: dict[str, Any],
    ) -> tuple[HnfDocument, list[str]]:
        warnings = validate_document_body(document)
        content_hash = document_content_hash(document)
        existing = self.db.scalar(
            select(HnfDocument).where(
                HnfDocument.org_id == org_id,
                HnfDocument.project_id == project_id,
                HnfDocument.document_uri == document_uri,
            )
        )
        if existing is not None:
            existing.body = document
            existing.content_hash = content_hash
            existing.validation_warnings = warnings or None
            return existing, warnings

        row = HnfDocument(
            org_id=org_id,
            project_id=project_id,
            document_uri=document_uri,
            content_hash=content_hash,
            body=document,
            validation_warnings=warnings or None,
        )
        self.db.add(row)
        self.db.flush()
        return row, warnings

    def persist_commit_snapshots(
        self,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        commit_id: uuid.UUID,
        snapshots: list[dict[str, Any]],
    ) -> tuple[list[HosObjectSnapshot], list[str]]:
        all_warnings: list[str] = []
        rows: list[HosObjectSnapshot] = []
        seq_by_path: dict[str, int] = {}

        for raw in snapshots:
            all_warnings.extend(validate_object_snapshot(raw))
            try:
                snap = HnfObjectSnapshotInput.model_validate(raw)
            except ValidationError:
                continue

            prev = seq_by_path.get(snap.object_path, 0)
            seq_by_path[snap.object_path] = prev + 1
            props = dict(snap.properties or {})
            if snap.version_num is not None:
                props.setdefault("version_num", snap.version_num)

            row = HosObjectSnapshot(
                org_id=org_id,
                project_id=project_id,
                commit_id=commit_id,
                object_path=snap.object_path,
                object_id=snap.object_id,
                version_id=snap.version_id,
                content_hash=snap.content_hash,
                hnf_type=snap.hnf_type,
                domain=snap.domain,
                refs=snap.refs or [],
                snapshot_version=seq_by_path[snap.object_path],
                properties=props,
            )
            self.db.add(row)
            rows.append(row)

        self.db.flush()
        return rows, all_warnings

    def load_commit_snapshot_map(
        self, commit_id: uuid.UUID, org_id: uuid.UUID
    ) -> dict[str, HosObjectSnapshot]:
        rows = self.db.scalars(
            select(HosObjectSnapshot).where(
                HosObjectSnapshot.commit_id == commit_id,
                HosObjectSnapshot.org_id == org_id,
            )
        )
        return {r.object_path: r for r in rows}

    def snapshot_to_diff_value(self, row: HosObjectSnapshot) -> dict[str, Any]:
        props = dict(row.properties or {})
        version_num = props.pop("version_num", None)
        return {
            "object_id": str(row.object_id) if row.object_id else None,
            "version_id": str(row.version_id) if row.version_id else None,
            "version_num": version_num,
            "content_hash": row.content_hash,
            "hnf_type": row.hnf_type,
            "domain": row.domain,
            "refs": row.refs or [],
            "properties": props or None,
            "snapshot_version": row.snapshot_version,
        }

    def try_parse_upload_bytes(
        self, file_bytes: bytes, *, filename: str, content_type: str
    ) -> tuple[dict[str, Any] | None, list[str]]:
        looks_hnf = (
            filename.endswith(".hnf.json")
            or filename.endswith(".hnf")
            or content_type in ("application/hnf+json", "application/vnd.hcp.hnf+json")
            or content_type == "application/json"
        )
        if not looks_hnf:
            return None, []
        try:
            if isinstance(file_bytes, (bytes, bytearray)):
                data = json.loads(file_bytes.decode("utf-8"))
            else:
                data = file_bytes
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, ["hnf_invalid_json"]
        if not isinstance(data, dict):
            return None, ["hnf_not_object"]
        warnings = validate_document_body(data)
        if not data.get("document_uri"):
            warnings.append("document_uri: required")
            data = {**data, "document_uri": f"hcp://upload/{filename}"}
        return data, warnings


def snapshot_fingerprint(value: dict[str, Any]) -> str:
    parts = [
        value.get("content_hash") or "",
        value.get("hnf_type") or "",
        value.get("domain") or "",
        json.dumps(value.get("refs") or [], sort_keys=True),
        json.dumps(value.get("properties") or {}, sort_keys=True),
        str(value.get("snapshot_version") or value.get("version_num") or 1),
    ]
    return "|".join(parts)


def legacy_tree_from_snapshots(snapshots: list[HnfObjectSnapshotInput]) -> dict[str, Any]:
    return {snap.object_path: legacy_tree_value(snap) for snap in snapshots}


def validate_hnf_document(data: Any) -> tuple[dict[str, Any] | None, list[str]]:
    if isinstance(data, (bytes, bytearray)):
        try:
            data = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None, ["hnf_invalid_json"]
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return None, ["hnf_invalid_json"]
    if not isinstance(data, dict):
        return None, ["hnf_not_object"]
    warnings = validate_document_body(data)
    if not data.get("document_uri"):
        warnings.append("document_uri: required")
    return data, warnings
