from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.rbac import role_at_least
from app.models.db import (
    HosAuditLog,
    HosBranch,
    HosCommit,
    HosCommitParent,
    HosConflict,
    HosMerge,
    HosObjectSnapshot,
    Project,
)
from app.services.event_taxonomy import (
    EVENT_COMMIT_CREATED,
    EVENT_CONFLICT_DETECTED,
    EVENT_MERGE_CREATED,
)
from app.services.event_emission import EventEmissionHooks
from app.services.hnf import (
    HnfObjectSnapshotInput,
    HnfService,
    legacy_tree_value,
    snapshots_from_legacy_tree,
)
from app.services.scene_graph import SceneGraphService


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HosVersionControlService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._events = EventEmissionHooks(db)
        self._hnf = HnfService(db)

    def _require_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.org_id == org_id)
        )
        if project is None:
            raise ValueError("project_not_found")
        return project

    def _write_audit(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        entity_type: str,
        entity_id: uuid.UUID,
        event_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        entry = HosAuditLog(
            org_id=user.org_id,
            project_id=project_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            actor_id=user.id,
            actor_email=user.email,
            metadata_=metadata,
        )
        self.db.add(entry)

    def _parent_ids(self, commit_id: uuid.UUID) -> list[uuid.UUID]:
        return list(
            self.db.scalars(
                select(HosCommitParent.parent_commit_id)
                .where(HosCommitParent.commit_id == commit_id)
                .order_by(HosCommitParent.parent_order.asc())
            )
        )

    def find_lca(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        commit_a: uuid.UUID,
        commit_b: uuid.UUID,
    ) -> uuid.UUID | None:
        self._require_project(project_id, user.org_id)
        ancestors_a: set[uuid.UUID] = set()
        queue: deque[uuid.UUID] = deque([commit_a])
        while queue:
            cid = queue.popleft()
            if cid in ancestors_a:
                continue
            ancestors_a.add(cid)
            for pid in self._parent_ids(cid):
                queue.append(pid)

        queue_b: deque[uuid.UUID] = deque([commit_b])
        while queue_b:
            cid = queue_b.popleft()
            if cid in ancestors_a:
                return cid
            for pid in self._parent_ids(cid):
                queue_b.append(pid)
        return None

    def _commit_state_map(
        self, commit: HosCommit, org_id: uuid.UUID
    ) -> dict[str, dict[str, Any]]:
        snap_map = self._hnf.load_commit_snapshot_map(commit.id, org_id)
        if snap_map:
            return {
                path: self._hnf.snapshot_to_diff_value(row)
                for path, row in snap_map.items()
            }
        tree = commit.tree or {}
        return {
            s.object_path: legacy_tree_value(s)
            for s in snapshots_from_legacy_tree(tree)
        }

    def _build_tree_from_snapshots(
        self, snapshots: list[HnfObjectSnapshotInput], *, root_ref: str | None = None
    ) -> tuple[dict[str, Any], str | None]:
        tree: dict[str, Any] = {}
        for snap in snapshots:
            tree[snap.object_path] = legacy_tree_value(snap)
        root = root_ref or (snapshots[0].object_path if snapshots else None)
        if root:
            tree["tree_root_ref"] = root
        return tree, root

    def create_branch(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        name: str,
        from_commit_id: uuid.UUID | None,
    ) -> HosBranch:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")
        self._require_project(project_id, user.org_id)

        head_commit_id: uuid.UUID | None = None
        if from_commit_id is not None:
            head = self.db.scalar(
                select(HosCommit).where(
                    HosCommit.id == from_commit_id,
                    HosCommit.org_id == user.org_id,
                    HosCommit.project_id == project_id,
                )
            )
            if head is None:
                raise ValueError("commit_not_found")
            head_commit_id = head.id

        branch = HosBranch(
            org_id=user.org_id,
            project_id=project_id,
            name=name,
            head_commit_id=head_commit_id,
            created_by=user.id,
        )
        self.db.add(branch)
        self.db.flush()

        self._write_audit(
            user=user,
            project_id=project_id,
            entity_type="branch",
            entity_id=branch.id,
            event_type="branch_created",
            metadata={"name": name, "from_commit_id": str(from_commit_id) if from_commit_id else None},
        )
        return branch

    def list_branches(self, *, user: CurrentUser, project_id: uuid.UUID) -> list[HosBranch]:
        self._require_project(project_id, user.org_id)
        return list(
            self.db.scalars(
                select(HosBranch)
                .where(
                    HosBranch.org_id == user.org_id,
                    HosBranch.project_id == project_id,
                )
                .order_by(HosBranch.name.asc())
            )
        )

    def get_branch(self, *, user: CurrentUser, project_id: uuid.UUID, branch_id: uuid.UUID) -> HosBranch:
        self._require_project(project_id, user.org_id)
        branch = self.db.scalar(
            select(HosBranch).where(
                HosBranch.id == branch_id,
                HosBranch.org_id == user.org_id,
                HosBranch.project_id == project_id,
            )
        )
        if branch is None:
            raise ValueError("branch_not_found")
        return branch

    def commit(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        branch_id: uuid.UUID,
        message: str,
        tree: dict | None = None,
        object_snapshots: list[dict[str, Any]] | None = None,
        tree_root_ref: str | None = None,
        parent_commit_ids: list[uuid.UUID] | None = None,
        create_scene_snapshot: bool = False,
        scene_snapshot_format: str = "json",
    ) -> HosCommit:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")
        self._require_project(project_id, user.org_id)
        branch = self.get_branch(user=user, project_id=project_id, branch_id=branch_id)

        resolved_parents: list[uuid.UUID] = []
        if parent_commit_ids is not None:
            resolved_parents = parent_commit_ids
        elif branch.head_commit_id is not None:
            resolved_parents = [branch.head_commit_id]

        for pid in resolved_parents:
            parent = self.db.scalar(
                select(HosCommit.id).where(
                    HosCommit.id == pid,
                    HosCommit.org_id == user.org_id,
                    HosCommit.project_id == project_id,
                )
            )
            if parent is None:
                raise ValueError("parent_commit_not_found")

        parsed_snapshots: list[HnfObjectSnapshotInput] = []
        if object_snapshots:
            for raw in object_snapshots:
                try:
                    parsed_snapshots.append(HnfObjectSnapshotInput.model_validate(raw))
                except Exception:
                    continue
        elif tree:
            parsed_snapshots = snapshots_from_legacy_tree(tree)

        legacy_tree, root_ref = self._build_tree_from_snapshots(
            parsed_snapshots, root_ref=tree_root_ref
        )
        if tree:
            for k, v in tree.items():
                if k not in legacy_tree:
                    legacy_tree[k] = v

        commit = HosCommit(
            org_id=user.org_id,
            project_id=project_id,
            branch_id=branch.id,
            message=message,
            created_by=user.id,
            tree=legacy_tree,
            tree_root_ref=root_ref,
        )
        self.db.add(commit)
        self.db.flush()

        if object_snapshots:
            _, hnf_warnings = self._hnf.persist_commit_snapshots(
                org_id=user.org_id,
                project_id=project_id,
                commit_id=commit.id,
                snapshots=object_snapshots,
            )
            if hnf_warnings:
                meta = commit.tree.get("_hnf_validation_warnings")
                if not isinstance(meta, list):
                    meta = []
                commit.tree = {**commit.tree, "_hnf_validation_warnings": meta + hnf_warnings}
        elif parsed_snapshots:
            self._hnf.persist_commit_snapshots(
                org_id=user.org_id,
                project_id=project_id,
                commit_id=commit.id,
                snapshots=[s.model_dump(mode="json") for s in parsed_snapshots],
            )

        for idx, pid in enumerate(resolved_parents):
            self.db.add(
                HosCommitParent(
                    org_id=user.org_id,
                    commit_id=commit.id,
                    parent_commit_id=pid,
                    parent_order=idx,
                )
            )

        branch.head_commit_id = commit.id
        self._write_audit(
            user=user,
            project_id=project_id,
            entity_type="commit",
            entity_id=commit.id,
            event_type=EVENT_COMMIT_CREATED,
            metadata={
                "branch_id": str(branch.id),
                "parent_commit_ids": [str(p) for p in resolved_parents],
                "tree_root_ref": root_ref,
            },
        )
        self._events.publish_commit_created(
            org_id=user.org_id,
            project_id=project_id,
            commit_id=commit.id,
            actor_id=user.id,
            metadata={
                "branch_id": str(branch.id),
                "commit_id": str(commit.id),
                "tree_root_ref": root_ref,
            },
        )

        if create_scene_snapshot:
            SceneGraphService(self.db).create_snapshot(
                user=user,
                project_id=project_id,
                commit_id=commit.id,
                snapshot_format=scene_snapshot_format,
            )

        return commit

    def list_object_snapshots(
        self, *, user: CurrentUser, project_id: uuid.UUID, commit_id: uuid.UUID
    ) -> list[HosObjectSnapshot]:
        self.get_commit(user=user, project_id=project_id, commit_id=commit_id)
        return list(
            self.db.scalars(
                select(HosObjectSnapshot)
                .where(
                    HosObjectSnapshot.org_id == user.org_id,
                    HosObjectSnapshot.project_id == project_id,
                    HosObjectSnapshot.commit_id == commit_id,
                )
                .order_by(HosObjectSnapshot.object_path.asc())
            )
        )

    def get_commit(self, *, user: CurrentUser, project_id: uuid.UUID, commit_id: uuid.UUID) -> HosCommit:
        self._require_project(project_id, user.org_id)
        commit = self.db.scalar(
            select(HosCommit).where(
                HosCommit.id == commit_id,
                HosCommit.org_id == user.org_id,
                HosCommit.project_id == project_id,
            )
        )
        if commit is None:
            raise ValueError("commit_not_found")
        return commit

    def log(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        branch_id: uuid.UUID,
        limit: int = 50,
    ) -> list[HosCommit]:
        self._require_project(project_id, user.org_id)
        _ = self.get_branch(user=user, project_id=project_id, branch_id=branch_id)
        return list(
            self.db.scalars(
                select(HosCommit)
                .where(
                    HosCommit.org_id == user.org_id,
                    HosCommit.project_id == project_id,
                    HosCommit.branch_id == branch_id,
                )
                .order_by(HosCommit.created_at.desc())
                .limit(limit)
            )
        )

    def diff(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        from_commit_id: uuid.UUID,
        to_commit_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        from_c = self.get_commit(user=user, project_id=project_id, commit_id=from_commit_id)
        to_c = self.get_commit(user=user, project_id=project_id, commit_id=to_commit_id)

        a = self._commit_state_map(from_c, user.org_id)
        b = self._commit_state_map(to_c, user.org_id)
        snapshot_model = bool(
            self._hnf.load_commit_snapshot_map(from_c.id, user.org_id)
            or self._hnf.load_commit_snapshot_map(to_c.id, user.org_id)
        )

        if not a and not b:
            a = {
                k: v
                for k, v in (from_c.tree or {}).items()
                if k not in ("scene_graph_snapshot", "tree_root_ref", "_hnf_validation_warnings")
            }
            b = {
                k: v
                for k, v in (to_c.tree or {}).items()
                if k not in ("scene_graph_snapshot", "tree_root_ref", "_hnf_validation_warnings")
            }

        paths = set(a.keys()) | set(b.keys())
        out: list[dict[str, Any]] = []
        for p in sorted(paths):
            av = a.get(p)
            bv = b.get(p)
            model = "object_snapshot" if snapshot_model else "tree"
            if av is None and bv is not None:
                out.append(
                    {
                        "path": p,
                        "change_type": "added",
                        "from_value": None,
                        "to_value": bv,
                        "model": model,
                    }
                )
            elif av is not None and bv is None:
                out.append(
                    {
                        "path": p,
                        "change_type": "removed",
                        "from_value": av,
                        "to_value": None,
                        "model": model,
                    }
                )
            elif av != bv:
                out.append(
                    {
                        "path": p,
                        "change_type": "modified",
                        "from_value": av,
                        "to_value": bv,
                        "model": model,
                    }
                )
        return out

    def merge(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        target_branch_id: uuid.UUID,
        source_branch_id: uuid.UUID,
    ) -> tuple[HosMerge, HosCommit | None, int]:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")
        self._require_project(project_id, user.org_id)

        target = self.get_branch(user=user, project_id=project_id, branch_id=target_branch_id)
        source = self.get_branch(user=user, project_id=project_id, branch_id=source_branch_id)

        ours_commit = (
            self.get_commit(user=user, project_id=project_id, commit_id=target.head_commit_id)
            if target.head_commit_id
            else None
        )
        theirs_commit = (
            self.get_commit(user=user, project_id=project_id, commit_id=source.head_commit_id)
            if source.head_commit_id
            else None
        )

        base_commit_id: uuid.UUID | None = None
        if ours_commit and theirs_commit:
            base_commit_id = self.find_lca(
                user=user,
                project_id=project_id,
                commit_a=ours_commit.id,
                commit_b=theirs_commit.id,
            )

        base_commit = (
            self.get_commit(user=user, project_id=project_id, commit_id=base_commit_id)
            if base_commit_id
            else None
        )

        ours_tree = self._commit_state_map(ours_commit, user.org_id) if ours_commit else {}
        theirs_tree = (
            self._commit_state_map(theirs_commit, user.org_id) if theirs_commit else {}
        )
        base_tree = self._commit_state_map(base_commit, user.org_id) if base_commit else {}

        merged_tree: dict[str, Any] = dict(ours_tree)
        conflicts: list[tuple[str, Any, Any, Any | None]] = []
        for path, theirs_value in theirs_tree.items():
            ours_value = ours_tree.get(path)
            base_value = base_tree.get(path)
            if ours_value is None:
                merged_tree[path] = theirs_value
            elif ours_value == theirs_value:
                merged_tree[path] = ours_value
            else:
                conflicts.append((path, base_value, ours_value, theirs_value))

        merge_row = HosMerge(
            org_id=user.org_id,
            project_id=project_id,
            target_branch_id=target.id,
            source_branch_id=source.id,
            target_head_commit_id=ours_commit.id if ours_commit else None,
            source_head_commit_id=theirs_commit.id if theirs_commit else None,
            status="conflicts" if conflicts else "merged",
            created_by=user.id,
        )
        self.db.add(merge_row)
        self.db.flush()

        for path, base_value, ours_value, theirs_value in conflicts:
            self.db.add(
                HosConflict(
                    org_id=user.org_id,
                    project_id=project_id,
                    merge_id=merge_row.id,
                    path=path,
                    base=base_value,
                    ours=ours_value,
                    theirs=theirs_value,
                    status="unresolved",
                )
            )

        result_commit: HosCommit | None = None
        if not conflicts:
            parent_ids: list[uuid.UUID] = []
            if ours_commit is not None:
                parent_ids.append(ours_commit.id)
            if theirs_commit is not None:
                parent_ids.append(theirs_commit.id)

            snapshot_payloads = [
                {
                    "object_path": path,
                    "hnf_type": (val or {}).get("hnf_type", "hardware.object"),
                    "object_id": val.get("object_id"),
                    "version_id": val.get("version_id"),
                    "version_num": val.get("version_num"),
                    "content_hash": val.get("content_hash"),
                    "domain": val.get("domain"),
                    "refs": val.get("refs") or [],
                    "properties": val.get("properties"),
                }
                for path, val in merged_tree.items()
            ]

            result_commit = self.commit(
                user=user,
                project_id=project_id,
                branch_id=target.id,
                message=f"Merge {source.name} into {target.name}",
                object_snapshots=snapshot_payloads,
                parent_commit_ids=parent_ids,
            )
            merge_row.result_commit_id = result_commit.id

        self._write_audit(
            user=user,
            project_id=project_id,
            entity_type="merge",
            entity_id=merge_row.id,
            event_type=EVENT_MERGE_CREATED,
            metadata={
                "target_branch_id": str(target.id),
                "source_branch_id": str(source.id),
                "status": merge_row.status,
                "conflict_count": len(conflicts),
                "base_commit_id": str(base_commit_id) if base_commit_id else None,
            },
        )
        self._events.publish_merge_created(
            org_id=user.org_id,
            project_id=project_id,
            merge_id=merge_row.id,
            actor_id=user.id,
            metadata={
                "merge_id": str(merge_row.id),
                "target_branch_id": str(target.id),
                "source_branch_id": str(source.id),
                "status": merge_row.status,
                "conflict_count": len(conflicts),
            },
        )
        if conflicts:
            self._events.publish_conflict_detected(
                org_id=user.org_id,
                project_id=project_id,
                merge_id=merge_row.id,
                actor_id=user.id,
                metadata={"merge_id": str(merge_row.id), "conflict_count": len(conflicts)},
            )

        return merge_row, result_commit, len(conflicts)

    def list_conflicts(
        self, *, user: CurrentUser, project_id: uuid.UUID, merge_id: uuid.UUID
    ) -> list[HosConflict]:
        self._require_project(project_id, user.org_id)
        merge_row = self.db.scalar(
            select(HosMerge.id).where(
                HosMerge.id == merge_id,
                HosMerge.org_id == user.org_id,
                HosMerge.project_id == project_id,
            )
        )
        if merge_row is None:
            raise ValueError("merge_not_found")
        return list(
            self.db.scalars(
                select(HosConflict)
                .where(
                    HosConflict.org_id == user.org_id,
                    HosConflict.project_id == project_id,
                    HosConflict.merge_id == merge_id,
                )
                .order_by(HosConflict.path.asc())
            )
        )

    def resolve_conflict(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        conflict_id: uuid.UUID,
        resolution: dict,
    ) -> HosConflict:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")
        self._require_project(project_id, user.org_id)
        conflict = self.db.scalar(
            select(HosConflict).where(
                HosConflict.id == conflict_id,
                HosConflict.org_id == user.org_id,
                HosConflict.project_id == project_id,
            )
        )
        if conflict is None:
            raise ValueError("conflict_not_found")

        conflict.resolution = resolution
        conflict.status = "resolved"
        conflict.resolved_at = _now()
        conflict.resolved_by = user.id

        self._write_audit(
            user=user,
            project_id=project_id,
            entity_type="conflict",
            entity_id=conflict.id,
            event_type="conflict_resolved",
            metadata={"path": conflict.path},
        )
        return conflict
