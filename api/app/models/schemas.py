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
