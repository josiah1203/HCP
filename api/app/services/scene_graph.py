from __future__ import annotations

import uuid
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.auth.rbac import role_at_least
from app.models.db import (
    ComponentIdentity,
    HosAuditLog,
    HosCommit,
    Project,
    SceneGraphEdge,
    SceneGraphNode,
    SceneGraphSnapshot,
)
from app.services.event_taxonomy import EVENT_SCENE_GRAPH_SNAPSHOT_CREATED
from app.services.events import EventPublisher

_VALID_SNAPSHOT_FORMATS = frozenset({"json", "glb", "octree+json"})


def build_protocol_snapshot(
    *,
    nodes: list[SceneGraphNode],
    edges: list[SceneGraphEdge],
    snapshot_format: str = "json",
) -> dict[str, Any]:
    """Align persisted snapshot JSON with hcp-sidecar-scenegraph.v0 shapes."""
    fmt = snapshot_format if snapshot_format in _VALID_SNAPSHOT_FORMATS else "json"
    legacy_nodes = [
        {
            "node_key": n.node_key,
            "nodeId": n.node_key,
            "identity_id": str(n.identity_id) if n.identity_id else None,
            "transform": n.transform or {},
            "metadata": n.metadata_ or None,
        }
        for n in nodes
    ]
    legacy_edges = [
        {
            "edge_key": e.edge_key,
            "edgeId": e.edge_key,
            "from_node_key": e.from_node_key,
            "fromNodeId": e.from_node_key,
            "to_node_key": e.to_node_key,
            "toNodeId": e.to_node_key,
            "constraint_type": e.constraint_type,
            "edgeType": e.constraint_type,
            "payload": e.payload or None,
        }
        for e in edges
    ]
    return {
        "format": fmt,
        "protocol": "hcp.rpc.v0",
        "nodes": legacy_nodes,
        "edges": legacy_edges,
        "rpc": {
            "nodes": [
                {
                    "nodeId": n.node_key,
                    "nodeType": (n.metadata_ or {}).get("node_type", "node"),
                    "attributes": {
                        "transform": n.transform or {},
                        **({} if not n.metadata_ else dict(n.metadata_)),
                    },
                }
                for n in nodes
            ],
            "edges": [
                {
                    "edgeId": e.edge_key,
                    "fromNodeId": e.from_node_key,
                    "toNodeId": e.to_node_key,
                    "edgeType": e.constraint_type,
                    "attributes": e.payload or {},
                }
                for e in edges
            ],
        },
    }


