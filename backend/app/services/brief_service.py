"""AI Content Brief generation service.

Generates comprehensive creative campaign briefs using Claude AI,
incorporating brand voice context and suggesting relevant existing assets.
Each brief costs $1.00 (100,000 millicents).
"""

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.prompt_safety import sanitize_for_prompt, wrap_user_input, strip_markdown_codeblock
from app.core.retry import retry
from app.core.tracing import trace_llm_call
from app.prompts import load_prompt

logger = logging.getLogger("bluewave.briefs")


async def generate_brief(
    prompt: str,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    brief_id: uuid.UUID,
) -> None:
    """Generate a content brief from a user prompt. Runs as background task."""
    from app.core.database import async_session_factory
    from app.models.ai_usage import AIActionType
    from app.models.asset import AssetStatus, MediaAsset
    from app.models.brand_guideline import BrandGuideline
    from app.models.content_brief import BriefStatus, ContentBrief
    from app.services.ai_usage import log_ai_usage

    import anthropic

    @retry(max_retries=3, base_delay=2.0, retryable=(anthropic.RateLimitError, anthropic.InternalServerError, anthropic.APIConnectionError))
    async def _call_claude_for_brief(client, model, system_prompt, user_message):
        return await client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": user_message}],
            system=system_prompt,
        )

    async with async_session_factory() as db:
        # Load brief record
        result = await db.execute(select(ContentBrief).where(ContentBrief.id == brief_id))
        brief = result.scalar_one_or_none()
        if not brief:
            return

        try:
            # Load brand guidelines
            g_result = await db.execute(
                select(BrandGuideline).where(
                    BrandGuideline.tenant_id == tenant_id,
                    BrandGuideline.is_active.is_(True),
                )
            )
            guidelines = g_result.scalar_one_or_none()

            # Load recent approved captions for brand voice
            cap_result = await db.execute(
                select(MediaAsset.caption)
                .where(
                    MediaAsset.tenant_id == tenant_id,
                    MediaAsset.status == AssetStatus.approved,
                    MediaAsset.caption.isnot(None),
                )
                .order_by(MediaAsset.updated_at.desc())
                .limit(20)
            )
            recent_captions = [r[0] for r in cap_result.all() if r[0]]

            # Build context
            brand_context = ""
            if guidelines:
                parts = []
                if guidelines.tone_description:
                    parts.append(f"Brand tone: {guidelines.tone_description}")
                if guidelines.primary_colors:
                    parts.append(f"Brand colors: {', '.join(guidelines.primary_colors)}")
                if guidelines.dos:
                    parts.append(f"Do: {', '.join(guidelines.dos)}")
                if guidelines.donts:
                    parts.append(f"Don't: {', '.join(guidelines.donts)}")
                brand_context = "\n".join(parts)

            voice_context = ""
            if recent_captions:
                examples = "\n".join(f"- {c}" for c in recent_captions[:10])
                voice_context = f"\nRecent approved captions (match this style):\n{examples}"

            # Generate brief with Claude
            system_prompt = load_prompt("brief_system")

            user_message = f"BRIEF REQUEST:\n{wrap_user_input('user_prompt', prompt, max_length=2000)}"
            if brand_context:
                user_message += f"\n\nBRAND CONTEXT:\n{sanitize_for_prompt(brand_context, max_length=2000)}"
            if voice_context:
                user_message += f"\n\n{voice_context}"

            async with trace_llm_call(
                "bluewave.generate_brief",
                inputs={"prompt": prompt},
                metadata={"tenant_id": str(tenant_id), "has_guidelines": bool(guidelines)},
                tags=["content-brief", "json-output"],
            ) as run:
                client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                resp = await _call_claude_for_brief(client, settings.AI_MODEL, system_prompt, user_message)
                raw = strip_markdown_codeblock(resp.content[0].text)
                brief_content = json.loads(raw)
                run.log_output({"brief_content": brief_content})

            # Find similar existing assets
            suggested_ids = []
            if brief_content.get("content_pieces"):
                keywords = " ".join(
                    p.get("title", "") for p in brief_content["content_pieces"][:3]
                )
                search = f"%{keywords[:50]}%"
                similar = await db.execute(
                    select(MediaAsset.id)
                    .where(
                        MediaAsset.tenant_id == tenant_id,
                        MediaAsset.caption.ilike(search),
                    )
                    .limit(10)
                )
                suggested_ids = [r[0] for r in similar.all()]

            # Update brief
            brief.brief_content = brief_content
            brief.suggested_asset_ids = suggested_ids
            brief.status = BriefStatus.completed

            # Log usage ($1.00)
            await log_ai_usage(
                db,
                tenant_id=tenant_id,
                user_id=user_id,
                asset_id=None,
                action_type=AIActionType.content_brief,
            )

            await db.commit()
            logger.info("Brief %s generated successfully", brief_id)

        except Exception:
            logger.exception("Brief generation failed for %s", brief_id)
            brief.status = BriefStatus.failed
            await db.commit()
