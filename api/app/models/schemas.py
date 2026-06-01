from __future__ import annotations
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Pagination(BaseModel):
    page: int = 1
    per_page: int = 20
    total: int = 0
    total_pages: int = 0


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    role: str
    org_id: uuid.UUID

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class VersionOut(BaseModel):
    id: uuid.UUID
    object_id: uuid.UUID
    version_num: int
    filename: str
    content_hash: str
    file_size_bytes: int
    parse_status: str
    lifecycle_state: str
    description: str | None
    source_tool: str | None = None
    source_tool_version: str | None = None
    domain: str | None = None
    representation: str | None = None
    created_at: datetime
    hcp_uri: str | None = None

    model_config = {"from_attributes": True}


class ObjectOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    object_type: str
    domain: str | None = None
    source_tool: str | None = None
    representation: str | None = None
    created_at: datetime
    latest_version: VersionOut | None = None

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    object: ObjectOut
    version: VersionOut
    deduplicated: bool = False


class BundleArtifactOut(BaseModel):
    path: str
    object_id: uuid.UUID
    version_id: uuid.UUID
    version_num: int


class BundleUploadResponse(BaseModel):
    release: str | None = None
    source_tool: str | None = None
    artifacts: list[BundleArtifactOut]
    relationships_applied: int = 0


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int


class HealthCheck(BaseModel):
    status: str
    checks: dict[str, str] = Field(default_factory=dict)


class PromoteRequest(BaseModel):
    target_state: str
    comment: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] | None = None


class ApiKeyCreated(BaseModel):
    key: str
    key_id: uuid.UUID
    name: str
    prefix: str


class ApiKeyOut(BaseModel):
    key_id: uuid.UUID
    name: str
    prefix: str
    last_used_at: datetime | None = None


class GraphLinkCreate(BaseModel):
    from_object_id: uuid.UUID
    to_object_id: uuid.UUID
    relationship_type: str
    metadata: dict | None = None


class GraphQueryRequest(BaseModel):
    cypher: str
    params: dict | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class HosBranchCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    from_commit_id: uuid.UUID | None = None


class HosBranchOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    head_commit_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HosObjectSnapshotIn(BaseModel):
    object_path: str
    object_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    content_hash: str | None = None
    hnf_type: str
    domain: str | None = None
    refs: list[str] = Field(default_factory=list)
    properties: dict = Field(default_factory=dict)
    snapshot_version: int = Field(default=1, ge=1)


class HosObjectSnapshotOut(BaseModel):
    id: uuid.UUID
    object_path: str
    object_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    content_hash: str | None = None
    hnf_type: str
    domain: str | None = None
    refs: list[str] = Field(default_factory=list)
    properties: dict = Field(default_factory=dict)
    snapshot_version: int

    model_config = {"from_attributes": True}


class HosObjectSnapshotListResponse(BaseModel):
    data: list[HosObjectSnapshotOut]


class HosCommitCreate(BaseModel):
    project_id: uuid.UUID
    branch_id: uuid.UUID
    message: str
    tree: dict = Field(default_factory=dict)
    object_snapshots: list[HosObjectSnapshotIn] | None = None
    tree_root_ref: str | None = None
    parent_commit_ids: list[uuid.UUID] | None = None
    create_scene_snapshot: bool = False
    scene_snapshot_format: str = "json"


class HosCommitOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    message: str
    tree: dict
    tree_root_ref: str | None = None
    created_by: uuid.UUID
    created_at: datetime
    parent_commit_ids: list[uuid.UUID] = Field(default_factory=list)


class HosLogResponse(BaseModel):
    data: list[HosCommitOut]


class HosDiffRequest(BaseModel):
    project_id: uuid.UUID
    from_commit_id: uuid.UUID
    to_commit_id: uuid.UUID


class HosDiffEntry(BaseModel):
    path: str
    change_type: str
    from_value: dict | None = None
    to_value: dict | None = None
    model: str | None = None


class HosDiffResponse(BaseModel):
    data: list[HosDiffEntry]


class HosMergeRequest(BaseModel):
    project_id: uuid.UUID
    target_branch_id: uuid.UUID
    source_branch_id: uuid.UUID


class HosMergeOut(BaseModel):
    merge_id: uuid.UUID
    status: str
    result_commit_id: uuid.UUID | None = None
    conflict_count: int = 0


class HosConflictOut(BaseModel):
    id: uuid.UUID
    path: str
    base: dict | None = None
    ours: dict | None = None
    theirs: dict | None = None
    resolution: dict | None = None
    status: str

    model_config = {"from_attributes": True}


class HosConflictListResponse(BaseModel):
    data: list[HosConflictOut]


class HosConflictResolveRequest(BaseModel):
    resolution: dict


