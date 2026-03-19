import logging
import os
import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UserContext, get_current_user, require_role
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.retry import retry
from app.core.tenant import get_tenant_db
from app.models.asset import AssetStatus, MediaAsset
from app.models.ai_usage import AIActionType
from app.schemas.asset import AssetListResponse, AssetOut, AssetUpdate
from app.core.tracing import trace_llm_call
from app.services.ai_service import ai_service
from app.services.ai_usage import log_ai_usage
from app.services.automation_engine import on_event
from app.services.thumbnail_service import generate_thumbnail
from app.services.webhook_service import emit_event

logger = logging.getLogger(__name__)

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> UserContext | None:
    """Like get_current_user but returns None instead of 401."""
    if not credentials:
        return None
    from app.core.security import decode_token
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        return None
    return UserContext(
        user_id=uuid.UUID(payload["sub"]),
        tenant_id=uuid.UUID(payload["tenant_id"]),
        role=payload["role"],
    )


router = APIRouter(prefix="/assets", tags=["assets"])

UPLOAD_ROOT = "/app/uploads"
ALLOWED_MIME_PREFIXES = ("image/", "video/")
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp4", ".mov", ".avi", ".mkv",
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@retry(max_retries=3, base_delay=1.0)
async def _run_ai_generation(
    asset_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    file_type: str,
    file_path: str,
):
    """Background task: generate caption + hashtags via AI and update the asset."""
    from app.core.database import async_session_factory
    from app.core.rate_limit import check_ai_rate_limit

    # Check rate limit before running AI (2 actions: caption + hashtags)
    async with async_session_factory() as db:
        try:
            await check_ai_rate_limit(db, tenant_id)
        except Exception:
            logger.warning("AI rate limit exceeded for tenant %s, skipping generation", tenant_id)
            return

    async with trace_llm_call(
        "bluewave.asset_pipeline",
        run_type="chain",
        inputs={"filename": filename, "file_type": file_type},
        metadata={
            "tenant_id": str(tenant_id),
            "asset_id": str(asset_id),
            "user_id": str(user_id),
            "pipeline_steps": ["caption", "hashtags"],
        },
        tags=["pipeline", "asset-upload"],
    ) as pipeline_run:
        caption = await ai_service.generate_caption(
            filename, file_type, file_path=file_path, tenant_id=tenant_id
        )
        hashtags = await ai_service.generate_hashtags(
            filename, file_type, file_path=file_path
        )

        pipeline_run.log_output({
            "caption": caption,
            "hashtags": hashtags,
        })

    # Generate thumbnail for image assets
    thumb_path = await generate_thumbnail(
        file_path=file_path,
        file_type=file_type,
        tenant_id=str(tenant_id),
        asset_id=str(asset_id),
    )

    async with async_session_factory() as db:
        result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()
        if asset:
            asset.caption = caption
            asset.hashtags = hashtags
            if thumb_path:
                asset.thumbnail_path = thumb_path

            # Log AI usage for billing
            await log_ai_usage(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                asset_id=asset_id,
                action_type=AIActionType.caption,
            )
            await log_ai_usage(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                asset_id=asset_id,
                action_type=AIActionType.hashtags,
            )
            await db.commit()

    # Emit webhook + trigger automations after AI completes
    try:
        await emit_event(tenant_id, "ai.completed", {
            "id": str(asset_id), "caption": caption, "hashtags": hashtags,
        })
        await on_event("asset_uploaded", asset_id, tenant_id)
    except Exception:
        logger.warning("Post-AI event dispatch failed for asset %s", asset_id)