class SceneGraphService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._events = EventPublisher(db)

    def _require_project(self, project_id: uuid.UUID, org_id: uuid.UUID) -> Project:
        project = self.db.scalar(
            select(Project).where(Project.id == project_id, Project.org_id == org_id)
        )
        if project is None:
            raise ValueError("project_not_found")
        return project

    def _require_editor(self, user: CurrentUser) -> None:
        if not role_at_least(user.role, "editor"):
            raise ValueError("forbidden")

    def create_component_identity(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        canonical_key: str,
        source_tool: str | None = None,
        source_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ComponentIdentity:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)
        row = ComponentIdentity(
            org_id=user.org_id,
            project_id=project_id,
            canonical_key=canonical_key,
            source_tool=source_tool,
            source_ref=source_ref,
            metadata_=metadata,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def get_component_identity(
        self, *, user: CurrentUser, project_id: uuid.UUID, identity_id: uuid.UUID
    ) -> ComponentIdentity:
        self._require_project(project_id, user.org_id)
        row = self.db.scalar(
            select(ComponentIdentity).where(
                ComponentIdentity.id == identity_id,
                ComponentIdentity.org_id == user.org_id,
                ComponentIdentity.project_id == project_id,
            )
        )
        if row is None:
            raise ValueError("component_identity_not_found")
        return row

    def list_component_identities(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ComponentIdentity]:
        self._require_project(project_id, user.org_id)
        return list(
            self.db.scalars(
                select(ComponentIdentity)
                .where(
                    ComponentIdentity.org_id == user.org_id,
                    ComponentIdentity.project_id == project_id,
                )
                .order_by(ComponentIdentity.created_at.asc())
                .limit(limit)
                .offset(offset)
            )
        )

    def upsert_nodes(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        nodes: Iterable[dict[str, Any]],
    ) -> list[SceneGraphNode]:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)

        out: list[SceneGraphNode] = []
        for n in nodes:
            node_key = str(n["node_key"])
            identity_id = n.get("identity_id")
            transform = n.get("transform") or {}
            metadata = n.get("metadata")

            existing = self.db.scalar(
                select(SceneGraphNode).where(
                    SceneGraphNode.org_id == user.org_id,
                    SceneGraphNode.project_id == project_id,
                    SceneGraphNode.node_key == node_key,
                )
            )
            if existing is not None:
                existing.identity_id = identity_id
                existing.transform = transform
                existing.metadata_ = metadata
                out.append(existing)
                continue

            row = SceneGraphNode(
                org_id=user.org_id,
                project_id=project_id,
                node_key=node_key,
                identity_id=identity_id,
                transform=transform,
                metadata_=metadata,
            )
            self.db.add(row)
            try:
                self.db.flush()
                out.append(row)
            except IntegrityError:
                self.db.rollback()
                existing = self.db.scalar(
                    select(SceneGraphNode).where(
                        SceneGraphNode.org_id == user.org_id,
                        SceneGraphNode.project_id == project_id,
                        SceneGraphNode.node_key == node_key,
                    )
                )
                if existing is None:
                    raise
                existing.identity_id = identity_id
                existing.transform = transform
                existing.metadata_ = metadata
                out.append(existing)
        return out

    def upsert_edges(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        edges: Iterable[dict[str, Any]],
    ) -> list[SceneGraphEdge]:
        self._require_editor(user)
        self._require_project(project_id, user.org_id)

        out: list[SceneGraphEdge] = []
        for e in edges:
            edge_key = str(e["edge_key"])
            from_node_key = str(e["from_node_key"])
            to_node_key = str(e["to_node_key"])
            constraint_type = str(e["constraint_type"])
            payload = e.get("payload")

            existing = self.db.scalar(
                select(SceneGraphEdge).where(
                    SceneGraphEdge.org_id == user.org_id,
                    SceneGraphEdge.project_id == project_id,
                    SceneGraphEdge.edge_key == edge_key,
                )
            )
            if existing is not None:
                existing.from_node_key = from_node_key
                existing.to_node_key = to_node_key
                existing.constraint_type = constraint_type
                existing.payload = payload
                out.append(existing)
                continue

            row = SceneGraphEdge(
                org_id=user.org_id,
                project_id=project_id,
                edge_key=edge_key,
                from_node_key=from_node_key,
                to_node_key=to_node_key,
                constraint_type=constraint_type,
                payload=payload,
            )
            self.db.add(row)
            try:
                self.db.flush()
                out.append(row)
            except IntegrityError:
                self.db.rollback()
                existing = self.db.scalar(
                    select(SceneGraphEdge).where(
                        SceneGraphEdge.org_id == user.org_id,
                        SceneGraphEdge.project_id == project_id,
                        SceneGraphEdge.edge_key == edge_key,
                    )
                )
                if existing is None:
                    raise
                existing.from_node_key = from_node_key
                existing.to_node_key = to_node_key
                existing.constraint_type = constraint_type
                existing.payload = payload
                out.append(existing)
        return out

    def create_snapshot(
        self,
        *,
        user: CurrentUser,
        project_id: uuid.UUID,
        commit_id: uuid.UUID,
        snapshot_format: str = "json",
    ) -> tuple[SceneGraphSnapshot, bool]:
        self._require_editor(user)
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

        existing = self.db.scalar(
            select(SceneGraphSnapshot).where(
                SceneGraphSnapshot.org_id == user.org_id,
                SceneGraphSnapshot.project_id == project_id,
                SceneGraphSnapshot.commit_id == commit_id,
            )
        )
        if existing is not None:
            return existing, False

        nodes = list(
            self.db.scalars(
                select(SceneGraphNode).where(
                    SceneGraphNode.org_id == user.org_id,
                    SceneGraphNode.project_id == project_id,
                )
            )
        )
        edges = list(
            self.db.scalars(
                select(SceneGraphEdge).where(
                    SceneGraphEdge.org_id == user.org_id,
                    SceneGraphEdge.project_id == project_id,
                )
            )
        )

        snapshot_json = build_protocol_snapshot(
            nodes=nodes, edges=edges, snapshot_format=snapshot_format
        )

        row = SceneGraphSnapshot(
            org_id=user.org_id,
            project_id=project_id,
            commit_id=commit_id,
            snapshot=snapshot_json,
            snapshot_format=snapshot_format
            if snapshot_format in _VALID_SNAPSHOT_FORMATS
            else "json",
            created_by=user.id,
        )
        self.db.add(row)
        try:
            self.db.flush()
            created = True
        except IntegrityError:
            self.db.rollback()
            existing = self.db.scalar(
                select(SceneGraphSnapshot).where(
                    SceneGraphSnapshot.org_id == user.org_id,
                    SceneGraphSnapshot.project_id == project_id,
                    SceneGraphSnapshot.commit_id == commit_id,
                )
            )
            if existing is None:
                raise
            row = existing
            created = False

        tree = dict(commit.tree or {})
        tree["scene_graph_snapshot"] = {
            "snapshot_id": str(row.id),
            "snapshot_format": row.snapshot_format,
        }
        commit.tree = tree

        self.db.add(
            HosAuditLog(
                org_id=user.org_id,
                project_id=project_id,
                entity_type="scene_graph_snapshot",
                entity_id=row.id,
                event_type=EVENT_SCENE_GRAPH_SNAPSHOT_CREATED,
                actor_id=user.id,
                actor_email=user.email,
                metadata_={"commit_id": str(commit_id), "snapshot_id": str(row.id)},
            )
        )

        if created:
            self._events.publish(
                org_id=user.org_id,
                project_id=project_id,
                event_type=EVENT_SCENE_GRAPH_SNAPSHOT_CREATED,
                dedupe_key=f"scene_graph_snapshot:{commit_id}",
                actor_id=user.id,
                source="scene_graph",
                metadata={"commit_id": str(commit_id), "snapshot_id": str(row.id)},
            )

        return row, created

