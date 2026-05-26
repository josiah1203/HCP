from __future__ import annotations
import hashlib
import json
import uuid
from datetime import datetime, timezone
from io import BytesIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.rbac import can_admin, role_at_least
from app.config import settings
from app.models.db import HardwareObject, Project, Version
from app.services.audit import write_audit
from app.services.lifecycle import validate_transition
from app.services.object_types import (
    build_hcp_uri,
    build_storage_key,
    infer_domain,
    infer_object_type,
    infer_representation,
)
from app.services.tasks import enqueue_parse
from infra.pal.factory import get_storage_provider
from infra.pal.interfaces.storage import StorageProvider


class ObjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._storage: StorageProvider | None = None

    @property
    def storage(self):
        if self._storage is None:
            self._storage = get_storage_provider()
        return self._storage

    def upload(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        file_bytes: bytes,
        filename: str,
        name: str,
        description: str | None,
        object_id: uuid.UUID | None,
        content_type: str,
        source_tool: str | None = None,
        source_tool_version: str | None = None,
        domain: str | None = None,
        representation: str | None = None,
        derived_from_version_id: uuid.UUID | None = None,
    ) -> tuple[HardwareObject, Version, bool]:
        project = self.db.scalar(
            select(Project).where(
                Project.id == project_id, Project.org_id == user.org_id
            )
        )
        if project is None:
            raise ValueError("project_not_found")

        content_hash = hashlib.sha256(file_bytes).hexdigest()
        deduplicated = False
        resolved_domain = infer_domain(
            filename, content_type, source_tool, domain=domain
        )
        resolved_representation = infer_representation(
            filename, representation=representation
        )
        resolved_object_type = infer_object_type(
            filename,
            domain=resolved_domain,
            mime=content_type,
            source_tool=source_tool,
        )

        if object_id is None:
            hw_object = HardwareObject(
                org_id=user.org_id,
                project_id=project_id,
                name=name,
                object_type=resolved_object_type,
                domain=resolved_domain,
                source_tool=source_tool,
                representation=resolved_representation,
                created_by=user.id,
            )
            self.db.add(hw_object)
            self.db.flush()
            version_num = 1
        else:
            hw_object = self.db.scalar(
                select(HardwareObject).where(
                    HardwareObject.id == object_id,
                    HardwareObject.org_id == user.org_id,
                )
            )
            if hw_object is None:
                raise ValueError("object_not_found")
            hw_object.domain = resolved_domain
            if source_tool:
                hw_object.source_tool = source_tool
            hw_object.representation = resolved_representation
            max_version = self.db.scalar(
                select(func.max(Version.version_num)).where(
                    Version.object_id == object_id
                )
            )
            version_num = (max_version or 0) + 1

        existing = self.db.scalar(
            select(Version).where(
                Version.org_id == user.org_id,
                Version.content_hash == content_hash,
            )
        )

        storage_key = build_storage_key(
            str(user.org_id),
            str(project_id),
            str(hw_object.id),
            version_num,
            filename,
        )

        if existing is not None and existing.storage_key:
            storage_key = existing.storage_key
            deduplicated = True
        else:
            self.storage.upload(storage_key, BytesIO(file_bytes), content_type)

        if derived_from_version_id is not None:
            parent = self.db.scalar(
                select(Version).where(
                    Version.id == derived_from_version_id,
                    Version.org_id == user.org_id,
                )
            )
            if parent is None:
                raise ValueError("derived_from_version_not_found")

        version = Version(
            org_id=user.org_id,
            object_id=hw_object.id,
            version_num=version_num,
            filename=filename,
            content_hash=content_hash,
            file_size_bytes=len(file_bytes),
            storage_key=storage_key,
            parse_status="pending",
            lifecycle_state="draft",
            uploaded_by=user.id,
            description=description,
            source_tool=source_tool,
            source_tool_version=source_tool_version,
            domain=resolved_domain,
            representation=resolved_representation,
            derived_from_version_id=derived_from_version_id,
        )
        self.db.add(version)
        self.db.flush()

        write_audit(
            self.db,
            org_id=user.org_id,
            object_id=hw_object.id,
            version_num=version_num,
            event_type="version_created",
            actor_id=user.id,
            actor_email=user.email,
            metadata={
                "content_hash": content_hash,
                "deduplicated": deduplicated,
                "domain": resolved_domain,
                "representation": resolved_representation,
                "source_tool": source_tool,
            },
        )

        enqueue_parse(
            str(version.id),
            context={
                "domain": resolved_domain,
                "representation": resolved_representation,
                "source_tool": source_tool,
                "source_tool_version": source_tool_version,
            },
        )

        if resolved_representation == "derived" and derived_from_version_id is not None:
            self._link_derived_from(user.org_id, version.id, derived_from_version_id)

        return hw_object, version, deduplicated

    def _link_derived_from(
        self, org_id: uuid.UUID, version_id: uuid.UUID, parent_version_id: uuid.UUID
    ) -> None:
        from app.services.graph import get_graph_service

        graph = get_graph_service()
        if graph is None:
            return
        try:
            if graph.ping():
                graph.create_derived_from(
                    str(org_id), str(version_id), str(parent_version_id)
                )
        except Exception:
            pass

    def get_object(
        self, object_id: uuid.UUID, org_id: uuid.UUID, *, include_deleted: bool = False
    ) -> HardwareObject | None:
        query = select(HardwareObject).where(
            HardwareObject.id == object_id,
            HardwareObject.org_id == org_id,
        )
        if not include_deleted:
            query = query.where(HardwareObject.deleted_at.is_(None))
        return self.db.scalar(query)

    def list_versions(self, object_id: uuid.UUID, org_id: uuid.UUID) -> list[Version]:
        obj = self.get_object(object_id, org_id)
        if obj is None:
            return []
        return list(
            self.db.scalars(
                select(Version)
                .where(Version.object_id == object_id)
                .order_by(Version.version_num.desc())
            )
        )

    def get_version(
        self, object_id: uuid.UUID, version_num: int, org_id: uuid.UUID
    ) -> Version | None:
        return self.db.scalar(
            select(Version).where(
                Version.object_id == object_id,
                Version.version_num == version_num,
                Version.org_id == org_id,
            )
        )

    def presigned_download(self, version: Version) -> str:
        return self.storage.generate_presigned_url(
            version.storage_key,
            settings.presigned_url_expiry_seconds,
        )

    def get_parsed_json(self, version: Version) -> dict | None:
        if version.parse_status != "complete" or not version.parsed_key:
            return None
        raw = self.storage.download(version.parsed_key)
        return json.loads(raw.decode())

    def promote(
        self,
        *,
        user: CurrentUser,
        version: Version,
        target_state: str,
        comment: str | None,
    ) -> Version:
        transition = validate_transition(version.lifecycle_state, target_state)
        if transition is None:
            raise ValueError("invalid_transition")

        min_role, _event = transition
        if not role_at_least(user.role, min_role):
            raise ValueError("forbidden")

        from_state = version.lifecycle_state
        version.lifecycle_state = target_state
        write_audit(
            self.db,
            org_id=user.org_id,
            object_id=version.object_id,
            version_num=version.version_num,
            event_type="lifecycle_transition",
            from_state=from_state,
            to_state=target_state,
            actor_id=user.id,
            actor_email=user.email,
            comment=comment,
        )
        return version

    def soft_delete(
        self, hw_object: HardwareObject, user: CurrentUser
    ) -> HardwareObject:
        if not can_admin(user.role):
            raise ValueError("forbidden")
        hw_object.deleted_at = datetime.now(timezone.utc)
        latest = self.db.scalar(
            select(Version)
            .where(Version.object_id == hw_object.id)
            .order_by(Version.version_num.desc())
            .limit(1)
        )
        version_num = latest.version_num if latest else 0
        write_audit(
            self.db,
            org_id=user.org_id,
            object_id=hw_object.id,
            version_num=version_num,
            event_type="object_deleted",
            actor_id=user.id,
            actor_email=user.email,
        )
        return hw_object

    @staticmethod
    def version_to_schema(version: Version, project_id: uuid.UUID) -> dict:
        return {
            "id": version.id,
            "object_id": version.object_id,
            "version_num": version.version_num,
            "filename": version.filename,
            "content_hash": version.content_hash,
            "file_size_bytes": version.file_size_bytes,
            "parse_status": version.parse_status,
            "lifecycle_state": version.lifecycle_state,
            "description": version.description,
            "source_tool": version.source_tool,
            "source_tool_version": version.source_tool_version,
            "domain": version.domain,
            "representation": version.representation,
            "created_at": version.created_at,
            "hcp_uri": build_hcp_uri(
                str(version.org_id),
                str(project_id),
                str(version.object_id),
                version.version_num,
            ),
        }
