"""Auto-resize endpoints — generate social media format variants from assets."""

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import MediaAsset
from app.models.asset_variant import AssetVariant
from app.services.resize_service import FORMATS

router = APIRouter(prefix="/assets/{asset_id}", tags=["resize"])


class ResizeRequest(BaseModel):
    formats: list[str] = ["all"]


class VariantOut(BaseModel):
    id: uuid.UUID
    format_name: str
    width: int
    height: int
    file_size: int
    created_at: str

    class Config:
        from_attributes = True


@router.post("/resize", status_code=202)
async def resize_asset(
    asset_id: uuid.UUID,
    body: ResizeRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Generate resized variants for an asset. Runs in background."""
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not asset.file_type.startswith("image/"):
        raise HTTPException(400, "Resize only supports images")

    # Validate format names
    format_names = body.formats
    if format_names != ["all"]:
        invalid = [f for f in format_names if f not in FORMATS]
        if invalid:
            raise HTTPException(400, f"Unknown formats: {', '.join(invalid)}. Available: {', '.join(FORMATS.keys())}")

    from app.services.resize_service import generate_all_variants
    background_tasks.add_task(
        generate_all_variants,
        asset_id, asset.file_path, current_user.tenant_id,
        current_user.user_id, format_names,
    )

    return {
        "message": "Resize started",
        "formats": list(FORMATS.keys()) if format_names == ["all"] else format_names,
    }


@router.get("/variants", response_model=list[VariantOut])
async def list_variants(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """List all generated variants for an asset."""
    result = await db.execute(
        select(AssetVariant)
        .where(AssetVariant.asset_id == asset_id)
        .order_by(AssetVariant.format_name)
    )
    variants = result.scalars().all()
    return [
        VariantOut(
            id=v.id, format_name=v.format_name, width=v.width,
            height=v.height, file_size=v.file_size, created_at=str(v.created_at),
        )
        for v in variants
    ]


@router.get("/variants/{format_name}/file")
async def get_variant_file(
    asset_id: uuid.UUID,
    format_name: str,
    token: str = Query(None),
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Serve a specific variant file."""
    result = await db.execute(
        select(AssetVariant).where(
            AssetVariant.asset_id == asset_id,
            AssetVariant.format_name == format_name,
        )
    )
    variant = result.scalar_one_or_none()
    if not variant:
        raise HTTPException(404, "Variant not found")
    if not os.path.exists(variant.file_path):
        raise HTTPException(404, "Variant file not found on disk")

    return FileResponse(variant.file_path, media_type="image/webp")


@router.get("/formats")
async def list_available_formats():
    """List all available resize formats and their dimensions."""
    return {name: {"width": f["width"], "height": f["height"], "name": f["name"]} for name, f in FORMATS.items()}
