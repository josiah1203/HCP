from __future__ import annotations

import re
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.rbac import role_at_least
from app.models.db import Project
from app.services.event_taxonomy import EVENT_ARTIFACT_BRANCHED
from app.services.events import EventPublisher
from app.services.hnf import HnfObjectSnapshotInput
from app.services.hos_version_control import HosVersionControlService
from app.services.object_types import infer_object_type
from app.services.objects import ObjectService
from app.services.tasks import enqueue_parse

SUPPORTED_FORMATS: dict[str, frozenset[str]] = {
    "kicad": frozenset({".kicad_sch", ".kicad_pcb", ".kicad_pro"}),
}

_KICAD_PARSERS: dict[str, Any] | None = None


def _kicad_parsers() -> dict[str, Any]:
    global _KICAD_PARSERS
    if _KICAD_PARSERS is None:
        from parser.parsers.kicad_pcb import KiCadPCBParser
        from parser.parsers.kicad_sch import KiCadSchematicParser
        from parser.pral.interfaces.parser_plugin import ParseContext

        _KICAD_PARSERS = {
            ".kicad_sch": (KiCadSchematicParser(), ParseContext),
            ".kicad_pcb": (KiCadPCBParser(), ParseContext),
        }
    return _KICAD_PARSERS


def _normalize_path(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/")))


def _branch_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slugify_branch_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower())
    return cleaned.strip("-") or "import"


def count_parsed_elements(parsed: Any) -> int:
    """Count design elements from a ParsedOutput for loss metrics."""
    total = len(parsed.components or [])
    board = parsed.board or {}
    if isinstance(board, dict):
        total += int(board.get("net_count") or 0)
    sheets = parsed.extracted_metadata.get("hierarchical_sheets") or []
    if isinstance(sheets, list):
        total += len(sheets)
    return total


def parse_for_metrics(format_name: str, filename: str, file_bytes: bytes) -> int:
    if format_name != "kicad":
        return 0
    suffix = PurePosixPath(filename).suffix.lower()
    parsers = _kicad_parsers()
    entry = parsers.get(suffix)
    if entry is None:
        return 0
    parser, ctx_cls = entry
    ctx = ctx_cls(
        filename=filename,
        object_id=str(uuid.uuid4()),
        version_id=str(uuid.uuid4()),
        source_tool="KiCad",
        domain="electrical",
    )
    try:
        parsed = parser.parse(file_bytes, ctx)
        return count_parsed_elements(parsed)
    except Exception:
        return 0


class ImportPipelineService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._objects = ObjectService(db)
        self._hos = HosVersionControlService(db)
        self._events = EventPublisher(db)

    def _require_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.org_id == org_id)
        )
        if project is None or project.archived_at is not None:
            raise ValueError("project_not_found")
        return project

    def _extract_members(
        self, payload: bytes, filename: str
    ) -> dict[str, bytes]:
        lower = filename.lower()
        if lower.endswith(".zip"):
            members: dict[str, bytes] = {}
            with zipfile.ZipFile(BytesIO(payload)) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    rel = _normalize_path(info.filename)
                    if rel.startswith("__MACOSX/") or "/." in rel:
                        continue
                    members[rel] = zf.read(info)
            return members

        return {_normalize_path(filename): payload}

    def _filter_import_files(
        self, format_name: str, members: dict[str, bytes]
    ) -> dict[str, bytes]:
        allowed = SUPPORTED_FORMATS.get(format_name)
        if allowed is None:
            raise ValueError("unsupported_format")
        filtered: dict[str, bytes] = {}
        for path, data in members.items():
            suffix = PurePosixPath(path).suffix.lower()
            if suffix in allowed and suffix != ".kicad_pro":
                filtered[path] = data
        if not filtered:
            raise ValueError("no_importable_files")
        return filtered

    def run_import(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        format_name: str,
        payload: bytes,
        filename: str,
        message: str | None = None,
    ) -> dict[str, Any]:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")

        format_key = _slugify_branch_segment(format_name)
        if format_key not in SUPPORTED_FORMATS:
            raise ValueError("unsupported_format")

        self._require_project(project_id, user.org_id)
        members = self._extract_members(payload, filename)
        import_files = self._filter_import_files(format_key, members)

        branch_name = f"import/{format_key}/{_branch_timestamp()}"
        branch = self._hos.create_branch(
            user=user,
            project_id=project_id,
            name=branch_name,
            from_commit_id=None,
        )

        artifacts: list[dict[str, Any]] = []
        snapshots: list[dict[str, Any]] = []
        source_elements = 0
        imported_elements = 0

        for rel_path, file_bytes in sorted(import_files.items()):
            base_name = PurePosixPath(rel_path).name
            source_elements += parse_for_metrics(format_key, base_name, file_bytes)

            hw_object, version, _deduped = self._objects.upload(
                user=user,
                project_id=project_id,
                file_bytes=file_bytes,
                filename=base_name,
                name=base_name,
                description=message or f"Import on {branch_name}",
                object_id=None,
                content_type="application/octet-stream",
                source_tool="KiCad" if format_key == "kicad" else format_key,
                domain="electrical",
            )
            enqueue_parse(version.id)
            element_count = parse_for_metrics(format_key, base_name, file_bytes)
            imported_elements += element_count

            obj_type = infer_object_type(
                base_name, domain="electrical", source_tool="KiCad"
            )
            snapshots.append(
                HnfObjectSnapshotInput(
                    object_path=rel_path,
                    object_id=hw_object.id,
                    version_id=version.id,
                    version_num=version.version_num,
                    content_hash=version.content_hash,
                    hnf_type=obj_type,
                    domain="electrical",
                    properties={"import_format": format_key, "element_count": element_count},
                ).model_dump(mode="json")
            )
            artifacts.append(
                {
                    "path": rel_path,
                    "object_id": str(hw_object.id),
                    "version_id": str(version.id),
                    "version_num": version.version_num,
                    "element_count": element_count,
                }
            )

        commit_message = message or f"Import {format_key} ({len(artifacts)} artifacts)"
        commit = self._hos.commit(
            user=user,
            project_id=project_id,
            branch_id=branch.id,
            message=commit_message,
            object_snapshots=snapshots,
            tree_root_ref=snapshots[0]["object_path"] if snapshots else None,
        )

        loss_ratio = 0.0
        if source_elements > 0:
            loss_ratio = max(0.0, (source_elements - imported_elements) / source_elements)

        dedupe_key = f"import:{branch.id}:{commit.id}"
        self._events.publish(
            org_id=user.org_id,
            project_id=project_id,
            event_type=EVENT_ARTIFACT_BRANCHED,
            dedupe_key=dedupe_key,
            actor_id=user.id,
            metadata={
                "branch_id": str(branch.id),
                "branch_name": branch_name,
                "commit_id": str(commit.id),
                "format": format_key,
                "artifact_count": len(artifacts),
                "source_elements": source_elements,
                "imported_elements": imported_elements,
                "loss_ratio": loss_ratio,
            },
        )

        return {
            "branch_id": str(branch.id),
            "branch_name": branch_name,
            "commit_id": str(commit.id),
            "format": format_key,
            "artifacts": artifacts,
            "metrics": {
                "source_elements": source_elements,
                "imported_elements": imported_elements,
                "loss_ratio": loss_ratio,
            },
        }
