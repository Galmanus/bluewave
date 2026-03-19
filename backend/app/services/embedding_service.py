"""Visual similarity search using CLIP embeddings.

Generates 512-dimensional embeddings for images using OpenCLIP ViT-B/32,
stores them in pgvector, and performs cosine similarity search.

Dependencies: open-clip-torch, torch (CPU), numpy, pgvector
All optional — gracefully degrades if not installed.
"""

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("bluewave.embeddings")

# Lazy-loaded singleton
_model = None
_preprocess = None
_tokenizer = None


def _load_model():
    """Load CLIP model (lazy singleton). Caches in memory after first call."""
    global _model, _preprocess, _tokenizer
    if _model is not None:
        return _model, _preprocess

    try:
        import open_clip
        import torch

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        model.eval()
        _model = model
        _preprocess = preprocess
        _tokenizer = open_clip.get_tokenizer("ViT-B-32")
        logger.info("CLIP model loaded (ViT-B/32, 512-dim)")
        return model, preprocess
    except ImportError:
        logger.warning("open-clip-torch or torch not installed — visual search disabled")
        return None, None
    except Exception:
        logger.exception("Failed to load CLIP model")
        return None, None


def generate_embedding(image_path: str) -> np.ndarray | None:
    """Generate a 512-dim CLIP embedding for an image. Returns None if unavailable."""
    model, preprocess = _load_model()
    if model is None:
        return None

    try:
        import torch
        from PIL import Image

        img = Image.open(image_path).convert("RGB")
        img_tensor = preprocess(img).unsqueeze(0)

        with torch.no_grad():
            embedding = model.encode_image(img_tensor)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # normalize

        return embedding.squeeze().numpy()
    except Exception:
        logger.exception("Embedding generation failed for %s", image_path)
        return None


async def store_embedding(asset_id, embedding: np.ndarray) -> None:
    """Store embedding in the media_assets table (pgvector column)."""
    from app.core.database import async_session_factory
    from sqlalchemy import text

    try:
        async with async_session_factory() as db:
            # pgvector expects a list representation
            vec_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
            await db.execute(
                text("UPDATE media_assets SET embedding = :vec WHERE id = :id"),
                {"vec": vec_str, "id": str(asset_id)},
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to store embedding for asset %s", asset_id)


async def find_similar(
    asset_id: str,
    tenant_id: str,
    limit: int = 10,
) -> list[dict]:
    """Find visually similar assets using cosine distance on pgvector embeddings."""
    from app.core.database import async_session_factory
    from sqlalchemy import text

    try:
        async with async_session_factory() as db:
            # Get the embedding of the query asset
            result = await db.execute(
                text("SELECT embedding FROM media_assets WHERE id = :id"),
                {"id": asset_id},
            )
            row = result.fetchone()
            if not row or row[0] is None:
                return []

            # Find similar by cosine distance
            similar = await db.execute(
                text("""
                    SELECT id, caption,
                           1 - (embedding <=> (SELECT embedding FROM media_assets WHERE id = :query_id)) AS similarity
                    FROM media_assets
                    WHERE tenant_id = :tid AND id != :query_id AND embedding IS NOT NULL
                    ORDER BY embedding <=> (SELECT embedding FROM media_assets WHERE id = :query_id)
                    LIMIT :lim
                """),
                {"query_id": asset_id, "tid": tenant_id, "lim": limit},
            )
            return [
                {"id": str(r[0]), "caption": r[1], "similarity": round(float(r[2]), 3)}
                for r in similar.fetchall()
            ]
    except Exception:
        logger.exception("Similarity search failed for asset %s", asset_id)
        return []
