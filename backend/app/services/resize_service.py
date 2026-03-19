"""Smart resize service — generate social media format variants from a single image.

Supports center-crop to maintain subject focus. Each resize is logged as an AI action ($0.05).
"""

import logging
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("bluewave.resize")

UPLOAD_ROOT = "/app/uploads"

# Social media format presets
FORMATS: dict[str, dict] = {
    "instagram_square": {"width": 1080, "height": 1080, "name": "Instagram Feed"},
    "instagram_story": {"width": 1080, "height": 1920, "name": "Instagram/TikTok Story"},
    "facebook_post": {"width": 1200, "height": 630, "name": "Facebook Post"},
    "twitter_post": {"width": 1600, "height": 900, "name": "Twitter/X Post"},
    "linkedin_post": {"width": 1200, "height": 627, "name": "LinkedIn Post"},
    "linkedin_banner": {"width": 1584, "height": 396, "name": "LinkedIn Banner"},
    "youtube_thumbnail": {"width": 1280, "height": 720, "name": "YouTube Thumbnail"},
    "pinterest_pin": {"width": 1000, "height": 1500, "name": "Pinterest Pin"},
}


def smart_resize(file_path: str, target_width: int, target_height: int, output_path: str) -> str:
    """Resize image with center-crop to target dimensions. Returns output_path."""
    from PIL import Image

    with Image.open(file_path) as img:
        src_w, src_h = img.size
        src_ratio = src_w / src_h
        target_ratio = target_width / target_height

        if src_ratio > target_ratio:
            # Source is wider — crop sides
            new_w = int(src_h * target_ratio)
            offset = (src_w - new_w) // 2
            crop_box = (offset, 0, offset + new_w, src_h)
        else:
            # Source is taller — crop top/bottom
            new_h = int(src_w / target_ratio)
            offset = (src_h - new_h) // 2
            crop_box = (0, offset, src_w, offset + new_h)

        cropped = img.crop(crop_box)
        resized = cropped.resize((target_width, target_height), Image.LANCZOS)
        resized.save(output_path, "WebP", quality=85)

    return output_path


async def generate_all_variants(
    asset_id: uuid.UUID,
    file_path: str,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    format_names: list[str] | None = None,
) -> list[dict]:
    """Generate resized variants for an asset. Runs as background task."""
    from app.core.database import async_session_factory
    from app.models.ai_usage import AIActionType
    from app.models.asset_variant import AssetVariant
    from app.services.ai_usage import log_ai_usage

    if format_names is None or format_names == ["all"]:
        format_names = list(FORMATS.keys())

    output_dir = os.path.join(UPLOAD_ROOT, str(tenant_id), "resized", str(asset_id))
    os.makedirs(output_dir, exist_ok=True)

    created = []

    async with async_session_factory() as db:
        for fmt_name in format_names:
            fmt = FORMATS.get(fmt_name)
            if not fmt:
                logger.warning("Unknown format: %s", fmt_name)
                continue

            output_path = os.path.join(output_dir, f"{fmt_name}.webp")
            try:
                smart_resize(file_path, fmt["width"], fmt["height"], output_path)
                file_size = os.path.getsize(output_path)

                variant = AssetVariant(
                    tenant_id=tenant_id,
                    asset_id=asset_id,
                    format_name=fmt_name,
                    width=fmt["width"],
                    height=fmt["height"],
                    file_path=output_path,
                    file_size=file_size,
                )
                db.add(variant)

                await log_ai_usage(
                    db,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    asset_id=asset_id,
                    action_type=AIActionType.resize,
                )

                created.append({"format": fmt_name, "width": fmt["width"], "height": fmt["height"], "file_size": file_size})
                logger.info("Variant created: %s %dx%d for asset %s", fmt_name, fmt["width"], fmt["height"], asset_id)

            except Exception:
                logger.exception("Failed to create variant %s for asset %s", fmt_name, asset_id)

        await db.commit()

    return created