@router.get("/counts")
async def asset_counts(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Return asset counts grouped by status for sidebar badges."""
    result = await db.execute(
        select(MediaAsset.status, func.count(MediaAsset.id))
        .group_by(MediaAsset.status)
    )
    counts = {row[0].value: row[1] for row in result.all()}
    return {
        "draft": counts.get("draft", 0),
        "pending_approval": counts.get("pending_approval", 0),
        "approved": counts.get("approved", 0),
        "total": sum(counts.values()),
    }


@router.get("", response_model=AssetListResponse)
async def list_assets(
    status_filter: AssetStatus | None = Query(None, alias="status"),
    q: str | None = Query(None, min_length=1, max_length=200),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Build base filter
    filters = []
    if status_filter:
        filters.append(MediaAsset.status == status_filter)
    if q:
        # Full-text search via tsvector (PostgreSQL) with ILIKE fallback
        from sqlalchemy import literal_column
        try:
            ts_query = func.plainto_tsquery("english", q)
            filters.append(literal_column("search_vector").op("@@")(ts_query))
        except Exception:
            search = f"%{q}%"
            filters.append(MediaAsset.caption.ilike(search) | MediaAsset.file_path.ilike(search))

    # Single query with window function for total count
    total_col = func.count(MediaAsset.id).over().label("_total")
    query = select(MediaAsset, total_col)
    for f in filters:
        query = query.where(f)
    query = query.order_by(MediaAsset.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    rows = result.all()

    items = [row[0] for row in rows]
    total = rows[0][1] if rows else 0

    return AssetListResponse(items=items, total=total, page=page, size=size)


@router.get("/{asset_id}", response_model=AssetOut)
async def get_asset(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{asset_id}/file")
async def get_asset_file(
    asset_id: uuid.UUID,
    token: str | None = Query(None),
    current_user: UserContext | None = Depends(_optional_auth),
):
    """Serve the actual file for preview/download.

    Accepts auth via Bearer header OR ?token= query parameter
    (needed for <img src> tags that can't send custom headers).
    """
    if not current_user and not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # If no Bearer auth, validate the query token
    if not current_user and token:
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")

    # Use unscoped session — asset ID is already unique
    from app.core.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not os.path.exists(asset.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        asset.file_path,
        media_type=asset.file_type,
        filename=asset.file_path.rsplit("/", 1)[-1],
    )


@router.get("/{asset_id}/thumbnail")
async def get_asset_thumbnail(
    asset_id: uuid.UUID,
    token: str | None = Query(None),
    current_user: UserContext | None = Depends(_optional_auth),
):
    """Serve the thumbnail image for an asset.

    Accepts auth via Bearer header OR ?token= query parameter
    (needed for <img src> tags that can't send custom headers).
    """
    if not current_user and not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    # If no Bearer auth, validate the query token
    if not current_user and token:
        from app.core.security import decode_token
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token")

    # Use unscoped session — asset ID is already unique
    from app.core.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(
            select(MediaAsset).where(MediaAsset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not asset.thumbnail_path or not os.path.exists(asset.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(
        asset.thumbnail_path,
        media_type="image/webp",
        filename=f"{asset_id}.webp",
    )


@router.post("", response_model=AssetOut, status_code=202)
async def upload_asset(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    # Validate MIME type
    if not file.content_type or not any(
        file.content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: image/*, video/*",
        )

    # Validate file extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read file and check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50 MB limit")

    # Save to disk: uploads/{tenant_id}/{uuid}_{filename}
    tenant_dir = os.path.join(UPLOAD_ROOT, str(current_user.tenant_id))
    os.makedirs(tenant_dir, exist_ok=True)

    safe_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(tenant_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    asset = MediaAsset(
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.user_id,
        file_path=file_path,
        file_type=file.content_type,
        file_size=len(content),
        status=AssetStatus.draft,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # Enqueue AI generation background task
    background_tasks.add_task(
        _run_ai_generation,
        asset.id,
        current_user.tenant_id,
        current_user.user_id,
        file.filename,
        file.content_type,
        file_path,
    )

    # Emit webhook for upload
    background_tasks.add_task(
        emit_event,
        current_user.tenant_id,
        "asset.uploaded",
        {"id": str(asset.id), "file_type": file.content_type,
         "file_size": len(content), "uploaded_by": str(current_user.user_id)},
    )

    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
async def update_asset(
    asset_id: uuid.UUID,
    body: AssetUpdate,
    current_user: UserContext = Depends(require_role("admin", "editor")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if body.caption is not None:
        asset.caption = body.caption
    if body.hashtags is not None:
        asset.hashtags = body.hashtags

    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: uuid.UUID,
    current_user: UserContext = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_tenant_db),
):
    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    await db.delete(asset)
    await db.commit()
    return None


# ---------------------------------------------------------------------------
# Bulk export (ZIP)
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    asset_ids: list[uuid.UUID]


@router.post("/export")
async def export_assets(
    body: ExportRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Export selected assets as a ZIP file with metadata CSV."""
    if len(body.asset_ids) > 100:
        raise HTTPException(400, "Maximum 100 assets per export")
    if not body.asset_ids:
        raise HTTPException(400, "No asset IDs provided")

    result = await db.execute(
        select(MediaAsset).where(MediaAsset.id.in_(body.asset_ids))
    )
    assets = result.scalars().all()

    if not assets:
        raise HTTPException(404, "No assets found")

    import csv
    import io
    import zipfile

    buf = io.BytesIO()
    total_size = 0
    max_total = 500 * 1024 * 1024  # 500MB

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Add metadata CSV
        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["id", "filename", "caption", "hashtags", "status", "compliance_score", "created_at"])

        for asset in assets:
            filename = asset.file_path.rsplit("/", 1)[-1] if asset.file_path else "unknown"
            hashtags_str = ", ".join(asset.hashtags) if asset.hashtags else ""
            writer.writerow([
                str(asset.id), filename, asset.caption or "",
                hashtags_str, asset.status.value,
                asset.compliance_score, str(asset.created_at),
            ])

            # Add file if it exists
            if asset.file_path and os.path.exists(asset.file_path):
                file_size = os.path.getsize(asset.file_path)
                total_size += file_size
                if total_size > max_total:
                    raise HTTPException(400, "Export exceeds 500MB limit. Select fewer assets.")
                zf.write(asset.file_path, f"files/{filename}")

        zf.writestr("metadata.csv", csv_buf.getvalue())

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=bluewave_export.zip"},
    )


# ---------------------------------------------------------------------------
# Visual similarity search (IMP-17)
# ---------------------------------------------------------------------------

@router.get("/{asset_id}/similar")
async def find_similar_assets(
    asset_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_tenant_db),
):
    """Find visually similar assets using CLIP embeddings."""
    from app.services.embedding_service import find_similar
    results = await find_similar(str(asset_id), str(current_user.tenant_id), limit)
    return {"similar": results, "count": len(results)}