class EventOut(BaseModel):
    seq: int
    event_id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    event_type: str
    dedupe_key: str
    actor_id: uuid.UUID | None = None
    source: str
    metadata: dict | None = Field(default=None, alias="metadata_")
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class EventPublishRequest(BaseModel):
    project_id: uuid.UUID
    event_type: str
    dedupe_key: str
    metadata: dict | None = None
    actor_id: uuid.UUID | None = None
    source: str | None = None
    event_id: uuid.UUID | None = None


class EventPublishResponse(BaseModel):
    event: EventOut
    deduped: bool = False


class EventPollResponse(BaseModel):
    data: list[EventOut]
    next_cursor: int
    has_more: bool = False


class ComponentIdentityCreate(BaseModel):
    project_id: uuid.UUID
    canonical_key: str
    source_tool: str | None = None
    source_ref: str | None = None
    metadata: dict | None = None


class ComponentIdentityOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    canonical_key: str
    source_tool: str | None = None
    source_ref: str | None = None
    metadata: dict | None = Field(default=None, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class ComponentIdentityListResponse(BaseModel):
    data: list[ComponentIdentityOut]


class SceneGraphNodeUpsert(BaseModel):
    node_key: str
    identity_id: uuid.UUID | None = None
    transform: dict = Field(default_factory=dict)
    metadata: dict | None = None


class SceneGraphNodeOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    node_key: str
    identity_id: uuid.UUID | None = None
    transform: dict
    metadata: dict | None = Field(default=None, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SceneGraphNodeUpsertRequest(BaseModel):
    project_id: uuid.UUID
    nodes: list[SceneGraphNodeUpsert]


class SceneGraphNodeUpsertResponse(BaseModel):
    data: list[SceneGraphNodeOut]


class SceneGraphEdgeUpsert(BaseModel):
    edge_key: str
    from_node_key: str
    to_node_key: str
    constraint_type: str
    payload: dict | None = None


class SceneGraphEdgeOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    edge_key: str
    from_node_key: str
    to_node_key: str
    constraint_type: str
    payload: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SceneGraphEdgeUpsertRequest(BaseModel):
    project_id: uuid.UUID
    edges: list[SceneGraphEdgeUpsert]


class SceneGraphEdgeUpsertResponse(BaseModel):
    data: list[SceneGraphEdgeOut]


class SceneGraphSnapshotCreateRequest(BaseModel):
    project_id: uuid.UUID
    commit_id: uuid.UUID
    snapshot_format: str = "json"
    snapshot_format: str = "json"


class SceneGraphSnapshotOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    commit_id: uuid.UUID
    snapshot: dict
    snapshot_format: str = "json"
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SceneGraphSnapshotResponse(BaseModel):
    snapshot: SceneGraphSnapshotOut
    deduped: bool = False


class PresenceHeartbeatRequest(BaseModel):
    project_id: uuid.UUID
    session_id: str
    resource_path: str | None = None
    domain: str | None = None
    client_meta: dict | None = None


class PresenceOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    user_id: uuid.UUID
    session_id: str
    resource_path: str | None = None
    domain: str | None = None
    client_meta: dict | None = None
    last_heartbeat_at: datetime

    model_config = {"from_attributes": True}


class PresenceHeartbeatResponse(BaseModel):
    presence: PresenceOut
    joined: bool = False


class PresenceListResponse(BaseModel):
    data: list[PresenceOut]


class PresenceLeaveRequest(BaseModel):
    project_id: uuid.UUID
    session_id: str


class PresenceLeaveResponse(BaseModel):
    left: bool


class SoftLockAcquireRequest(BaseModel):
    project_id: uuid.UUID
    resource_path: str
    session_id: str | None = None
    ttl_seconds: int = Field(default=300, ge=30, le=3600)


class SoftLockOut(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    resource_path: str
    holder_user_id: uuid.UUID
    holder_session_id: str | None = None
    advisory: bool
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SoftLockAcquireResponse(BaseModel):
    lock: SoftLockOut
    acquired: bool
    held_by_other: bool = False
    existing_lock: SoftLockOut | None = None


class SoftLockListResponse(BaseModel):
    data: list[SoftLockOut]


class CrossDomainAlertRequest(BaseModel):
    project_id: uuid.UUID
    alert_id: str
    source_domain: str
    target_domain: str
    severity: str = "info"
    message: str
    context: dict | None = None


class CrossDomainAlertResponse(BaseModel):
    alert_id: str
    published: bool = True


class CrdtOperationRequest(BaseModel):
    project_id: uuid.UUID
    document_id: str
    operation_id: str
    envelope: dict


class CrdtOperationResponse(BaseModel):
    document_id: str
    operation_id: str
    envelope: dict
    accepted: bool = True
