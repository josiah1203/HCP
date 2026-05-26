from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.services.graph import GraphService
from app.services.object_types import infer_object_type, infer_representation
from app.services.objects import ObjectService

MANIFEST_NAME = "manifest.json"
BUNDLE_REL_TYPES = frozenset(
    {
        "CONTAINS",
        "USES",
        "TARGETS",
        "VALIDATES",
        "SATISFIES",
        "SOURCED_FROM",
        "DERIVED_FROM",
        "REPRESENTS",
    }
)
OBJECT_LEVEL_REL_TYPES = frozenset(
    {
        "CONTAINS",
        "USES",
        "TARGETS",
        "VALIDATES",
        "SATISFIES",
        "SOURCED_FROM",
        "REPRESENTS",
    }
)


def _normalize_path(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


class BundleIngestService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._objects = ObjectService(db)
        self._graph = GraphService(db)

    def ingest(
        self,
        *,
        user: CurrentUser,
        project_id: UUID,
        bundle_bytes: bytes,
        bundle_filename: str,
        bundle_name: str | None,
        description: str | None,
    ) -> dict[str, Any]:
        manifest, members = self._extract_bundle(bundle_bytes, bundle_filename)
        source_tool = manifest.get("source_tool")
        source_tool_version = manifest.get("source_tool_version")
        release = manifest.get("release") or bundle_name

        path_to_ids: dict[str, dict[str, UUID]] = {}
        artifacts_out: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        for entry in manifest.get("artifacts") or []:
            if not entry.get("path") or not entry.get("domain"):
                raise ValueError("invalid_bundle")
            rel_path = _normalize_path(entry["path"])
            if rel_path in seen_paths:
                raise ValueError("invalid_bundle")
            seen_paths.add(rel_path)
            if rel_path not in members:
                raise ValueError("invalid_bundle")

            file_bytes = members[rel_path]
            filename = PurePosixPath(rel_path).name
            artifact_name = entry.get("name") or filename
            domain = entry["domain"]
            representation = entry.get("representation") or infer_representation(
                filename
            )

            hw_object, version, _deduped = self._objects.upload(
                user=user,
                project_id=project_id,
                file_bytes=file_bytes,
                filename=filename,
                name=artifact_name,
                description=description or release,
                object_id=None,
                content_type="application/octet-stream",
                source_tool=source_tool,
                source_tool_version=source_tool_version,
                domain=domain,
                representation=representation,
            )
            hw_object.object_type = infer_object_type(
                filename, domain=domain, source_tool=source_tool
            )
            self.db.flush()

            path_to_ids[rel_path] = {
                "object_id": hw_object.id,
                "version_id": version.id,
            }
            artifacts_out.append(
                {
                    "path": rel_path,
                    "object_id": hw_object.id,
                    "version_id": version.id,
                    "version_num": version.version_num,
                }
            )

        relationships_applied = self._apply_relationships(
            user.org_id, manifest.get("relationships") or [], path_to_ids
        )

        return {
            "release": release,
            "source_tool": source_tool,
            "artifacts": artifacts_out,
            "relationships_applied": relationships_applied,
        }

    def _extract_bundle(
        self, bundle_bytes: bytes, bundle_filename: str
    ) -> tuple[dict[str, Any], dict[str, bytes]]:
        lower = bundle_filename.lower()
        if not lower.endswith(".zip"):
            raise ValueError("invalid_bundle")

        members: dict[str, bytes] = {}
        manifest: dict[str, Any] | None = None

        with zipfile.ZipFile(BytesIO(bundle_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = _normalize_path(info.filename)
                if rel.endswith("/"):
                    continue
                members[rel] = zf.read(info.filename)
                if rel == MANIFEST_NAME or rel.endswith(f"/{MANIFEST_NAME}"):
                    manifest = json.loads(members[rel].decode())

        if manifest is None:
            raise ValueError("invalid_bundle")
        if manifest.get("schema_version") != "1.0":
            raise ValueError("invalid_bundle")
        if not manifest.get("artifacts"):
            raise ValueError("invalid_bundle")

        return manifest, members

    def _apply_relationships(
        self,
        org_id: UUID,
        relationships: list[dict[str, Any]],
        path_to_ids: dict[str, dict[str, UUID]],
    ) -> int:
        applied = 0
        for rel in relationships:
            rel_type = rel.get("type", "").upper()
            if rel_type not in BUNDLE_REL_TYPES:
                continue

            from_path = _normalize_path(rel["from"])
            to_path = _normalize_path(rel["to"])
            from_ids = path_to_ids.get(from_path)
            to_ids = path_to_ids.get(to_path)
            if not from_ids or not to_ids:
                continue

            metadata = rel.get("metadata") or {}

            if rel_type == "DERIVED_FROM":
                self._graph.create_derived_from_link(
                    org_id,
                    from_version_id=from_ids["version_id"],
                    to_version_id=to_ids["version_id"],
                    metadata=metadata,
                )
                applied += 1
                continue

            if rel_type not in OBJECT_LEVEL_REL_TYPES:
                continue

            self._graph.create_link(
                org_id=org_id,
                from_object_id=from_ids["object_id"],
                to_object_id=to_ids["object_id"],
                relationship_type=rel_type,
                metadata=metadata,
            )
            applied += 1

        return applied
