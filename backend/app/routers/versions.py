"""Asset versioning — upload new versions, view history, restore previous versions."""

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import AssetStatus, MediaAsset
from app.models.asset_version import AssetVersion

router = APIRouter(prefix="/assets/{asset_id}/versions", tags=["versioning"])

UPLOAD_ROOT = "/app/uploads"


class VersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    file_type: str
    file_size: int
    caption: str | None
    comment: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[VersionOut])
async def list_versions(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(AssetVersion)
        .where(AssetVersion.asset_id == asset_id)
        .order_by(AssetVersion.version_number.desc())
    )
    versions = result.scalars().all()
    return [
        VersionOut(
            id=v.id, version_number=v.version_number, file_type=v.file_type,
            file_size=v.file_size, caption=v.caption, comment=v.comment,
            created_at=str(v.created_at),
        )
        for v in versions
    ]


@router.post("", status_code=201)
async def upload_new_version(
    asset_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    comment: str | None = None,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Upload a new version of an asset. Saves current state as a version, replaces the file."""
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    # Get next version number
    max_ver = await db.execute(
        select(func.coalesce(func.max(AssetVersion.version_number), 0))
        .where(AssetVersion.asset_id == asset_id)
    )
    next_version = (max_ver.scalar() or 0) + 1

    # Save current state as a version
    version = AssetVersion(
        tenant_id=current_user.tenant_id,
        asset_id=asset_id,
        version_number=next_version,
        file_path=asset.file_path,
        file_type=asset.file_type,
        file_size=asset.file_size,
        caption=asset.caption,
        hashtags=asset.hashtags,
        uploaded_by=current_user.user_id,
        comment=comment or f"Version {next_version}",
    )
    db.add(version)

    # Save new file
    content = await file.read()
    tenant_dir = os.path.join(UPLOAD_ROOT, str(current_user.tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4()}_{file.filename}"
    new_path = os.path.join(tenant_dir, safe_name)
    with open(new_path, "wb") as f:
        f.write(content)

    # Update asset with new file
    asset.file_path = new_path
    asset.file_type = file.content_type or asset.file_type
    asset.file_size = len(content)
    asset.status = AssetStatus.draft  # Reset to draft
    asset.compliance_score = None
    asset.compliance_issues = None

    await db.commit()

    # Re-run AI pipeline in background
    from app.routers.assets import _run_ai_generation
    background_tasks.add_task(
        _run_ai_generation,
        asset_id, current_user.tenant_id, current_user.user_id,
        file.filename or "file", file.content_type or "image/jpeg", new_path,
    )

    return {"message": f"Version {next_version} created", "version_number": next_version}


@router.post("/{version_id}/restore", status_code=200)
async def restore_version(
    asset_id: uuid.UUID,
    version_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Restore an asset to a previous version."""
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    ver_result = await db.execute(
        select(AssetVersion).where(AssetVersion.id == version_id, AssetVersion.asset_id == asset_id)
    )
    version = ver_result.scalar_one_or_none()
    if not version:
        raise HTTPException(404, "Version not found")

    # Save current as new version first
    max_ver = await db.execute(
        select(func.coalesce(func.max(AssetVersion.version_number), 0))
        .where(AssetVersion.asset_id == asset_id)
    )
    next_version = (max_ver.scalar() or 0) + 1

    current_snapshot = AssetVersion(
        tenant_id=current_user.tenant_id,
        asset_id=asset_id,
        version_number=next_version,
        file_path=asset.file_path,
        file_type=asset.file_type,
        file_size=asset.file_size,
        caption=asset.caption,
        hashtags=asset.hashtags,
        uploaded_by=current_user.user_id,
        comment=f"Snapshot before restoring v{version.version_number}",
    )
    db.add(current_snapshot)

    # Restore from version
    asset.file_path = version.file_path
    asset.file_type = version.file_type
    asset.file_size = version.file_size
    asset.caption = version.caption
    asset.hashtags = version.hashtags
    asset.status = AssetStatus.draft

    await db.commit()

    return {"message": f"Restored to version {version.version_number}"}
