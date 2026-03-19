"""Thumbnail generation for uploaded images using Pillow."""

import logging
import os
from pathlib import Path

logger = logging.getLogger("bluewave.thumbnails")

THUMB_SIZE = (400, 400)
THUMB_QUALITY = 80
UPLOAD_ROOT = "/app/uploads"


async def generate_thumbnail(
    file_path: str,
    file_type: str,
    tenant_id: str,
    asset_id: str,
    size: tuple[int, int] = THUMB_SIZE,
) -> str | None:
    """Generate a WebP thumbnail for an image asset.

    Returns the thumbnail path or None if generation fails/unsupported.
    """
    if not file_type.startswith("image/"):
        return None

    try:
        from PIL import Image

        thumb_dir = os.path.join(UPLOAD_ROOT, str(tenant_id), "thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, f"{asset_id}.webp")

        with Image.open(file_path) as img:
            img.thumbnail(size)
            img.save(thumb_path, "WebP", quality=THUMB_QUALITY)

        logger.info("Thumbnail generated: %s", thumb_path)
        return thumb_path
    except Exception:
        logger.exception("Thumbnail generation failed for %s", file_path)
        return None
