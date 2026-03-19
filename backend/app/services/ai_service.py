"""AI service layer with Claude API integration and stub fallback.

ClaudeAIService uses Anthropic's Claude API with vision support to
analyse uploaded media and generate captions + hashtags.  When no
API key is configured the service falls back to StubAIService so
development/testing works without external calls.
"""

import base64
import json
import logging
import mimetypes
import time
import uuid
from datetime import datetime
from typing import Protocol

import anthropic

# In-memory cache for brand voice context: {tenant_id: (text, expires_at)}
_brand_voice_cache: dict[uuid.UUID, tuple[str, float]] = {}
_BRAND_VOICE_TTL = 300  # 5 minutes

from app.core.config import settings
from app.core.retry import retry
from app.core.prompt_safety import sanitize_for_prompt, wrap_user_input, strip_markdown_codeblock
from app.core.tracing import trace_llm_call
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class AIServiceProtocol(Protocol):
    async def generate_caption(
        self, filename: str, file_type: str, *,
        file_path: str | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> str: ...

    async def generate_hashtags(
        self, filename: str, file_type: str, *, file_path: str | None = None
    ) -> list[str]: ...


# ---------------------------------------------------------------------------
# Stub (deterministic, no API calls)
# ---------------------------------------------------------------------------

class StubAIService:
    """Deterministic stubs for development/testing."""

    _CAPTIONS = {
        "image": "A stunning visual composition that captures attention and tells a compelling brand story.",
        "video": "An engaging video that showcases dynamic movement and delivers a powerful brand message.",
    }

    _HASHTAGS = {
        "image": [
            "#photography", "#visualcontent", "#branding",
            "#creative", "#marketing", "#design",
        ],
        "video": [
            "#videocontent", "#motion", "#branding",
            "#storytelling", "#marketing", "#production",
        ],
    }

    async def generate_caption(
        self, filename: str, file_type: str, *,
        file_path: str | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> str:
        media_kind = "video" if file_type.startswith("video/") else "image"
        base = self._CAPTIONS[media_kind]
        caption = f"{base} | {filename}"

        async with trace_llm_call(
            "bluewave.generate_caption",
            inputs={"filename": filename, "file_type": file_type},
            metadata={"is_stub": True, "tenant_id": str(tenant_id) if tenant_id else None},
            tags=["caption", "stub", "development"],
        ) as run:
            run.log_output({"caption": caption})

        return caption

    async def generate_hashtags(
        self, filename: str, file_type: str, *, file_path: str | None = None
    ) -> list[str]:
        media_kind = "video" if file_type.startswith("video/") else "image"
        hashtags = self._HASHTAGS[media_kind]

        async with trace_llm_call(
            "bluewave.generate_hashtags",
            inputs={"filename": filename, "file_type": file_type},
            metadata={"is_stub": True},
            tags=["hashtags", "stub", "development"],
        ) as run:
            run.log_output({"hashtags": hashtags})

        return hashtags


# ---------------------------------------------------------------------------
# Claude API (real implementation)
# ---------------------------------------------------------------------------

# Media types Claude vision accepts
_VISION_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
}

# Max image payload for the API (20 MB)
_MAX_IMAGE_BYTES = 20 * 1024 * 1024


def _read_image_as_base64(file_path: str, file_type: str) -> tuple[str, str] | None:
    """Read an image file and return (base64_data, media_type) or None."""
    if file_type not in _VISION_TYPES:
        return None
    try:
        with open(file_path, "rb") as f:
            data = f.read(_MAX_IMAGE_BYTES + 1)
        if len(data) > _MAX_IMAGE_BYTES:
            logger.warning("Image too large for vision API: %s", file_path)
            return None
        return base64.standard_b64encode(data).decode("ascii"), file_type
    except OSError:
        logger.exception("Failed to read image for vision: %s", file_path)
        return None


class ClaudeAIService:
    """Real AI service powered by Anthropic Claude API with vision."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.AI_MODEL

    # -- brand voice (few-shot examples from approved content) -----------

    async def _get_brand_voice_context(self, tenant_id: uuid.UUID | None) -> str:
        """Load recent approved captions as few-shot examples for brand voice learning."""
        if not tenant_id:
            return ""
        try:
            from app.core.database import async_session_factory
            from app.models.asset import AssetStatus, MediaAsset
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(
                    select(MediaAsset.caption)
                    .where(
                        MediaAsset.tenant_id == tenant_id,
                        MediaAsset.status == AssetStatus.approved,
                        MediaAsset.caption.isnot(None),
                    )
                    .order_by(MediaAsset.updated_at.desc())
                    .limit(10)
                )
                captions = [row[0] for row in result.all() if row[0]]

            if len(captions) < 3:
                return ""

            examples = "\n".join(f"- {c}" for c in captions[:8])
            return (
                f"\n\nBRAND VOICE EXAMPLES (match this style and tone):\n{examples}\n\n"
                "Write the new caption in the same style, tone, and voice as these examples."
            )
        except Exception:
            logger.debug("Brand voice context load failed — using generic style")
            return ""

    # -- internal retryable call ----------------------------------------

    @retry(max_retries=3, base_delay=1.0, retryable=(anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError))
    async def _call_claude(self, *, model: str, max_tokens: int, system: str, content: list[dict]) -> anthropic.types.Message:
        """Retryable Claude API call with exponential backoff."""
        return await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
            system=system,
        )

    # -- caption --------------------------------------------------------

    async def generate_caption(
        self, filename: str, file_type: str, *,
        file_path: str | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> str:
        content = self._build_caption_content(filename, file_type, file_path)
        brand_voice = await self._get_brand_voice_context(tenant_id)
        has_image = file_path is not None and file_type in _VISION_TYPES
        brand_voice_count = brand_voice.count("- ") if brand_voice else 0

        system_prompt = load_prompt("caption_system") + brand_voice

        trace_inputs = {
            "system_prompt": system_prompt,
            "model": self._model,
            "max_tokens": 300,
            "filename": filename,
            "file_type": file_type,
        }
        trace_metadata = {
            "tenant_id": str(tenant_id) if tenant_id else None,
            "filename": filename,
            "file_type": file_type,
            "has_vision": has_image,
            "brand_voice_examples": brand_voice_count,
        }
        trace_tags = ["caption", "vision" if has_image else "text-only"]
        if brand_voice_count > 0:
            trace_tags.append("brand-voice")

        async with trace_llm_call(
            "bluewave.generate_caption",
            inputs=trace_inputs,
            metadata=trace_metadata,
            tags=trace_tags,
        ) as run:
            t0 = time.perf_counter()
            try:
                resp = await self._call_claude(
                    model=self._model,
                    max_tokens=300,
                    system=system_prompt,
                    content=content,
                )
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                usage = resp.usage if hasattr(resp, "usage") else None
                input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
                output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
                caption = resp.content[0].text.strip()

                run.log_output({
                    "caption": caption,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "model_used": resp.model,
                    "stop_reason": resp.stop_reason,
                    "duration_ms": duration_ms,
                })

                logger.info(
                    "AI caption generated",
                    extra={
                        "model": self._model, "filename": filename,
                        "duration_ms": duration_ms, "success": True,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "langsmith_run_id": run.run_id,
                    },
                )
                return caption
            except Exception:
                duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                fallback = f"Creative asset: {filename}"
                run.log_output({"caption": fallback, "used_fallback": True, "duration_ms": duration_ms})
                run.add_tags(["fallback"])
                logger.exception(
                    "AI caption failed",
                    extra={"model": self._model, "filename": filename, "duration_ms": duration_ms, "success": False},
                )
                return fallback

    # -- hashtags -------------------------------------------------------

    async def generate_hashtags(
        self, filename: str, file_type: str, *, file_path: str | None = None
    ) -> list[str]:
        content = self._build_hashtag_content(filename, file_type, file_path)
        has_image = file_path is not None and file_type in _VISION_TYPES

        system_prompt = load_prompt("hashtags_system")

        async with trace_llm_call(
            "bluewave.generate_hashtags",
            inputs={"system_prompt": system_prompt, "model": self._model, "filename": filename, "file_type": file_type},
            metadata={"filename": filename, "file_type": file_type, "has_vision": has_image, "output_format": "json_array"},
            tags=["hashtags", "json-output", "vision" if has_image else "text-only"],
        ) as run:
            try:
                resp = await self._call_claude(
                    model=self._model,
                    max_tokens=200,
                    system=system_prompt,
                    content=content,
                )
                raw = resp.content[0].text.strip()
                json_parse_ok = False
                try:
                    tags = json.loads(raw)
                    json_parse_ok = True
                except json.JSONDecodeError:
                    tags = None

                if json_parse_ok and isinstance(tags, list) and all(isinstance(t, str) for t in tags):
                    result = [t if t.startswith("#") else f"#{t}" for t in tags]
                    usage = resp.usage if hasattr(resp, "usage") else None
                    run.log_output({
                        "hashtags": result,
                        "hashtag_count": len(result),
                        "raw_response": raw,
                        "json_parse_success": True,
                        "used_fallback": False,
                        "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
                        "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
                        "model_used": resp.model,
                    })
                    return result

                # JSON parsed but wrong format, or parse failed
                run.log_output({
                    "raw_response": raw,
                    "json_parse_success": json_parse_ok,
                    "used_fallback": True,
                })
                run.add_tags(["fallback"])
                raise ValueError("Unexpected format or JSON parse failed")
            except Exception:
                fallback = ["#creative", "#content", "#branding", "#marketing", "#digital"]
                run.log_output({"hashtags": fallback, "used_fallback": True})
                run.add_tags(["fallback"])
                logger.exception("Claude hashtag generation failed for %s", filename)
                return fallback

    # -- helpers --------------------------------------------------------

    def _build_caption_content(
        self, filename: str, file_type: str, file_path: str | None
    ) -> list[dict]:
        """Build message content, including vision block when possible."""
        blocks: list[dict] = []
        image_data = None
        if file_path and file_type in _VISION_TYPES:
            image_data = _read_image_as_base64(file_path, file_type)

        safe_filename = sanitize_for_prompt(filename, max_length=200)
        safe_type = sanitize_for_prompt(file_type, max_length=50)

        if image_data:
            b64, media = image_data
            blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media, "data": b64},
            })
            blocks.append({
                "type": "text",
                "text": (
                    f"This image file metadata:\n"
                    f"{wrap_user_input('filename', safe_filename)}\n"
                    f"{wrap_user_input('file_type', safe_type)}\n"
                    "Write a compelling, concise caption for this asset."
                ),
            })
        else:
            media_kind = "video" if file_type.startswith("video/") else "image"
            blocks.append({
                "type": "text",
                "text": (
                    f"Generate a caption for a {media_kind} asset.\n"
                    f"{wrap_user_input('filename', safe_filename)}\n"
                    f"{wrap_user_input('file_type', safe_type)}\n"
                    "Infer the likely content from the filename "
                    "and write a compelling, concise caption."
                ),
            })
        return blocks

    def _build_hashtag_content(
        self, filename: str, file_type: str, file_path: str | None
    ) -> list[dict]:
        """Build message content for hashtag generation."""
        blocks: list[dict] = []
        image_data = None
        if file_path and file_type in _VISION_TYPES:
            image_data = _read_image_as_base64(file_path, file_type)

        safe_filename = sanitize_for_prompt(filename, max_length=200)
        safe_type = sanitize_for_prompt(file_type, max_length=50)

        if image_data:
            b64, media = image_data
            blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": media, "data": b64},
            })
            blocks.append({
                "type": "text",
                "text": (
                    f"This image file metadata:\n"
                    f"{wrap_user_input('filename', safe_filename)}\n"
                    f"{wrap_user_input('file_type', safe_type)}\n"
                    "Generate relevant hashtags for this asset."
                ),
            })
        else:
            media_kind = "video" if file_type.startswith("video/") else "image"
            blocks.append({
                "type": "text",
                "text": (
                    f"Generate hashtags for a {media_kind} asset.\n"
                    f"{wrap_user_input('filename', safe_filename)}\n"
                    f"{wrap_user_input('file_type', safe_type)}\n"
                    "Infer the likely content from the filename."
                ),
            })
        return blocks


    # -- multi-language captions ------------------------------------------

    async def generate_caption_multilang(
        self, filename: str, file_type: str, *,
        file_path: str | None = None,
        languages: list[str] | None = None,
    ) -> dict[str, str]:
        """Generate captions in multiple languages in a single Claude call."""
        if not languages:
            languages = ["en", "pt", "es", "fr", "de"]

        content = self._build_caption_content(filename, file_type, file_path)
        lang_list = ", ".join(languages)

        async with trace_llm_call(
            "bluewave.generate_caption_multilang",
            inputs={"filename": filename, "languages": languages},
            metadata={"language_count": len(languages)},
            tags=["caption", "multilang"],
        ) as run:
            try:
                resp = await self._call_claude(
                    model=self._model,
                    max_tokens=1000,
                    content=content,
                    system=(
                        f"Generate a concise, engaging caption for this asset in each of these languages: {lang_list}. "
                        'Return ONLY a JSON object mapping language codes to captions. '
                        'Example: {"en": "...", "pt": "...", "es": "..."}. No other text.'
                    ),
                )
                raw = strip_markdown_codeblock(resp.content[0].text)
                result = json.loads(raw)
                if isinstance(result, dict):
                    run.log_output({"captions": result, "language_count": len(result)})
                    return result
            except Exception:
                logger.exception("Multi-language caption failed for %s", filename)

            # Fallback: return English only
            return {"en": f"Creative asset: {filename}"}


# ---------------------------------------------------------------------------
# Singleton — picks real service when API key is set, else stub
# ---------------------------------------------------------------------------

def _create_ai_service() -> AIServiceProtocol:
    if settings.ANTHROPIC_API_KEY:
        logger.info("AI service: ClaudeAIService (model=%s)", settings.AI_MODEL)
        return ClaudeAIService()
    logger.warning("ANTHROPIC_API_KEY not set — using StubAIService")
    return StubAIService()


ai_service: AIServiceProtocol = _create_ai_service()
