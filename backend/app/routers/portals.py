"""Client Portal management (admin) + public portal endpoints (no auth)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import UserContext, require_role
from app.core.tenant import get_tenant_db
from app.models.asset import AssetStatus, MediaAsset
from app.models.portal import ClientPortal, PortalCollection, PortalCollectionAsset

router = APIRouter(tags=["portals"])


# --- Schemas ---

class PortalCreate(BaseModel):
    name: str
    slug: str
    client_name: str
    client_logo_url: str | None = None
    primary_color: str = "#2563EB"
    welcome_message: str | None = None

class PortalOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    client_name: str
    client_logo_url: str | None
    primary_color: str
    welcome_message: str | None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}

class PortalUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    client_logo_url: str | None = None
    primary_color: str | None = None
    welcome_message: str | None = None
    is_active: bool | None = None

class CollectionCreate(BaseModel):
    name: str
    description: str | None = None

class CollectionOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_public: bool
    asset_count: int = 0
    created_at: datetime
    model_config = {"from_attributes": True}

class PublicPortalOut(BaseModel):
    name: str
    client_name: str
    client_logo_url: str | None
    primary_color: str
    welcome_message: str | None

class PublicAssetOut(BaseModel):
    id: uuid.UUID
    file_type: str
    caption: str | None
    hashtags: list[str] | None
    model_config = {"from_attributes": True}


# ============================================================
# ADMIN ENDPOINTS (authenticated, tenant-scoped)
# ============================================================

admin_router = APIRouter(prefix="/portals", tags=["portals"])


@admin_router.get("", response_model=list[PortalOut])
async def list_portals(
    limit: int = 50,
    offset: int = 0,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    limit = min(limit, 200)
    result = await db.execute(
        select(ClientPortal).order_by(ClientPortal.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()


@admin_router.post("", response_model=PortalOut, status_code=201)
async def create_portal(
    body: PortalCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Check slug uniqueness
    existing = await db.execute(select(ClientPortal).where(ClientPortal.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Slug already in use")

    portal = ClientPortal(
        tenant_id=current_user.tenant_id,
        name=body.name,
        slug=body.slug,
        client_name=body.client_name,
        client_logo_url=body.client_logo_url,
        primary_color=body.primary_color,
        welcome_message=body.welcome_message,
    )
    db.add(portal)
    await db.commit()
    await db.refresh(portal)
    return portal


@admin_router.patch("/{portal_id}", response_model=PortalOut)
async def update_portal(
    portal_id: uuid.UUID,
    body: PortalUpdate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ClientPortal).where(ClientPortal.id == portal_id))
    portal = result.scalar_one_or_none()
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(portal, field, value)

    await db.commit()
    await db.refresh(portal)
    return portal


@admin_router.delete("/{portal_id}", status_code=204)
async def delete_portal(
    portal_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ClientPortal).where(ClientPortal.id == portal_id))
    portal = result.scalar_one_or_none()
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    await db.delete(portal)
    await db.commit()
    return None


# --- Collections ---

@admin_router.post("/{portal_id}/collections", response_model=CollectionOut, status_code=201)
async def create_collection(
    portal_id: uuid.UUID,
    body: CollectionCreate,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(select(ClientPortal).where(ClientPortal.id == portal_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portal not found")

    coll = PortalCollection(
        tenant_id=current_user.tenant_id,
        portal_id=portal_id,
        name=body.name,
        description=body.description,
    )
    db.add(coll)
    await db.commit()
    await db.refresh(coll)
    return CollectionOut(
        id=coll.id, name=coll.name, description=coll.description,
        is_public=coll.is_public, asset_count=0, created_at=coll.created_at,
    )


@admin_router.post("/{portal_id}/collections/{collection_id}/assets/{asset_id}", status_code=201)
async def add_asset_to_collection(
    portal_id: uuid.UUID,
    collection_id: uuid.UUID,
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Verify asset is approved
    asset_result = await db.execute(select(MediaAsset).where(MediaAsset.id == asset_id))
    asset = asset_result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.status != AssetStatus.approved:
        raise HTTPException(status_code=400, detail="Only approved assets can be added to portals")

    link = PortalCollectionAsset(collection_id=collection_id, asset_id=asset_id)
    db.add(link)
    await db.commit()
    return {"message": "Asset added to collection"}


@admin_router.delete("/{portal_id}/collections/{collection_id}/assets/{asset_id}", status_code=204)
async def remove_asset_from_collection(
    portal_id: uuid.UUID,
    collection_id: uuid.UUID,
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(PortalCollectionAsset).where(
            PortalCollectionAsset.collection_id == collection_id,
            PortalCollectionAsset.asset_id == asset_id,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Asset not in collection")
    await db.delete(link)
    await db.commit()
    return None


# ============================================================
# PUBLIC ENDPOINTS (no auth — client-facing)
# ============================================================

public_router = APIRouter(prefix="/p", tags=["portal-public"])


@public_router.get("/{slug}", response_model=PublicPortalOut)
async def get_public_portal(slug: str, db: AsyncSession = Depends(get_db)):
    """Public: get portal info by slug. No authentication required."""
    result = await db.execute(
        select(ClientPortal).where(ClientPortal.slug == slug, ClientPortal.is_active.is_(True))
    )
    portal = result.scalar_one_or_none()
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")
    return PublicPortalOut(
        name=portal.name,
        client_name=portal.client_name,
        client_logo_url=portal.client_logo_url,
        primary_color=portal.primary_color,
        welcome_message=portal.welcome_message,
    )


@public_router.get("/{slug}/collections")
async def get_public_collections(slug: str, db: AsyncSession = Depends(get_db)):
    """Public: list collections in a portal."""
    result = await db.execute(
        select(ClientPortal).where(ClientPortal.slug == slug, ClientPortal.is_active.is_(True))
    )
    portal = result.scalar_one_or_none()
    if not portal:
        raise HTTPException(status_code=404, detail="Portal not found")

    now = datetime.now(timezone.utc)
    colls = await db.execute(
        select(PortalCollection)
        .where(
            PortalCollection.portal_id == portal.id,
            PortalCollection.is_public.is_(True),
            (PortalCollection.expires_at.is_(None)) | (PortalCollection.expires_at > now),
        )
        .options(selectinload(PortalCollection.assets))
    )
    collections = colls.scalars().all()

    return [
        {
            "id": str(c.id),
            "name": c.name,
            "description": c.description,
            "asset_count": len(c.assets),
        }
        for c in collections
    ]


@public_router.get("/{slug}/collections/{collection_id}/assets", response_model=list[PublicAssetOut])
async def get_public_collection_assets(
    slug: str,
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Public: list approved assets in a collection."""
    # Verify portal exists and is active
    portal_result = await db.execute(
        select(ClientPortal).where(ClientPortal.slug == slug, ClientPortal.is_active.is_(True))
    )
    if not portal_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Portal not found")

    # Get assets via join
    result = await db.execute(
        select(MediaAsset)
        .join(PortalCollectionAsset, PortalCollectionAsset.asset_id == MediaAsset.id)
        .where(
            PortalCollectionAsset.collection_id == collection_id,
            MediaAsset.status == AssetStatus.approved,
        )
    )
    return result.scalars().all()
