from __future__ import annotations
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CurrentUser,
    get_current_user,
    require_admin,
    require_upload_permission,
)
from app.dependencies import get_db
from app.models.schemas import (
    BundleUploadResponse,
    DownloadResponse,
    ObjectOut,
    PromoteRequest,
    UploadResponse,
    VersionOut,
)
from app.services.bundles import BundleIngestService
from app.services.objects import ObjectService

router = APIRouter(prefix="/v1/objects", tags=["objects"])


@router.post(
    "/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED
)
async def upload_object(
    file: UploadFile = File(...),
    project_id: uuid.UUID = Form(...),
    name: str = Form(...),
    description: str | None = Form(None),
    object_id: uuid.UUID | None = Form(None),
    source_tool: str | None = Form(None),
    source_tool_version: str | None = Form(None),
    domain: str | None = Form(None),
    derived_from_version_id: uuid.UUID | None = Form(None),
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": "Filename required"},
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": "Empty file"},
        )

    service = ObjectService(db)
    try:
        hw_object, version, deduplicated = service.upload(
            user=user,
            project_id=project_id,
            file_bytes=file_bytes,
            filename=file.filename,
            name=name,
            description=description,
            object_id=object_id,
            content_type=file.content_type or "application/octet-stream",
            source_tool=source_tool,
            source_tool_version=source_tool_version,
            domain=domain,
            derived_from_version_id=derived_from_version_id,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "Project not found"},
            ) from exc
        if code == "object_not_found":
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "Object not found"},
            ) from exc
        if code == "derived_from_version_not_found":
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "not_found",
                    "message": "Derived-from version not found",
                },
            ) from exc
        raise

    db.commit()
    db.refresh(hw_object)
    db.refresh(version)

    version_out = VersionOut(**service.version_to_schema(version, hw_object.project_id))
    return UploadResponse(
        object=ObjectOut(
            id=hw_object.id,
            org_id=hw_object.org_id,
            project_id=hw_object.project_id,
            name=hw_object.name,
            object_type=hw_object.object_type,
            domain=hw_object.domain,
            source_tool=hw_object.source_tool,
            representation=hw_object.representation,
            created_at=hw_object.created_at,
            latest_version=version_out,
        ),
        version=version_out,
        deduplicated=deduplicated,
    )


@router.post(
    "/upload-bundle",
    response_model=BundleUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_bundle(
    file: UploadFile = File(...),
    project_id: uuid.UUID = Form(...),
    name: str | None = Form(None),
    description: str | None = Form(None),
    user: CurrentUser = Depends(require_upload_permission),
    db: Session = Depends(get_db),
) -> BundleUploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": "Filename required"},
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": "Empty file"},
        )

    service = BundleIngestService(db)
    try:
        result = service.ingest(
            user=user,
            project_id=project_id,
            bundle_bytes=file_bytes,
            bundle_filename=file.filename,
            bundle_name=name,
            description=description,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "project_not_found":
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "Project not found"},
            ) from exc
        if code == "invalid_bundle":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "Invalid bundle archive or manifest",
                },
            ) from exc
        raise

    db.commit()
    return BundleUploadResponse(**result)


@router.get("/{object_id}", response_model=ObjectOut)
def get_object(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ObjectOut:
    service = ObjectService(db)
    hw_object = service.get_object(object_id, user.org_id)
    if hw_object is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )

    versions = service.list_versions(object_id, user.org_id)
    latest = versions[0] if versions else None
    latest_out = (
        VersionOut(**service.version_to_schema(latest, hw_object.project_id))
        if latest
        else None
    )

    return ObjectOut(
        id=hw_object.id,
        org_id=hw_object.org_id,
        project_id=hw_object.project_id,
        name=hw_object.name,
        object_type=hw_object.object_type,
        domain=hw_object.domain,
        source_tool=hw_object.source_tool,
        representation=hw_object.representation,
        created_at=hw_object.created_at,
        latest_version=latest_out,
    )


@router.get("/{object_id}/versions", response_model=dict)
def list_versions(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = ObjectService(db)
    hw_object = service.get_object(object_id, user.org_id)
    if hw_object is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )

    versions = service.list_versions(object_id, user.org_id)
    return {
        "data": [
            VersionOut(**service.version_to_schema(v, hw_object.project_id))
            for v in versions
        ],
    }


@router.get("/{object_id}/versions/{version_num}", response_model=VersionOut)
def get_version(
    object_id: uuid.UUID,
    version_num: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionOut:
    service = ObjectService(db)
    hw_object = service.get_object(object_id, user.org_id)
    if hw_object is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )

    version = service.get_version(object_id, version_num, user.org_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Version not found"},
        )

    return VersionOut(**service.version_to_schema(version, hw_object.project_id))


@router.get(
    "/{object_id}/versions/{version_num}/download", response_model=DownloadResponse
)
def download_version(
    object_id: uuid.UUID,
    version_num: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DownloadResponse:
    from app.config import settings

    service = ObjectService(db)
    version = service.get_version(object_id, version_num, user.org_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Version not found"},
        )

    url = service.presigned_download(version)
    return DownloadResponse(
        url=url, expires_in_seconds=settings.presigned_url_expiry_seconds
    )


@router.get("/{object_id}/versions/{version_num}/parsed")
def get_parsed(
    object_id: uuid.UUID,
    version_num: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    service = ObjectService(db)
    version = service.get_version(object_id, version_num, user.org_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Version not found"},
        )
    if version.parse_status != "complete":
        raise HTTPException(
            status_code=404,
            detail={
                "code": "not_found",
                "message": f"Parsed output not available (status={version.parse_status})",
            },
        )
    parsed = service.get_parsed_json(version)
    if parsed is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Parsed output not found"},
        )
    return parsed


@router.post("/{object_id}/versions/{version_num}/promote", response_model=VersionOut)
def promote_version(
    object_id: uuid.UUID,
    version_num: int,
    body: PromoteRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionOut:
    service = ObjectService(db)
    hw_object = service.get_object(object_id, user.org_id)
    if hw_object is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )

    version = service.get_version(object_id, version_num, user.org_id)
    if version is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Version not found"},
        )

    try:
        version = service.promote(
            user=user,
            version=version,
            target_state=body.target_state,
            comment=body.comment,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_transition":
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "Invalid lifecycle transition",
                },
            ) from exc
        if code == "forbidden":
            raise HTTPException(
                status_code=403,
                detail={"code": "forbidden", "message": "Insufficient role"},
            ) from exc
        raise

    db.commit()
    db.refresh(version)
    return VersionOut(**service.version_to_schema(version, hw_object.project_id))


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_object(
    object_id: uuid.UUID,
    user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    service = ObjectService(db)
    hw_object = service.get_object(object_id, user.org_id)
    if hw_object is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Object not found"}
        )
    try:
        service.soft_delete(hw_object, user)
    except ValueError as exc:
        if str(exc) == "forbidden":
            raise HTTPException(
                status_code=403,
                detail={"code": "forbidden", "message": "Admin required"},
            ) from exc
        raise
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
